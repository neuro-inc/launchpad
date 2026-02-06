import json
import os
import random
import string
import typing as t

import apolo_sdk
from apolo_app_types import LLMInputs, TextEmbeddingsInferenceAppInputs
from apolo_app_types.app_types import AppType
from apolo_app_types.helm.apps.base import BaseChartValueProcessor
from apolo_app_types.helm.apps.common import (
    append_apolo_storage_integration_annotations,
    gen_apolo_storage_integration_labels,
    gen_extra_values,
)
from apolo_app_types.helm.apps.ingress import _get_ingress_name_template
from apolo_app_types.helm.utils.dictionaries import get_nested_values
from apolo_app_types.outputs.utils.apolo_secrets import get_apolo_secret
from apolo_app_types.protocols.common.hugging_face import (
    HuggingFaceCache,
    HuggingFaceModel,
)
from apolo_app_types.protocols.common.storage import (
    ApoloFilesMount,
    ApoloFilesPath,
    MountPath,
)
from apolo_app_types.protocols.postgres import (
    PGBackupConfig,
    PGBouncer,
    PostgresConfig,
    PostgresDBUser,
    PostgresInputs,
)

from .consts import APP_SECRET_KEYS
from .types import (
    ApoloFilesImagePath,
    ColorPicker,
    CustomLLMModel,
    HuggingFaceEmbeddingsModel,
    HuggingFaceLLMModel,
    LaunchpadAppInputs,
    NoQuickStartConfig,
    OpenWebUIConfig,
    PreConfiguredEmbeddingsModels,
    PreConfiguredHuggingFaceLLMModel,
    PreConfiguredLLMModels,
)


PASSWORD_CHAR_POOL = string.ascii_letters + string.digits
PASSWORD_DEFAULT_LENGTH = 12
PASSWORD_MIN_LENGTH = 4

# Branding paths
BRANDING_DIR_LAUNCHPAD = "/etc/launchpad/branding"
BRANDING_DIR_KEYCLOAK = "/opt/bitnami/keycloak/themes/apolo/login/resources/branding"


def _generate_password(length: int = PASSWORD_DEFAULT_LENGTH) -> str:
    if length < PASSWORD_MIN_LENGTH:
        err_msg = f"Password length must be at least {PASSWORD_MIN_LENGTH}"
        raise ValueError(err_msg)

    return "".join([random.choice(PASSWORD_CHAR_POOL) for _ in range(length)])


