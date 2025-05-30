from datetime import datetime
from pathlib import Path
import shutil
import time
from typing import Annotated, Any, Optional

from madsci.common.types.action_types import (
    ActionFailed,
    ActionSucceeded,
    ActionResult
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

from pe_icp_interface import ICPInterface


class ICPConfig(RestNodeConfig):
    """Configuration for a Syngistix ICP Node"""

    dll_path: str = (
        "C:/Program Files (x86)/PerkinElmer/Syngistix-ICP/SyngistixRemoteControl"
    )
    """The path to the folder containing the SyngistixRemoteControl .NET DLL"""
    server_ip: str = "146.139.45.9"
    """IP Address of the Syngistix Remote Control Server"""
    client_ip: str = "146.139.45.9"
    """IP Address of the client machine connecting to the Syngisix Remote Control Server"""
    result_file_path: str = "C:/Users/Public/PerkinElmer Syngistix/ICP/Data/Reports"
    """Path to the ICP's report output folder"""
    sample_info_path: str = "C:/Users/Public/PerkinElmer Syngistix/ICP/Data/Sample Information"


class ICPNode(RestNode):
    """Node Module Implementation for the Perkins Elmer Syngistix ICP Instruments"""

    config_model = ICPConfig

    icp: Optional[ICPInterface] = None
    """Instance of a PE ICP Interface"""

    def startup_handler(self) -> None:
        """Connects to the ICP on node startup"""
        self.icp = ICPInterface(
            server_ip=self.config.server_ip,
            client_ip=self.config.client_ip,
            name=self.node_definition.node_name,
            dll_path=self.config.dll_path,
        )

    def shutdown_handler(self) -> None:
        """Disconnects from the ICP on node shutdown"""
        del self.icp

    def state_handler(self) -> None:
        """Called periodically to update the state published by the node"""
        if self.icp is not None:
            self.node_state = {
                "instrument_error": str(self.icp.instrument_error),
                "last_updated": str(datetime.now()),
                "instrument_status": self.icp.instrument_status,
                "plasma_status": self.icp.plasma_status,
                "analysis_status": self.icp.analysis_status,
                "autosampler_status": self.icp.autosampler_status,
                "connection_status": self.icp.connection_status,
            }
    @action(name="run_analysis")
    def run_analysis(
    self,
    method_name: Annotated[str, "The name of the method to use for the analysis"],
    dataset_name: Annotated[str, "The name of the dataset to store results to"],
    sample_info_file: Annotated[Path, "The sample info file"],
    export_template_name: Annotated[
        str, "The name of the export template file to use for auto-export"
    ],
    wavelength_realign: Annotated[
        int,
        "When to auto realign the wavelength. 0 for never, 1 for the start of analysis, 2 for the start of each method.",
    ],
    precalibrate: Annotated[
        bool, "Whether to precalibrate the instrument before starting the analysis"
    ] = False,
    use_active_method: Annotated[
        bool,
        "Whether to use the active method, or load the method specified by 'method_name' (ignored if 'precalibrate' is False)",
    ] = False,
    wait_for_completion: Annotated[
        bool, "Whether to wait for the analysis to complete before returning"
    ] = True,
) -> ActionResult:
        """
        Start an auto analysis process
        """
        shutil.copyfile(sample_info_file, Path(self.config.sample_info_folder) / sample_info_file.name)
        self.icp.start_auto_analysis(
            method_name,
            dataset_name,
            sample_info_file.name,
            export_template_name,
            wavelength_realign,
            precalibrate,
            use_active_method,
        )
        self.icp.syn_client.GetAnalysisStatus()
        if wait_for_completion:
            while self.icp.analysis_status[0] in [1, 2]:
                time.sleep(1)
        return ActionSucceeded(
                files={
                    "result_file": Path(self.config.result_file_path)
                    / f"{dataset_name}.csv",
                   
                },
            )

    

    
    @action(name="Hg_realign")
    def Hg_realign(self) -> ActionResult:
        """Realign the mercury bulb"""
        return self.icp.Hg_realign()

    @action(name="Plasma_on")
    def Plasma_on(self, 
        num_retrys: Annotated[int, "The number of times to retry starting the plasma"],
        retry_delay: Annotated[int, "The number of seconds to wait between attempts"],
        stabilization_delay: Annotated[float, "The time to wait after completion for stabilization"] = 900,
        
        ) -> ActionResult:
        """Safely enable the ICP's plasma"""
        
        if self.icp.plasma_on(num_retrys=num_retrys, retry_delay=retry_delay):
            time.sleep(stabilization_delay)
            return ActionSucceeded()
        else:
            self.logger.log_error("Plasma Failed To Ignite")
            return ActionFailed()

    @action(name="Plasma_off")
    def Plasma_off(self,
        num_retrys: Annotated[int, "The number of times to retry disabling the plasma"],
        retry_delay: Annotated[int, "The number of seconds to wait between attempts"]) -> ActionResult:
        """Safely disable the ICP's plasma"""
        if self.icp.plasma_off(num_retrys=num_retrys, retry_delay=retry_delay):
            return ActionSucceeded()
        else:
            self.logger.log_error("Plasma Failed To Turn Off")
            return ActionFailed()



"""-------------"""
"""Admin Actions"""
"""-------------"""


def safety_stop(self) -> AdminCommandResponse:
    # hard stopping current analysis
    if not self.icp.hard_stop():
        self.logger.log_error("Plasma failed to turn off")
    return AdminCommandResponse


if __name__ == "__main__":
    icp_node = ICPNode()
    icp_node.start_node()
