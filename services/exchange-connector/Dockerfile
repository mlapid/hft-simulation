FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PATH="/app/services/exchange-connector/.venv/bin:$PATH" \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

COPY services/exchange-connector/pyproject.toml \
     services/exchange-connector/uv.lock \
     services/exchange-connector/README.md \
     /app/services/exchange-connector/

COPY libs/common/pyproject.toml \
     libs/common/uv.lock \
     libs/common/README.md \
     /app/libs/common/

COPY libs/common/src /app/libs/common/src
COPY services/exchange-connector/src /app/services/exchange-connector/src

WORKDIR /app/services/exchange-connector

RUN uv sync --frozen --no-dev

ENTRYPOINT ["uv", "run", "exchange-connector"]