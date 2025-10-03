from apolo_apps_launchpad.inputs_processor import LaunchpadInputsProcessor
from apolo_apps_launchpad.outputs_processor import LaunchpadOutputProcessor
from .types import LaunchpadAppInputs, LaunchpadAppOutputs

APOLO_APP_TYPE = "launchpad"

__all__ = [
    "APOLO_APP_TYPE",
    "LaunchpadAppInputs",
    "LaunchpadAppOutputs",
    "LaunchpadOutputProcessor",
    "LaunchpadInputsProcessor",
]
