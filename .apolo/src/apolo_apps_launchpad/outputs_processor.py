import typing as t

from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.outputs.launchpad import get_launchpad_outputs

from .types import LaunchpadAppOutputs


class LaunchpadOutputProcessor(BaseAppOutputsProcessor[LaunchpadAppOutputs]):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
        app_instance_id: str,
    ) -> LaunchpadAppOutputs:
        return LaunchpadAppOutputs.model_validate(
            **(await get_launchpad_outputs(helm_values, app_instance_id))
        )