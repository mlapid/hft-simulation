FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PATH="/app/.venv/bin:$PATH" \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

COPY pyproject.toml uv.lock /app/

COPY services/exchange-connector/pyproject.toml services/exchange-connector/README.md /app/services/exchange-connector/
COPY libs/common/pyproject.toml libs/common/README.md /app/libs/common/

COPY libs/common/src /app/libs/common/src
COPY libs/common/tests /app/libs/common/tests
COPY services/exchange-connector/src /app/services/exchange-connector/src
COPY services/exchange-connector/entrypoint.sh /app/services/exchange-connector/entrypoint.sh

RUN uv sync --frozen --no-dev --package exchange-connector

ENTRYPOINT ["bash", "/app/services/exchange-connector/entrypoint.sh"]