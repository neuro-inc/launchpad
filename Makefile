.PHONY: all test clean
all test clean:

IMAGE_NAME ?= launchpad
HOOK_IMAGE_NAME ?= launchpad-hook
KEYCLOAK_IMAGE_NAME ?= launchpad-keycloak
HELM_RELEASE_NAME ?= launchpad
HELM_CHART_PATH ?= charts/launchpad
HELM_TEST_VALUES ?= charts/launchpad/ci/procore-values.yaml
HELM_TEMPLATE_OUTPUT ?= /tmp/launchpad-helm-template.yaml

SHELL := /bin/sh -e

.PHONY: install
install: poetry.lock
	poetry config virtualenvs.in-project true
	poetry install
	poetry run pre-commit install;


dist:
	poetry build -f wheel;


.PHONY: format
format:
ifdef CI
	poetry run pre-commit run --all-files --show-diff-on-failure
else
	# automatically fix the formatting issues and rerun again
	poetry run pre-commit run --all-files || poetry run pre-commit run --all-files
endif

.PHONY: lint
lint: format
	poetry run mypy launchpad tests


.PHONY: test-unit
test-unit:
	poetry run pytest -vvs --cov=launchpad --cov-report xml:.coverage.unit.xml tests/unit

.PHONY: test-integration
test-integration:
	poetry run pytest -vv --cov=launchpad --cov-report xml:.coverage.integration.xml tests/integration

.PHONY: test-hooks
test-hooks:
	cd hooks && \
	poetry run pytest -vv --cov=apolo_apps_launchpad --cov-report xml:.coverage.hooks.xml tests/unit

.PHONY: test-hooks-lint
test-hooks-lint:
	cd hooks && \
	poetry run ruff check .

.PHONY: test-hooks-format
test-hooks-format:
	cd hooks && \
	poetry run ruff format --check .

.PHONY: test-keycloak-idp
test-keycloak-idp:
	cd keycloak-procore-idp && \
	mvn -B -ntp test

.PHONY: test-helm-lint
test-helm-lint:
	helm lint $(HELM_CHART_PATH) -f $(HELM_TEST_VALUES)

.PHONY: test-helm-template
test-helm-template:
	helm template $(HELM_RELEASE_NAME) $(HELM_CHART_PATH) -f $(HELM_TEST_VALUES) > $(HELM_TEMPLATE_OUTPUT)
	test -s $(HELM_TEMPLATE_OUTPUT)

.PHONY: test-helm-unittest
test-helm-unittest:
	helm unittest $(HELM_CHART_PATH)

.PHONY: test-helm-ct
test-helm-ct:
	ct lint --config .ct.yaml --all

.PHONY: test-helm
test-helm: test-helm-lint test-helm-template test-helm-unittest test-helm-ct

.PHONY: hooks-install
hooks-install:
	cd hooks && \
	poetry config virtualenvs.in-project true && \
	poetry install

.PHONY: test-all
test-all: test-unit test-integration test-hooks test-keycloak-idp test-helm

.PHONY: build-image
build-image:
	docker build \
		--target runtime \
		-t $(IMAGE_NAME):latest \
		-f Dockerfile \
		.;

.PHONY: push-image
push-image:
	docker tag $(IMAGE_NAME):latest ghcr.io/neuro-inc/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push ghcr.io/neuro-inc/$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: build-hook-image
build-hook-image:
	docker build \
		--build-arg APP_IMAGE_TAG=$(APP_IMAGE_TAG) \
		-t $(HOOK_IMAGE_NAME):latest \
		-f ./hooks/hooks.Dockerfile \
		.;

.PHONY: push-hook-image
push-hook-image:
	docker tag $(HOOK_IMAGE_NAME):latest ghcr.io/neuro-inc/$(HOOK_IMAGE_NAME):$(IMAGE_TAG)
	docker push ghcr.io/neuro-inc/$(HOOK_IMAGE_NAME):$(IMAGE_TAG)

.PHONY: build-keycloak-image
build-keycloak-image:
	docker build \
		--target keycloak-runtime \
		-t $(KEYCLOAK_IMAGE_NAME):latest \
		-f Dockerfile \
		.;

.PHONY: push-keycloak-image
push-keycloak-image:
	docker tag $(KEYCLOAK_IMAGE_NAME):latest ghcr.io/neuro-inc/$(KEYCLOAK_IMAGE_NAME):$(IMAGE_TAG)
	docker push ghcr.io/neuro-inc/$(KEYCLOAK_IMAGE_NAME):$(IMAGE_TAG)

.PHONY: gen-types-schemas
gen-types-schemas:
	app-types dump-types-schema .apolo/src/apolo_apps_launchpad LaunchpadAppInputs .apolo/src/apolo_apps_launchpad/schemas/LaunchpadAppInputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_launchpad LaunchpadAppOutputs .apolo/src/apolo_apps_launchpad/schemas/LaunchpadAppOutputs.json
