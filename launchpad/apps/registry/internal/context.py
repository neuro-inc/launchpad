import dataclasses
from typing import Any

from launchpad.apps.registry.base import BaseContext


@dataclasses.dataclass
class InternalAppContext(BaseContext):
    config: dict[str, Any]

    def merge_with_inputs(
        self, inputs: dict[str, Any], config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Recursively merges inputs with the context
        """
        config = config or self.config
        merged_dict = (
            inputs.copy()
        )  # Start with a copy to avoid modifying original dict1

        for key, value in config.items():
            if key in merged_dict:
                if isinstance(merged_dict[key], dict) and isinstance(value, dict):
                    # If both values are dictionaries, recursively merge them
                    merged_dict[key] = self.merge_with_inputs(value, merged_dict[key])
                elif isinstance(merged_dict[key], list) and isinstance(value, list):
                    # If both values are lists, extend the list in merged_dict
                    merged_dict[key].extend(value)
                else:
                    # For other types, or if types don't match, overwrite with context value
                    merged_dict[key] = value
            else:
                # If a key is not in inputs, add it from context
                merged_dict[key] = value
        return merged_dict
