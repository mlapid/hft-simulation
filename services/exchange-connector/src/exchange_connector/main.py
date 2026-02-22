import asyncio
from loguru import logger

from common.settings import Settings

from exchange_connector.connectors.deribit_connector import DeribitConnector


settings: Settings = Settings()

async def run() -> None:
    async with await DeribitConnector.connect(is_test=True) as connector:
        await connector.subscribe(channels=['book.ETH-PERPETUAL.none.10.100ms'])
        await connector.set_heartbeat(interval=10)

        async for message in connector.receive():
            logger.info(f'Received message: {message}')

def main() -> None:
    logger.info('Exchange connector started.')

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info('Interrupted by user.')
    logger.info('Exchange connector stopped.')

if __name__ == '__main__':
    main()