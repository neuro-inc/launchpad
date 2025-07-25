from launchpad.apps.registry.model import App


APP_NAME_LLM_INFERENCE = "vllm-llama-3.1-8b"


def gen_llm_inference_definition(preset: str) -> App:
    return App(
        template_name="llm-inference",
        template_version="v25.7.1",
        name=APP_NAME_LLM_INFERENCE,
        is_internal=True,
        is_shared=True,
        input={
            "ingress_http": None,
            "hugging_face_model": {
                "hf_token": {"key": "HF_TOKEN"},
                "model_hf_name": "meta-llama/Llama-3.1-8B-Instruct",
            },
            "tokenizer_hf_name": "meta-llama/Llama-3.1-8B-Instruct",
            "cache_config": None,
            "displayName": APP_NAME_LLM_INFERENCE,
            "preset": {
                "name": preset,
            },
            "server_extra_args": [],
            "extra_env_vars": [],
        },
    )
