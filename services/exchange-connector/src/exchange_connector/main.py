from loguru import logger

from common.settings import Settings


settings: Settings = Settings()


def main() -> None:
    logger.info('Exchange connector is running...')

if __name__ == '__main__':
    main()