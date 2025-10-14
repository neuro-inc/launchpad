import json

import pytest

from apolo_app_types.protocols.common import Preset
from apolo_app_types.protocols.common.storage import ApoloFilesPath
from apolo_apps_launchpad.inputs_processor import LaunchpadInputsProcessor
from apolo_apps_launchpad.types import (
    AppsConfig,
    CustomLLMModel,
    HuggingFaceLLMModel,
    LaunchpadAppInputs,
    LaunchpadWebAppConfig,
    LLMConfig,
    OpenWebUIConfig,
    PostgresConfig,
    PreConfiguredEmbeddingsModels,
    PreConfiguredHuggingFaceLLMModel,
    PreConfiguredLLMModels,
    TextEmbeddingsConfig,
)

from apolo_app_types_fixtures.constants import (
    APP_ID,
    APP_SECRETS_NAME,
)


@pytest.mark.asyncio
async def test_launchpad_values_generation_with_preconfigured_model(setup_clients):
    """Test launchpad helm values generation with a pre-configured LLM model."""
    processor = LaunchpadInputsProcessor(client=setup_clients)
    helm_params = await processor.gen_extra_values(
        input_=LaunchpadAppInputs(
            launchpad_web_app_config=LaunchpadWebAppConfig(
                preset=Preset(name="cpu-small"),
            ),
            apps_config=AppsConfig(
                quick_start_config=OpenWebUIConfig(
                    openweb_quickstart=True,
                    llm_config=LLMConfig(
                        model=PreConfiguredHuggingFaceLLMModel(
                            model=PreConfiguredLLMModels.LLAMA_31_8b
                        ),
                        llm_preset=Preset(name="gpu-small"),
                        ui_preset=Preset(name="cpu-small"),
                    ),
                    postgres_config=PostgresConfig(
                        preset=Preset(name="cpu-small"),
                    ),
                    embeddings_config=TextEmbeddingsConfig(
                        model=PreConfiguredEmbeddingsModels.BAAI_BGE_M3,
                        preset=Preset(name="gpu-small"),
                    ),
                ),
            ),
        ),
        app_name="launchpad-app",
        namespace="default-namespace",
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    # Validate the complete helm_params structure at once
    expected_helm_params = {
        "preset_name": "cpu-small",
        "resources": {
            "requests": {"cpu": "2000.0m", "memory": "0M"},
            "limits": {"cpu": "2000.0m", "memory": "0M"},
        },
        "tolerations": [
            {
                "effect": "NoSchedule",
                "key": "platform.neuromation.io/job",
                "operator": "Exists",
            },
            {
                "effect": "NoExecute",
                "key": "node.kubernetes.io/not-ready",
                "operator": "Exists",
                "tolerationSeconds": 300,
            },
            {
                "effect": "NoExecute",
                "key": "node.kubernetes.io/unreachable",
                "operator": "Exists",
                "tolerationSeconds": 300,
            },
        ],
        "affinity": {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "platform.neuromation.io/nodepool",
                                    "operator": "In",
                                    "values": ["cpu_pool"],
                                }
                            ]
                        }
                    ]
                }
            }
        },
        "podLabels": {
            "platform.apolo.us/component": "app",
            "platform.apolo.us/preset": "cpu-small",
        },
        "apolo_app_id": APP_ID,
        "LAUNCHPAD_INITIAL_CONFIG": json.dumps(
            {
                "vllm": {
                    "hugging_face_model": {
                        "model_hf_name": "meta-llama/Llama-3.1-8B-Instruct",
                        "hf_token": None,
                        "__type__": "HuggingFaceModel",
                    },
                    "preset": {"name": "gpu-small", "__type__": "Preset"},
                    "server_extra_args": [],
                    "cache_config": {
                        "files_path": {
                            "path": "storage:.apps/hugging-face-cache",
                            "__type__": "ApoloFilesPath",
                        },
                        "__type__": "HuggingFaceCache",
                    },
                },
                "postgres": {
                    "preset": {"name": "cpu-small", "__type__": "Preset"},
                    "pg_bouncer": {
                        "preset": {"name": "cpu-small", "__type__": "Preset"},
                    },
                },
                "text-embeddings": {
                    "model": {
                        "model_hf_name": "BAAI/bge-m3",
                        "hf_token": None,
                        "__type__": "HuggingFaceModel",
                    },
                    "preset": {"name": "gpu-small", "__type__": "Preset"},
                    "server_extra_args": [],
                },
            }
        ),
    }

    # Assert each main key separately
    assert helm_params["preset_name"] == expected_helm_params["preset_name"]
    assert helm_params["resources"] == expected_helm_params["resources"]
    assert helm_params["tolerations"] == expected_helm_params["tolerations"]
    assert helm_params["affinity"] == expected_helm_params["affinity"]
    assert helm_params["podLabels"] == expected_helm_params["podLabels"]
    assert helm_params["apolo_app_id"] == expected_helm_params["apolo_app_id"]
    assert (
        helm_params["LAUNCHPAD_INITIAL_CONFIG"]
        == expected_helm_params["LAUNCHPAD_INITIAL_CONFIG"]
    )

    # Check that dynamic fields are present
    assert "dbPassword" in helm_params
    assert "dbSecretName" in helm_params
    assert "domain" in helm_params
    assert "keycloak" in helm_params
    assert "postgresql" in helm_params

    # Test keycloak fields
    assert "fullnameOverride" in helm_params["keycloak"]
    assert helm_params["keycloak"]["fullnameOverride"] == f"launchpad-{APP_ID}-keycloak"
    assert helm_params["keycloak"]["preset_name"] == expected_helm_params["preset_name"]
    assert helm_params["keycloak"]["resources"] == expected_helm_params["resources"]
    assert helm_params["keycloak"]["tolerations"] == expected_helm_params["tolerations"]
    assert helm_params["keycloak"]["affinity"] == expected_helm_params["affinity"]
    assert helm_params["keycloak"]["podLabels"] == expected_helm_params["podLabels"]
    assert (
        helm_params["keycloak"]["apolo_app_id"] == expected_helm_params["apolo_app_id"]
    )

    assert "fullnameOverride" in helm_params["mlops-keycloak"]
    assert (
        helm_params["mlops-keycloak"]["fullnameOverride"]
        == f"launchpad-{APP_ID}-keycloak"
    )
    assert (
        helm_params["mlops-keycloak"]["preset_name"]
        == expected_helm_params["preset_name"]
    )
    assert (
        helm_params["mlops-keycloak"]["resources"] == expected_helm_params["resources"]
    )
    assert (
        helm_params["mlops-keycloak"]["tolerations"]
        == expected_helm_params["tolerations"]
    )
    assert helm_params["mlops-keycloak"]["affinity"] == expected_helm_params["affinity"]
    assert (
        helm_params["mlops-keycloak"]["podLabels"] == expected_helm_params["podLabels"]
    )
    assert (
        helm_params["mlops-keycloak"]["apolo_app_id"]
        == expected_helm_params["apolo_app_id"]
    )

    # Test postgres fields
    assert "fullnameOverride" in helm_params["postgresql"]
    assert helm_params["postgresql"]["fullnameOverride"] == f"launchpad-{APP_ID}-db"


