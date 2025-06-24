FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"

COPY pyproject.toml README.md ./

RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv sync

COPY src ./src
# COPY tests ./tests

ENV PYTHONPATH=/app/src

ENTRYPOINT ["uv", "run", "exchange-connector"]