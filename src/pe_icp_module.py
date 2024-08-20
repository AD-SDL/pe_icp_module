"""
REST-based node that interfaces with WEI and provides a simple Sleep(t) function
"""

import time
from pathlib import Path
from typing import Optional

from starlette.datastructures import State
from typing_extensions import Annotated
from wei.modules.rest_module import RESTModule
from wei.types.module_types import ModuleState
from wei.types.step_types import StepResponse
from wei.utils import extract_version

from pe_icp_interface import ICPInterface

pe_icp_module = RESTModule(
    name="pe_icp_module",
    version=extract_version(Path(__file__).parent.parent / "pyproject.toml"),
    description="Controls a PerkinElmer Syngistix ICP (such as the Avio 550 Max).",
    model="PerkinElmer Avio 550 Max",
)
pe_icp_module.arg_parser.add_argument(
    "--server_ip",
    type=str,
    default="192.168.4.32",  # TODO: Generalize this
)
pe_icp_module.arg_parser.add_argument("--client_ip", type=str, default="192.168.4.32")
pe_icp_module.arg_parser.add_argument(
    "--dll_path",
    type=str,
    default=r"""C:\Program Files (x86)\PerkinElmer\Syngistix-ICP\SyngistixRemoteControl""",
)


"""---------"""
"""Lifecycle"""
"""---------"""


@pe_icp_module.startup()
def custom_startup_handler(state: State):
    """
    Open the connection to the ICP Interface when the module is started
    """
    state.icp_interface = None
    state.icp_interface = ICPInterface(
        state.server_ip, state.client_ip, state.name, state.dll_path
    )


@pe_icp_module.shutdown()
def custom_shutdown_handler(state: State):
    """
    Close the connection to Syngistix ICP when the module is shut down
    """

    del state.icp_interface


@pe_icp_module.state_handler()
def custom_state_handler(state: State) -> ModuleState:
    """
    Returns the module's status, along with information about the state of the instrument
    """

    # interface.query_state(state)  # *Query the state of the device, if supported
    if state.icp_interface is not None:
        state.icp_interface.syn_client.GetPlasmaStatus()
        state.icp_interface.syn_client.GetInstrumentStatus()
        print(state.icp_interface.syn_client.GetAnalysisStatus())
        return ModuleState.model_validate(
            {
                "status": state.status,  # *Required
                "error": state.error,
                "instrument_status": state.icp_interface.instrument_status,
                "plasma_status": state.icp_interface.plasma_status,
                "analysis_status": state.icp_interface.analysis_status,
                "autosampler_status": state.icp_interface.autosampler_status,
                "connection_status": state.icp_interface.connection_status,
                "methods": state.icp_interface.syn_client.GetMethodsList(str()),
            }
        )

    return ModuleState.model_validate(
        {
            "status": state.status,  # *Required
            "error": state.error,
        }
    )


"""--------"""
""" Actions"""
"""--------"""


@pe_icp_module.action(name="plasma_on")
def plasma_on(state: State) -> StepResponse:
    """
    Turn on the plasma
    """
    state.icp_interface.syn_client.PlasmaOn()
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())


@pe_icp_module.action(name="plasma_off")
def plasma_off(state: State) -> StepResponse:
    """
    Turn off the plasma
    """
    state.icp_interface.syn_client.PlasmaOff()
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())


@pe_icp_module.action(name="move_autosampler")
def move_autosampler(state: State, location: int) -> StepResponse:
    """
    Move the autosampler to a specific position
    """
    state.icp_interface.syn_client.MoveAutosampler(location)
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())


@pe_icp_module.action(name="stop_analysis")
def stop_analysis(state: State) -> StepResponse:
    """
    Stop the analysis
    """
    state.icp_interface.syn_client.StopAnalysis()
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())


@pe_icp_module.action(name="start_auto_analysis")
def start_auto_analysis(
    state: State,
    method_name: Annotated[str, "The name of the method to use for the analysis"],
    dataset_name: Annotated[str, "The name of the dataset to store results to"],
    sample_info_name: Annotated[
        str, "The name of the sample info file to use for analysis"
    ],
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
) -> StepResponse:
    """
    Start an auto analysis process
    """
    icp: ICPInterface = state.icp_interface
    icp.start_auto_analysis(
        method_name,
        dataset_name,
        sample_info_name,
        export_template_name,
        wavelength_realign,
        precalibrate,
        use_active_method,
    )
    icp.syn_client.GetAnalysisStatus()
    if wait_for_completion:
        while icp.analysis_status[0] in [1, 2]:
            time.sleep(1)
            icp.syn_client.GetAnalysisStatus()
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())


@pe_icp_module.action(name="hg_realign")
def hg_realign(state: State) -> StepResponse:
    """
    Realign the mercury lamp
    """
    state.icp_interface.syn_client.HgRealign()
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())


@pe_icp_module.action(name="load_sample_info")
def load_sample_info(
    state: State,
    sample_info_file_path: Annotated[
        str, "The path of the sample info file to load into Syngistix."
    ],
) -> StepResponse:
    """
    Load a sample info file
    """
    state.icp_interface.syn_client.DownloadSampleInfoFile(sample_info_file_path)
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())


@pe_icp_module.action(name="load_method")
def load_method(
    state: State,
    method_name: Annotated[str, "The name of the method to load into Syngistix"],
) -> StepResponse:
    """
    Load a method
    """
    state.icp_interface.syn_client.LoadMethod(method_name)
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())


@pe_icp_module.action(name="start_manual_analysis")
def start_manual_analysis(
    state: State,
    sample_id: Annotated[Optional[str], "The ID of the sample to analyze"] = None,
    blank_num: Annotated[Optional[int], "The calibration blank number (1-n)"] = None,
    std_num: Annotated[
        Optional[int],
        "The calibration standard number as defined in the Syngistix method (1-n)",
    ] = None,
    qc_num: Annotated[
        Optional[int], "The QC number (1-n) as defined in the Syngistix method"
    ] = None,
    wait_for_completion: Annotated[
        bool, "Whether to wait for the analysis to complete before returning"
    ] = True,
) -> StepResponse:
    """
    Start a manual analysis process. The type of analysis is determined by the provided parameter. Only one of sample_id, blank_num, std_num, or qc_num should be provided, if multiple are provided, the first one will be used.
    """
    icp: ICPInterface = state.icp_interface
    if sample_id is not None:
        icp.syn_client.ManualAnalyzeSample(sample_id)
    elif blank_num is not None:
        icp.syn_client.ManualAnalyzeBlank(blank_num)
    elif std_num is not None:
        icp.syn_client.ManualAnalyzeStd(std_num)
    elif qc_num is not None:
        icp.syn_client.ManualAnalyzeQC(qc_num)
    icp.syn_client.GetAnalysisStatus()
    if wait_for_completion:
        while icp.analysis_status[0] in [1, 2]:
            time.sleep(1)
            icp.syn_client.GetAnalysisStatus()
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())


"""-------------"""
"""Admin Actions"""
"""-------------"""


@pe_icp_module.cancel()
def cancel(state: State) -> StepResponse:
    """
    Cancel the current action
    """
    state.icp_interface.syn_client.StopAnalysis()
    state.icp_interface.syn_client.ResetAnalysisSequence()
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())


@pe_icp_module.pause()
@pe_icp_module.safety_stop()
def stop(state: State) -> StepResponse:
    """
    Stop the current action
    """
    state.icp_interface.syn_client.StopAnalysis()


if __name__ == "__main__":
    pe_icp_module.start()
