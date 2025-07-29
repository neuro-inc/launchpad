from typing import Any

from launchpad.apps.registry.base import App
from launchpad.apps.registry.internal.context import InternalAppContext

APP_NAME_LLM_INFERENCE = "vllm-llama-3.1-8b"


class LlmInferenceApp(App[InternalAppContext]):
    name = APP_NAME_LLM_INFERENCE
    template_name = "llm-inference"
    template_version = "v25.7.1"
    is_internal = True
    is_shared = True
    verbose_name = "LLM Inference"
    description_short = "LLM Inference"
    description_long = "LLM Inference"
    logo = ""
    documentation_urls = []
    external_urls = []
    tags = []

    async def _generate_inputs(self) -> dict[str, Any]:
        return {
            "ingress_http": None,
            "hugging_face_model": {
                "hf_token": {"key": "HF_TOKEN"},
                "model_hf_name": "meta-llama/Llama-3.1-8B-Instruct",
            },
            "tokenizer_hf_name": "meta-llama/Llama-3.1-8B-Instruct",
            "cache_config": None,
            "displayName": APP_NAME_LLM_INFERENCE,
            "preset": {
                "name": self._context.preset,
            },
            "server_extra_args": [],
            "extra_env_vars": [],
        }
