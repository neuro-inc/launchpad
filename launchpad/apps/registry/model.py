import dataclasses
from typing import Any


@dataclasses.dataclass
class App:
    name: str
    template_name: str
    template_version: str
    is_internal: bool
    is_shared: bool
    input: dict[str, Any]

    def __str__(self) -> str:
        return self.name

    __repr__ = __str__

    def to_apps_api_payload(self) -> dict[str, Any]:
        return {
            "template_name": self.template_name,
            "template_version": self.template_version,
            "input": self.input,
        }
