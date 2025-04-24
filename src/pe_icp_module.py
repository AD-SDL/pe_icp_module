from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Optional

from madsci.common.types.action_types import (
    ActionFailed,
    ActionResult,
    ActionStatus,
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
    file_path: str = "C:/Users/Public/PerkinElmer Syngistix/ICP/Data/Reports"
    """Path to the ICP's report output folder"""


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
            name=self.node_definition.name,
            dll_path=self.config.dll_path,
        )

    def shutdown_handler(self) -> None:
        """Disconnects from the ICP on node shutdown"""
        del self.icp

    def state_handler(self) -> None:
        """Called periodically to update the state published by the node"""
        if self.icp is not None:
            if self.node_status.ready:
                self.icp.syn_client.GetPlasmaStatus()
                self.icp.syn_client.GetInstrumentStatus()
                self.icp.syn_client.GetAnalysisStatus()
                self.node_state = {
                    "instrument_error": str(self.icp.instrument_error),
                    "last_updated": str(datetime.now()),
                    "instrument_status": self.icp.instrument_status,
                    "plasma_status": self.icp.plasma_status,
                    "analysis_status": self.icp.analysis_status,
                    "autosampler_status": self.icp.autosampler_status,
                    "connection_status": self.icp.connection_status,
                }

    @action
    def start_auto_analysis_on_container(
        self,
        method_name: Annotated[str, "The name of the method to use for the analysis"],
        container: Annotated[Any, "The sample container to use"],
        dataset_name: Annotated[str, "The name of the dataset to store results to"],
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
        """Start's the ICP's auto analysis process using the specified method name"""
        icp: ICPInterface = self.icp
        icp.container = container
        icp.last_method = method_name
        icp.last_template = export_template_name
        icp.unpack_self_container()
        result = icp.run_analysis()  # 0 if incomplete or there is a problem

        # result code, also icp.status["decision"]

        # OK to continue
        # 1 - Normal (Normal termination)
        # 2 - Incomplete (Incomplete normal run)
        # 3 - Soft stop (External stop)

        # Do not continue
        # 0 - No connection (Syngistix cannot be remoted into)
        # 4 - Socket error (Syngistic crashed during the run)
        # 5 - Hard stop (Hardware error during the run)
        # 6 - Hard stop, recovered (hard reload of Syngistix)
        # 7 - Failed (analysis failed to load)
        try:  # if exist, data needs to be saved regardless of the termination
            return ActionResult(
                status=ActionStatus.SUCCEEDED
                if result in [1, 2, 3]
                else ActionStatus.FAILED,
                data={"result": result, "last_id": icp.last_ID},
                files={
                    "result_file": Path(self.config.file_path)
                    / f"run_{icp.last_ID}.csv",
                    "converted_file": Path(self.config.file_path)
                    / f"run_{icp.last_ID}_converted.csv",
                    "status_file": Path(self.config.file_path)
                    / f"ICP_{icp.last_ID}.json",
                },
            )
        except Exception as e:
            ActionFailed(errors=e)

    @action
    def copy2storage(
        self,
        name: Annotated[str, "The name of central data storage to copy results to"],
    ) -> ActionResult:
        """Copy results for the current container to storage"""
        return self.icp.copy2exp(name)

    @action(name="Hg_realign")
    def Hg_realign(self) -> ActionResult:
        """Realign the mercury bulb"""
        return self.icp.Hg_realign()

    @action(name="Plasma_on")
    def Plasma_on(self) -> ActionResult:
        """Safely enable the ICP's plasma"""
        return self.icp.plasma(True)

    @action(name="Plasma_off")
    def Plasma_off(self) -> ActionResult:
        """Safely disable the ICP's plasma"""
        return self.icp.plasma(False)


"""-------------"""
"""Admin Actions"""
"""-------------"""


def safety_stop(self) -> AdminCommandResponse:
    # hard stopping current analysis
    self.icp.hard_stop("Administrative stop")
    return AdminCommandResponse


if __name__ == "__main__":
    icp_node = ICPNode()
    icp_node.start_node()
