from loguru import logger

from common.settings import Settings


settings: Settings = Settings()


def main() -> None:
    logger.info(f'Grafana host: {settings.grafana_host}')
    logger.info(f'Grafana port: {settings.grafana_port}')
    logger.info(f'Grafana user: {settings.grafana_user}')
    logger.info(f'Grafana password: {settings.grafana_password}')
    logger.info(f'Grafana token: {settings.grafana_token}')
