"""
REST-based node that interfaces with WEI and provides a simple Sleep(t) function
"""

from pathlib import Path

from pe_icp_interface import ICPInterface
from starlette.datastructures import State
from wei.modules.rest_module import RESTModule
from wei.types.module_types import ModuleState
from wei.types.step_types import StepResponse
from wei.utils import extract_version

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


# ***********#
# *Lifecycle*#
# ***********#
@pe_icp_module.startup()
def custom_startup_handler(state: State):
    """
    Open the connection to the ICP Interface when the module is started
    """
    state.icp_interface = None
    state.icp_interface = ICPInterface(state.server_ip, state.client_ip, state.name)


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
        state.icp_interface.syn_client.GetAnalysisStatus()
        return ModuleState.model_validate(
            {
                "status": state.status,  # *Required
                "error": state.error,
                "instrument_status": state.icp_interface.instrument_status,
                "plasma_status": state.icp_interface.plasma_status,
                "analysis_status": state.icp_interface.analysis_status,
                "autosampler_status": state.icp_interface.autosampler_status,
                "connection_status": state.icp_interface.connection_status,
            }
        )

    return ModuleState.model_validate(
        {
            "status": state.status,  # *Required
            "error": state.error,
        }
    )


###########
# Actions #
###########

@pe_icp_module.action("plasma_on")
def plasma_on(state: State) -> StepResponse:
    """
    Turn on the plasma
    """
    state.icp_interface.syn_client.PlasmaOn()
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())

@pe_icp_module.action("plasma_off")
def plasma_off(state: State) -> StepResponse:
    """
    Turn off the plasma
    """
    state.icp_interface.syn_client.PlasmaOff()
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())

@pe_icp_module.action("move_autosampler")
def move_autosampler(state: State, location: int) -> StepResponse:
    """
    Move the autosampler to a specific position
    """
    state.icp_interface.syn_client.MoveAutosampler(location)
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())

@pe_icp_module.action("stop_analysis")
def stop_analysis(state: State) -> StepResponse:
    """
    Stop the analysis
    """
    state.icp_interface.syn_client.StopAnalysis()
    return StepResponse.step_succeeded(state.icp_interface.syn_client.Response())

@pe_icp_module.cancel()
@pe_icp_module.pause()
@pe_icp_module.safety_stop()
def cancel(state: State) -> StepResponse:
    """
    Cancel the current action
    """
    state.icp_interface.syn_client.StopAnalysis()

if __name__ == "__main__":
    pe_icp_module.start()
