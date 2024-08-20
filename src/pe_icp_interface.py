"""Interface for controlling a Perkins Elmer Syngistix ICP."""

import sys
import time

# * Using .dlls and .NET assemblies
# * pip install pythonnet
# * See docs: https://pythonnet.github.io/pythonnet/python.html
import clr
from typing_extensions import Self


class ICPInterface:
    """Interface for controlling a Perkins Elmer Syngistix ICP."""

    instrument_status = None
    plasma_status = None
    analysis_status = None
    analysis_sample = None
    autosampler_status = None
    client_status = []
    instrument_error = {}
    connection_status = None

    def __init__(
        self,
        server_ip: str,
        client_ip: str,
        name: str,
        dll_path: str = r"""C:\Program Files (x86)\PerkinElmer\Syngistix-ICP\SyngistixRemoteControl""",
    ) -> Self:
        """Initialize the ICP interface"""

        sys.path.append(dll_path)
        clr.AddReference("RemoteSyngsitix")
        import RemoteSyngistix

        self.RemoteSyngistix = RemoteSyngistix
        self.syn_client = RemoteSyngistix.SyngistixInterface()
        self.syn_client.connectionStatusCallback = (
            RemoteSyngistix.ConnectionStatusCallback(self.connection_status_callback)
        )
        self.syn_client.statusCallback = RemoteSyngistix.StatusCallback(
            self.status_callback
        )
        self.syn_client.plasmaStatusCallback = RemoteSyngistix.PlasmaStatusCallback(
            self.plasma_status_callback
        )
        self.syn_client.analysisStatusCallback = RemoteSyngistix.AnalysisStatusCallback(
            self.analysis_status_callback
        )
        self.syn_client.analysisSampleCallback = RemoteSyngistix.AnalysisSampleCallback(
            self.analysis_sample_callback
        )
        self.syn_client.instrumentStatusCallback = (
            RemoteSyngistix.InstrumentStatusCallback(self.instrument_status_callback)
        )
        self.syn_client.autosamplerStatusCallback = (
            RemoteSyngistix.AutosamplerStatusCallback(self.autosampler_status_callback)
        )
        self.syn_client.errorCallback = RemoteSyngistix.ErrorCallback(
            self.error_callback
        )
        print(
            "Connected: ",
            self.syn_client.Connect(clientIP=client_ip, serverIP=server_ip, name=name),
        )

    def __del__(self):
        """Disconnect from the ICP interface"""
        self.syn_client.Disconnect()

    def status_callback(self, status: str):
        """Callback function for status"""
        self.client_status.append(status)

    def error_callback(self, num: int, msg: str, severity: int):
        """Callback function for errors"""
        self.instrument_error[num] = {"msg": msg, "severity": severity}

    def analysis_status_callback(self, status: int):
        """Callback function for analysis status"""

        if status == 1:
            self.analysis_status = f"{status}: Analysis Running"
        elif status == 2:
            self.analysis_status = f"{status}: Analysis Paused"
        elif status == 0:
            self.analysis_status = f"{status}: Idle"
        else:
            self.analysis_status = status

    def analysis_sample_callback(self, sampleID: str):
        """Callback function for analysis sample"""
        self.analysis_sample = sampleID

    def plasma_status_callback(self, status: int):
        """Callback function for plasma status"""
        if status == 0:
            self.plasma_status = f"{status}: Plasma is On"
        elif status == 1:
            self.plasma_status = f"{status}: Plasma is Off"
        elif status == 2:
            self.plasma_status = f"{status}: Plasma Igniting"
        elif status == 3:
            self.plasma_status = f"{status}: Plasma Extinguishing"
        else:
            self.plasma_status = status

    def instrument_status_callback(self, status: int):
        """Callback function for instrument status"""
        self.instrument_status = (
            f"{status}: {self.RemoteSyngistix.InstrumentStatus(status).ToString()}"
        )

    def autosampler_status_callback(self, status: int):
        """Callback function for autosampler status"""
        self.autosampler_status = (
            f"{status}: {self.RemoteSyngistix.InstrumentStatus(status).ToString()}"
        )

    def connection_status_callback(self, status: int):
        """Callback function for connection status"""
        self.connection_status = status == 1

    def start_auto_analysis(
        self,
        method_name: str,
        dataset_name: str,
        sample_info_name: str,
        export_template_name: str,
        wavelength_realign: int,
        precalibrate: bool = False,
        use_active_method: bool = False,
    ):
        """Start an auto analysis"""
        if precalibrate:
            self.syn_client.AutoAnalyzeAll(
                methodName=method_name,
                dataSetName=dataset_name,
                sampleInfoName=sample_info_name,
                exportTemplateName=export_template_name,
                wavelenghtRealign=wavelength_realign,
                methodSource=use_active_method,
            )
        else:
            self.syn_client.AutoAnalyzeSamples(
                methodName=method_name,
                dataSetName=dataset_name,
                sampleInfoName=sample_info_name,
                exportTemplateName=export_template_name,
                wavelenghtRealign=wavelength_realign,
            )

if __name__ == "__main__":
    # * Example usage
    icp = ICPInterface("192.168.4.32", "192.168.4.32", "Test from Python")
    time.sleep(5)
    del icp
