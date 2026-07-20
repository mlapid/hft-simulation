FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./

ENV UV_LINK_MODE=copy \
    UV_NO_DEV=1

RUN uv sync --locked --no-install-project

COPY src/ src/

RUN uv sync --locked

CMD ["uv", "run", "--no-sync", "market-connector-api"]