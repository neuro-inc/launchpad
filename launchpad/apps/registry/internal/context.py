import dataclasses

from launchpad.apps.registry.base import BaseContext


@dataclasses.dataclass
class InternalAppContext(BaseContext):
    preset: str
