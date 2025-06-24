import os

from loguru import logger


def main() -> None:
    token_file = os.getenv('GRAFANA_TOKEN_FILE')
    with open(token_file, 'r') as f:
        grafana_token = f.read().strip()

    logger.info(f"Grafana token: {grafana_token}")
