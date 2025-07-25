from launchpad.apps.registry.model import App


APP_NAME_EMBEDDINGS = "embeddings"


def gen_embeddings_definition(preset: str) -> App:
    return App(
        template_name="text-embeddings-inference",
        template_version="v25.7.0",
        name=APP_NAME_EMBEDDINGS,
        is_internal=True,
        is_shared=True,
        input={
            "ingress_http": None,
            "model": {"hf_token": {"key": "HF_TOKEN"}, "model_hf_name": "BAAI/bge-m3"},
            "displayName": APP_NAME_EMBEDDINGS,
            "preset": {"name": preset},
            "server_extra_args": [],
            "extra_env_vars": [],
        },
    )
