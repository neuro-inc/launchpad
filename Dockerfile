ARG PY_VERSION=3.13
ARG KEYCLOAK_VERSION=26.3.3-debian-12-r0

FROM maven:3.9.9-eclipse-temurin-21 AS keycloak-procore-idp-builder

WORKDIR /tmp

COPY keycloak-procore-idp/ ./

RUN mvn -B -ntp package

FROM bitnamilegacy/keycloak:${KEYCLOAK_VERSION} AS keycloak-runtime

COPY --from=keycloak-procore-idp-builder /tmp/target/keycloak-procore-idp.jar /opt/bitnami/keycloak/providers/keycloak-procore-idp.jar

RUN /opt/bitnami/keycloak/bin/kc.sh build

FROM python:${PY_VERSION}-slim-bullseye AS builder

WORKDIR /app

ENV PYTHONPATH=/app \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry-cache \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1

RUN apt-get update && apt-get install -y git make libmagic1

RUN pip3 install --disable-pip-version-check --no-cache-dir poetry==2.1.3

COPY poetry.lock pyproject.toml Makefile README.md ./
COPY .apolo ./.apolo
COPY launchpad ./launchpad

RUN poetry install --only main

FROM python:${PY_VERSION}-slim-bullseye AS runtime

LABEL org.opencontainers.image.source="https://github.com/neuro-inc/launchpad"

ENV SERVICE_NAME="launchpad"

RUN apt-get update && apt-get install -y libmagic1 && rm -rf /var/lib/apt/lists/*

RUN addgroup --gid 1001 $SERVICE_NAME && \
    adduser --gid 1001 --shell /bin/false --disabled-password --gecos "" --uid 1001 $SERVICE_NAME && \
    mkdir -p /var/log/$SERVICE_NAME && \
    chown $SERVICE_NAME:$SERVICE_NAME /var/log/$SERVICE_NAME

USER $SERVICE_NAME

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

EXPOSE 8080

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY alembic.ini .
COPY alembic ./alembic

COPY launchpad ./launchpad
COPY scripts ./scripts
COPY .apolo ./.apolo

ENTRYPOINT ["python", "-m", "launchpad"]
