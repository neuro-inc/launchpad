from launchpad.apps.registry.base import BaseContext, GenericApp
from apolo_app_types.helm.utils.deep_merging import merge_list_of_dicts
from copy import deepcopy

from starlette.requests import Request
from typing import Self, Any, cast


class ServiceDeploymentContext(BaseContext):
    auth_middleware_name: str

    @classmethod
    async def from_request(
        cls,
        request: Request,
    ) -> Self:
        params = {
            "auth_middleware_name": request.app.config.apolo.auth_middleware_name,
        }
        return ServiceDeploymentContext(**params)


class ServiceDeploymentApp(GenericApp):
    async def _generate_inputs(self) -> dict[str, Any]:
        context = cast(ServiceDeploymentContext, self._context)
        inputs = deepcopy(self._inputs)
        middleware_config = {
            "networking_config": {
                "advanced_networking": {
                    "ingress_middleware": {"name": context.auth_middleware_name}
                },
            }
        }
        inputs = merge_list_of_dicts([inputs, middleware_config])
        return inputs