class LaunchpadInputsProcessor(BaseChartValueProcessor[LaunchpadAppInputs]):
    async def get_vllm_inputs(
        self,
        input_: LaunchpadAppInputs,
    ) -> LLMInputs:
        if isinstance(input_.apps_config.quick_start_config, NoQuickStartConfig):
            raise Exception("NoQuickStartConfig is not allowed for this method")

        llm_extra_args: list[str] = []
        if isinstance(
            input_.apps_config.quick_start_config.llm_config.model,
            PreConfiguredHuggingFaceLLMModel,
        ):
            llm_model = HuggingFaceModel(
                model_hf_name=input_.apps_config.quick_start_config.llm_config.model.model.value,
                hf_token=input_.apps_config.quick_start_config.llm_config.model.hf_token,
            )
            llm_extra_args = (
                input_.apps_config.quick_start_config.llm_config.model.server_extra_args
            )
            match input_.apps_config.quick_start_config.llm_config.model.model:
                case PreConfiguredLLMModels.MAGISTRAL_24B:
                    llm_extra_args.extend(
                        [
                            "--tokenizer_mode=mistral",
                            "--config_format=mistral",
                            "--load_format=mistral",
                            "--tool-call-parser=mistral",
                            "--enable-auto-tool-choice",
                            "--tensor-parallel-size=2",
                        ]
                    )
        elif isinstance(
            input_.apps_config.quick_start_config.llm_config.model, HuggingFaceLLMModel
        ):
            llm_model = input_.apps_config.quick_start_config.llm_config.model.hf_model
            llm_extra_args = (
                input_.apps_config.quick_start_config.llm_config.model.server_extra_args
            )
        elif isinstance(
            input_.apps_config.quick_start_config.llm_config.model, CustomLLMModel
        ):
            # For custom models, we use the model_name as both model and tokenizer
            llm_model = HuggingFaceModel(
                model_hf_name=input_.apps_config.quick_start_config.llm_config.model.model_name,
            )
            llm_extra_args = (
                input_.apps_config.quick_start_config.llm_config.model.server_extra_args
            )
        else:
            err = (
                "Unsupported LLM model type. Expected "
                "PreConfiguredHuggingFaceLLMModel, HuggingFaceLLMModel, "
                "or CustomLLMModel."
            )
            raise ValueError(err)

        # Determine cache configuration based on model type
        if isinstance(
            input_.apps_config.quick_start_config.llm_config.model, CustomLLMModel
        ):
            # For custom models, mount the model path as cache
            cache_config = HuggingFaceCache(
                files_path=input_.apps_config.quick_start_config.llm_config.model.model_apolo_path
            )
        else:
            # For HuggingFace models, use the standard cache
            cache_config = HuggingFaceCache(
                files_path=ApoloFilesPath(path="storage:.apps/hugging-face-cache")
            )
        llm_model.hf_cache = cache_config

        return LLMInputs(
            hugging_face_model=llm_model,
            tokenizer_hf_name=llm_model.model_hf_name,
            preset=input_.apps_config.quick_start_config.llm_config.llm_preset,
            server_extra_args=llm_extra_args,
        )

    async def get_postgres_inputs(
        self,
        input_: LaunchpadAppInputs,
    ) -> PostgresInputs:
        if isinstance(input_.apps_config.quick_start_config, NoQuickStartConfig):
            raise Exception("NoQuickStartConfig is not allowed for this method")

        return PostgresInputs(
            preset=input_.apps_config.quick_start_config.postgres_config.preset,
            postgres_config=PostgresConfig(
                instance_replicas=input_.apps_config.quick_start_config.postgres_config.replicas,
                db_users=[PostgresDBUser(name="launchpaduser", db_names=["launchpad"])],
            ),
            pg_bouncer=PGBouncer(
                preset=input_.apps_config.quick_start_config.postgres_config.preset,
                replicas=input_.apps_config.quick_start_config.postgres_config.replicas,
            ),
            backup=PGBackupConfig(enable=True),
        )

    async def get_text_embeddings_inputs(
        self,
        input_: LaunchpadAppInputs,
    ) -> TextEmbeddingsInferenceAppInputs:
        if isinstance(input_.apps_config.quick_start_config, NoQuickStartConfig):
            raise Exception("NoQuickStartConfig is not allowed for this method")

        extra_args: list[str] = []
        if isinstance(
            input_.apps_config.quick_start_config.embeddings_config.model,
            PreConfiguredEmbeddingsModels,
        ):
            model_name = (
                input_.apps_config.quick_start_config.embeddings_config.model.value
            )
            model = HuggingFaceModel(
                model_hf_name=model_name,
            )
        elif isinstance(
            input_.apps_config.quick_start_config.embeddings_config.model,
            HuggingFaceEmbeddingsModel,
        ):
            model = (
                input_.apps_config.quick_start_config.embeddings_config.model.hf_model
            )
            extra_args = input_.apps_config.quick_start_config.embeddings_config.model.server_extra_args
        else:
            err = "Unsupported embeddings model type."
            raise ValueError(err)

        return TextEmbeddingsInferenceAppInputs(
            model=model,
            preset=input_.apps_config.quick_start_config.embeddings_config.preset,
            server_extra_args=extra_args,
        )

    async def gen_extra_values(
        self,
        input_: LaunchpadAppInputs,
        app_name: str,
        namespace: str,
        app_id: str,
        app_secrets_name: str,
        *_: t.Any,
        **kwargs: t.Any,
    ) -> dict[str, t.Any]:
        # may need storage later, especially as cache for pulling models
        # base_app_storage_path = get_app_data_files_path_url(
        #     client=self.client,
        #     app_type_name=str(AppType.Launchpad.value),
        #     app_name=app_name,
        # )
        LAUNCHPAD_INITIAL_CONFIG = ""
        db_secret_name = f"launchpad-{app_id}-db-secret"
        kc_realm_import_config_map_name = f"launchpad-{app_id}-keycloak-realm"

        print("Quick start config:", input_.apps_config.quick_start_config)
        if isinstance(input_.apps_config.quick_start_config, OpenWebUIConfig):
            print("Using OpenWebUI preset configuration")
            llm_input = await self.get_vllm_inputs(
                input_,
            )
            postgres_inputs = await self.get_postgres_inputs(
                input_,
            )
            text_embeddings_inputs = await self.get_text_embeddings_inputs(
                input_,
            )
            LAUNCHPAD_INITIAL_CONFIG = json.dumps(
                {
                    "vllm": get_nested_values(
                        llm_input.model_dump(),
                        [
                            "hugging_face_model",
                            "preset",
                            "server_extra_args",
                        ],
                    ),
                    "postgres": get_nested_values(
                        postgres_inputs.model_dump(),
                        ["preset", "pg_bouncer.preset"],
                    ),
                    "text-embeddings": get_nested_values(
                        text_embeddings_inputs.model_dump(),
                        ["model", "preset", "server_extra_args"],
                    ),
                }
            )

        # Add storage integration labels to lauchpad deployment if branding files provided
        needs_branding_mounts = False
        if input_.branding and (
            input_.branding.logo_file
            or input_.branding.favicon_file
            or (
                input_.branding.background
                and isinstance(input_.branding.background, ApoloFilesImagePath)
            )
        ):
            needs_branding_mounts = True

        lauchpad_file_mounts = []
        kc_file_mounts = []

        if needs_branding_mounts:
            if input_.branding.logo_file:
                lauchpad_file_mounts.append(
                    ApoloFilesMount(
                        storage_uri=t.cast(ApoloFilesPath, input_.branding.logo_file),
                        mount_path=MountPath(path=f"{BRANDING_DIR_LAUNCHPAD}/logo"),
                    )
                )
                kc_file_mounts.append(
                    ApoloFilesMount(
                        storage_uri=t.cast(ApoloFilesPath, input_.branding.logo_file),
                        mount_path=MountPath(path=f"{BRANDING_DIR_KEYCLOAK}/logo"),
                    )
                )

            if input_.branding.favicon_file:
                lauchpad_file_mounts.append(
                    ApoloFilesMount(
                        storage_uri=t.cast(
                            ApoloFilesPath, input_.branding.favicon_file
                        ),
                        mount_path=MountPath(path=f"{BRANDING_DIR_LAUNCHPAD}/favicon"),
                    )
                )
                kc_file_mounts.append(
                    ApoloFilesMount(
                        storage_uri=t.cast(
                            ApoloFilesPath, input_.branding.favicon_file
                        ),
                        mount_path=MountPath(path=f"{BRANDING_DIR_KEYCLOAK}/favicon"),
                    )
                )

            if input_.branding.background and isinstance(
                input_.branding.background, ApoloFilesImagePath
            ):
                lauchpad_file_mounts.append(
                    ApoloFilesMount(
                        storage_uri=t.cast(ApoloFilesPath, input_.branding.background),
                        mount_path=MountPath(
                            path=f"{BRANDING_DIR_LAUNCHPAD}/background"
                        ),
                    )
                )
                kc_file_mounts.append(
                    ApoloFilesMount(
                        storage_uri=t.cast(ApoloFilesPath, input_.branding.background),
                        mount_path=MountPath(
                            path=f"{BRANDING_DIR_KEYCLOAK}/background"
                        ),
                    )
                )

        ### LAUCHPAD CONFIGURATION ###
        values = await gen_extra_values(
            apolo_client=self.client,
            preset_type=input_.launchpad_web_app_config.preset,
            namespace=namespace,
            app_id=app_id,
            app_type=AppType.Launchpad,
        )

        if lauchpad_file_mounts:
            storage_labels = gen_apolo_storage_integration_labels(
                client=self.client, inject_storage=True
            )
            if "podLabels" not in values:
                values["podLabels"] = {}
            values["podLabels"].update(storage_labels)

            pod_annotations = append_apolo_storage_integration_annotations(
                current_annotations=values.get("podAnnotations", {}),
                files_mounts=lauchpad_file_mounts,
                client=self.client,
            )
            values["podAnnotations"] = pod_annotations

        ingress_template = await _get_ingress_name_template(
            client=self.client,
        )
        domain = ingress_template.split(".", 1)[1]
        if domain.endswith("."):
            domain = domain[:-1]

        extra_env = {}
        if input_.branding:
            if needs_branding_mounts:
                extra_env["BRANDING_DIR"] = BRANDING_DIR_LAUNCHPAD

            if input_.branding.title:
                extra_env["BRANDING_TITLE"] = input_.branding.title

            if input_.branding.background and isinstance(
                input_.branding.background, ColorPicker
            ):
                extra_env["BRANDING_BACKGROUND"] = input_.branding.background.hex_code

        ### KEYCLOAK CONFIGURATION ###
        try:
            keycloak_admin_password = await get_apolo_secret(
                app_instance_id=app_id, key=APP_SECRET_KEYS["KEYCLOAK"]
            )
        except apolo_sdk.ResourceNotFound:
            keycloak_admin_password = _generate_password()

        try:
            keycloak_db_password = await get_apolo_secret(
                app_instance_id=app_id, key=APP_SECRET_KEYS["KEYCLOAK_DB"]
            )
        except apolo_sdk.ResourceNotFound:
            keycloak_db_password = _generate_password()

        try:
            launchpad_admin_password = await get_apolo_secret(
                app_instance_id=app_id, key=APP_SECRET_KEYS["LAUNCHPAD"]
            )
        except apolo_sdk.ResourceNotFound:
            launchpad_admin_password = _generate_password()

        keycloak_values = {
            "fullnameOverride": f"launchpad-{app_id}-keycloak",
            "auth": {
                "adminPassword": keycloak_admin_password,
            },
            "externalDatabase": {"existingSecret": db_secret_name},
            **values,
            "labels": {
                "application": "launchpad",
            },
            "service": {
                "extraLabels": {
                    "service": "keycloak",
                }
            },
            "extraVolumes": [
                {
                    "name": "realm-import",
                    "configMap": {
                        "name": kc_realm_import_config_map_name,
                        "items": [
                            {
                                "key": "realm.json",
                                "path": "realm.json",
                            }
                        ],
                    },
                }
            ],
        }

        if kc_file_mounts:
            if "podLabels" not in keycloak_values:
                keycloak_values["podLabels"] = {}
            keycloak_values["podLabels"].update(
                gen_apolo_storage_integration_labels(
                    client=self.client, inject_storage=True
                )
            )
            keycloak_values["podAnnotations"] = (
                append_apolo_storage_integration_annotations(
                    current_annotations={},  # ignore annotations from lauchpad
                    files_mounts=kc_file_mounts,
                    client=self.client,
                )
            )

        kc_extra_env_vars = []
        if input_.branding and input_.branding.background:
            if isinstance(input_.branding.background, ColorPicker):
                kc_extra_env_vars.append(
                    {
                        "name": "BRANDING_BACKGROUND_COLOR",
                        "value": input_.branding.background.hex_code,
                    }
                )
        if kc_extra_env_vars:
            keycloak_values["extraEnvVars"] = kc_extra_env_vars

        return {
            **values,
            "image": {"tag": os.getenv("APP_IMAGE_TAG", "latest")},
            "dbSecretName": db_secret_name,
            "keycloakRealmImportConfigMapName": kc_realm_import_config_map_name,
            "postgresql": {
                "fullnameOverride": f"launchpad-{app_id}-db",
                "auth": {
                    "existingSecret": db_secret_name,
                },
            },
            "dbPassword": keycloak_db_password,
            "extraEnv": extra_env,
            "domain": domain,
            "keycloak": keycloak_values,  # keeping this for backwards compatibility
            "mlops-keycloak": keycloak_values,
            "LAUNCHPAD_ADMIN_USER": "admin",
            "LAUNCHPAD_ADMIN_EMAIL": "admin@launchpad.com",
            "LAUNCHPAD_ADMIN_PASSWORD": launchpad_admin_password,
            "LAUNCHPAD_INITIAL_CONFIG": LAUNCHPAD_INITIAL_CONFIG,
        }
