ARG PY_VERSION=3.13.1

FROM python:${PY_VERSION}-slim-bullseye as builder

WORKDIR /app

ENV PYTHONPATH=/app \
    POETRY_NO_INTERACTION=1\
    POETRY_CACHE_DIR=/tmp/poetry-cache \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1

RUN apt-get update && apt-get install -y git make && rm -rf /var/lib/apt/lists/*

RUN pip3 install --disable-pip-version-check --no-cache-dir poetry==2.1.3

COPY poetry.lock pyproject.toml Makefile /app/

RUN poetry install --only main && rm -rf /tmp/poetry-cache

FROM python:${PY_VERSION}-slim-bullseye as runtime

LABEL org.opencontainers.image.source = "https://github.com/neuro-inc/launchpad"

ENV SERVICE_NAME="launchpad"

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

COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

COPY launchpad /app/launchpad
COPY scripts /app/scripts

ENTRYPOINT ["python", "-m", "launchpad"]