@pytest.mark.asyncio
async def test_launchpad_values_generation_with_huggingface_model(setup_clients):
    """Test launchpad helm values generation with a HuggingFace LLM model."""
    from apolo_app_types import HuggingFaceModel

    processor = LaunchpadInputsProcessor(client=setup_clients)
    helm_params = await processor.gen_extra_values(
        input_=LaunchpadAppInputs(
            launchpad_web_app_config=LaunchpadWebAppConfig(
                preset=Preset(name="cpu-small"),
            ),
            apps_config=AppsConfig(
                quick_start_config=OpenWebUIConfig(
                    openweb_quickstart=True,
                    llm_config=LLMConfig(
                        model=HuggingFaceLLMModel(
                            hf_model=HuggingFaceModel(
                                model_hf_name="microsoft/DialoGPT-medium",
                            ),
                            server_extra_args=[
                                "--max-model-len=2048",
                                "--gpu-memory-utilization=0.9",
                            ],
                        ),
                        llm_preset=Preset(name="gpu-large"),
                        ui_preset=Preset(name="cpu-medium"),
                    ),
                    postgres_config=PostgresConfig(
                        preset=Preset(name="cpu-small"),
                    ),
                    embeddings_config=TextEmbeddingsConfig(
                        model=PreConfiguredEmbeddingsModels.BAAI_BGE_M3,
                        preset=Preset(name="gpu-small"),
                    ),
                ),
            ),
        ),
        app_name="launchpad-app",
        namespace="default-namespace",
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    # Validate the complete helm_params structure at once
    expected_helm_params = {
        "preset_name": "cpu-small",
        "resources": {
            "requests": {"cpu": "2000.0m", "memory": "0M"},
            "limits": {"cpu": "2000.0m", "memory": "0M"},
        },
        "tolerations": [
            {
                "effect": "NoSchedule",
                "key": "platform.neuromation.io/job",
                "operator": "Exists",
            },
            {
                "effect": "NoExecute",
                "key": "node.kubernetes.io/not-ready",
                "operator": "Exists",
                "tolerationSeconds": 300,
            },
            {
                "effect": "NoExecute",
                "key": "node.kubernetes.io/unreachable",
                "operator": "Exists",
                "tolerationSeconds": 300,
            },
        ],
        "affinity": {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "platform.neuromation.io/nodepool",
                                    "operator": "In",
                                    "values": ["cpu_pool"],
                                }
                            ]
                        }
                    ]
                }
            }
        },
        "podLabels": {
            "platform.apolo.us/component": "app",
            "platform.apolo.us/preset": "cpu-small",
        },
        "apolo_app_id": APP_ID,
        "LAUNCHPAD_INITIAL_CONFIG": json.dumps(
            {
                "vllm": {
                    "hugging_face_model": {
                        "model_hf_name": "microsoft/DialoGPT-medium",
                        "hf_token": None,
                        "__type__": "HuggingFaceModel",
                    },
                    "preset": {"name": "gpu-large", "__type__": "Preset"},
                    "server_extra_args": [
                        "--max-model-len=2048",
                        "--gpu-memory-utilization=0.9",
                    ],
                    "cache_config": {
                        "files_path": {
                            "path": "storage:.apps/hugging-face-cache",
                            "__type__": "ApoloFilesPath",
                        },
                        "__type__": "HuggingFaceCache",
                    },
                },
                "postgres": {
                    "preset": {"name": "cpu-small", "__type__": "Preset"},
                    "pg_bouncer": {
                        "preset": {"name": "cpu-small", "__type__": "Preset"},
                    },
                },
                "text-embeddings": {
                    "model": {
                        "model_hf_name": "BAAI/bge-m3",
                        "hf_token": None,
                        "__type__": "HuggingFaceModel",
                    },
                    "preset": {"name": "gpu-small", "__type__": "Preset"},
                    "server_extra_args": [],
                },
            }
        ),
    }

    # Assert each main key separately
    assert helm_params["preset_name"] == expected_helm_params["preset_name"]
    assert helm_params["resources"] == expected_helm_params["resources"]
    assert helm_params["tolerations"] == expected_helm_params["tolerations"]
    assert helm_params["affinity"] == expected_helm_params["affinity"]
    assert helm_params["podLabels"] == expected_helm_params["podLabels"]
    assert helm_params["apolo_app_id"] == expected_helm_params["apolo_app_id"]
    assert (
        helm_params["LAUNCHPAD_INITIAL_CONFIG"]
        == expected_helm_params["LAUNCHPAD_INITIAL_CONFIG"]
    )

    # Check that dynamic fields are present
    assert "dbPassword" in helm_params
    assert "dbSecretName" in helm_params
    assert "domain" in helm_params
    assert "keycloak" in helm_params
    assert "postgresql" in helm_params

    # Test keycloak fields
    assert "fullnameOverride" in helm_params["keycloak"]
    assert helm_params["keycloak"]["fullnameOverride"] == f"launchpad-{APP_ID}-keycloak"

    # Test postgres fields
    assert "fullnameOverride" in helm_params["postgresql"]
    assert helm_params["postgresql"]["fullnameOverride"] == f"launchpad-{APP_ID}-db"


