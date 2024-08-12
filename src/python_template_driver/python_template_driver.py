"""Driver for interfacing with the python_template device/instrument/robot."""

from pathlib import Path

from starlette.datastructures import State

# * Using .dlls and .NET assemblies
# * pip install pythonnet
# * See docs: https://pythonnet.github.io/pythonnet/python.html
# import clr
# clr.AddReference("Your.Assembly")
# from Your.Driver.Namespace import DriverClass


def run_protocol(path: Path):
    """Run a protocol file"""
    pass


def query_state(state: State):
    """Update the state by querying the device"""
    pass
