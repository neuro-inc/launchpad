.PHONY: all test clean
all test clean:

IMAGE_NAME ?= launchpad

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