@pytest.mark.asyncio
async def test_launchpad_values_generation_with_custom_model(setup_clients):
    """Test launchpad helm values generation with a custom LLM model."""
    # Custom models are now supported
    processor = LaunchpadInputsProcessor(client=setup_clients)
    helm_params = await processor.gen_extra_values(
        input_=LaunchpadAppInputs(
            launchpad_web_app_config=LaunchpadWebAppConfig(
                preset=Preset(name="cpu-small"),
            ),
            apps_config=AppsConfig(
                quick_start_config=OpenWebUIConfig(
                    openweb_quickstart=True,
                    llm_config=LLMConfig(
                        model=CustomLLMModel(
                            model_name="my-custom-model",
                            model_apolo_path=ApoloFilesPath(
                                path="storage://cluster/org/project/models/my-model"
                            ),
                            server_extra_args=[
                                "--max-model-len",
                                "4096",
                                "--tensor-parallel-size",
                                "2",
                            ],
                        ),
                        llm_preset=Preset(name="gpu-xlarge"),
                        ui_preset=Preset(name="cpu-small"),
                    ),
                    postgres_config=PostgresConfig(
                        preset=Preset(name="cpu-small"),
                    ),
                    embeddings_config=TextEmbeddingsConfig(
                        model=PreConfiguredEmbeddingsModels.BAAI_BGE_M3,
                        preset=Preset(name="gpu-small"),
                    ),
                ),
            ),
        ),
        app_name="launchpad-app",
        namespace="default-namespace",
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    # Validate that custom model configuration works
    expected_vllm_config = {
        "hugging_face_model": {
            "model_hf_name": "my-custom-model",
            "hf_token": None,
            "__type__": "HuggingFaceModel",
        },
        "preset": {"name": "gpu-xlarge", "__type__": "Preset"},
        "server_extra_args": [
            "--max-model-len",
            "4096",
            "--tensor-parallel-size",
            "2",
        ],
        "cache_config": {
            "files_path": {
                "path": "storage://cluster/org/project/models/my-model",
                "__type__": "ApoloFilesPath",
            },
            "__type__": "HuggingFaceCache",
        },
    }

    # Check that the custom model configuration is correct
    launchpad_web_app_config = json.loads(helm_params["LAUNCHPAD_INITIAL_CONFIG"])
    assert launchpad_web_app_config["vllm"] == expected_vllm_config

    # Check that dynamic fields are present
    assert "dbPassword" in helm_params
    assert "dbSecretName" in helm_params
    assert "domain" in helm_params
    assert "keycloak" in helm_params
    assert "postgresql" in helm_params


@pytest.mark.asyncio
async def test_launchpad_values_generation_magistral_model(setup_clients):
    """Test launchpad helm values generation with Magistral pre-configured model."""
    processor = LaunchpadInputsProcessor(client=setup_clients)
    helm_params = await processor.gen_extra_values(
        input_=LaunchpadAppInputs(
            launchpad_web_app_config=LaunchpadWebAppConfig(
                preset=Preset(name="cpu-medium"),
            ),
            apps_config=AppsConfig(
                quick_start_config=OpenWebUIConfig(
                    openweb_quickstart=True,
                    llm_config=LLMConfig(
                        model=PreConfiguredHuggingFaceLLMModel(
                            model=PreConfiguredLLMModels.MAGISTRAL_24B
                        ),
                        llm_preset=Preset(name="gpu-medium"),
                        ui_preset=Preset(name="cpu-small"),
                    ),
                    postgres_config=PostgresConfig(
                        preset=Preset(name="cpu-small"),
                    ),
                    embeddings_config=TextEmbeddingsConfig(
                        model=PreConfiguredEmbeddingsModels.BAAI_BGE_M3,
                        preset=Preset(name="gpu-small"),
                    ),
                ),
            ),
        ),
        app_name="launchpad-app",
        namespace="default-namespace",
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    # Validate the complete helm_params structure at once
    expected_helm_params = {
        "preset_name": "cpu-medium",
        "resources": {
            "requests": {"cpu": "2000.0m", "memory": "0M"},
            "limits": {"cpu": "2000.0m", "memory": "0M"},
        },
        "tolerations": [
            {
                "effect": "NoSchedule",
                "key": "platform.neuromation.io/job",
                "operator": "Exists",
            },
            {
                "effect": "NoExecute",
                "key": "node.kubernetes.io/not-ready",
                "operator": "Exists",
                "tolerationSeconds": 300,
            },
            {
                "effect": "NoExecute",
                "key": "node.kubernetes.io/unreachable",
                "operator": "Exists",
                "tolerationSeconds": 300,
            },
        ],
        "affinity": {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "platform.neuromation.io/nodepool",
                                    "operator": "In",
                                    "values": ["cpu_pool"],
                                }
                            ]
                        }
                    ]
                }
            }
        },
        "podLabels": {
            "platform.apolo.us/component": "app",
            "platform.apolo.us/preset": "cpu-medium",
        },
        "apolo_app_id": APP_ID,
        "LAUNCHPAD_INITIAL_CONFIG": json.dumps(
            {
                "vllm": {
                    "hugging_face_model": {
                        "model_hf_name": "unsloth/Magistral-Small-2506-GGUF",
                        "hf_token": None,
                        "__type__": "HuggingFaceModel",
                    },
                    "preset": {"name": "gpu-medium", "__type__": "Preset"},
                    "server_extra_args": [
                        "--tokenizer_mode=mistral",
                        "--config_format=mistral",
                        "--load_format=mistral",
                        "--tool-call-parser=mistral",
                        "--enable-auto-tool-choice",
                        "--tensor-parallel-size=2",
                    ],
                    "cache_config": {
                        "files_path": {
                            "path": "storage:.apps/hugging-face-cache",
                            "__type__": "ApoloFilesPath",
                        },
                        "__type__": "HuggingFaceCache",
                    },
                },
                "postgres": {
                    "preset": {"name": "cpu-small", "__type__": "Preset"},
                    "pg_bouncer": {
                        "preset": {"name": "cpu-small", "__type__": "Preset"},
                    },
                },
                "text-embeddings": {
                    "model": {
                        "model_hf_name": "BAAI/bge-m3",
                        "hf_token": None,
                        "__type__": "HuggingFaceModel",
                    },
                    "preset": {"name": "gpu-small", "__type__": "Preset"},
                    "server_extra_args": [],
                },
            }
        ),
    }

    # Check that dynamic fields are present
    assert "dbPassword" in helm_params
    assert "dbSecretName" in helm_params
    assert "domain" in helm_params
    assert "keycloak" in helm_params
    assert "postgresql" in helm_params

    # Assert each main key separately
    assert helm_params["preset_name"] == expected_helm_params["preset_name"]
    assert helm_params["resources"] == expected_helm_params["resources"]
    assert helm_params["tolerations"] == expected_helm_params["tolerations"]
    assert helm_params["affinity"] == expected_helm_params["affinity"]
    assert helm_params["podLabels"] == expected_helm_params["podLabels"]
    assert helm_params["apolo_app_id"] == expected_helm_params["apolo_app_id"]
    assert (
        helm_params["LAUNCHPAD_INITIAL_CONFIG"]
        == expected_helm_params["LAUNCHPAD_INITIAL_CONFIG"]
    )

    # Test keycloak fields
    assert "fullnameOverride" in helm_params["keycloak"]
    assert helm_params["keycloak"]["fullnameOverride"] == f"launchpad-{APP_ID}-keycloak"

    # Test postgres fields
    assert "fullnameOverride" in helm_params["postgresql"]
    assert helm_params["postgresql"]["fullnameOverride"] == f"launchpad-{APP_ID}-db"
