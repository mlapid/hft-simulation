import asyncio
from contextlib import AsyncExitStack

from loguru import logger

from common.settings import Settings

from common.redis.redis_producer import RedisProducer
from exchange_connector.connectors.deribit_connector import DeribitConnector


settings: Settings = Settings()

async def run() -> None:

    async with AsyncExitStack() as stack:
        redis_producer = await stack.enter_async_context(await RedisProducer.connect('deribit'))
        connector = await stack.enter_async_context(await DeribitConnector.connect(is_test=False))

        await connector.subscribe(channels=['book.BTC-PERPETUAL.none.10.100ms'])
        await connector.set_heartbeat(interval=10)

        async for message in connector.receive():
            logger.info(f'Received message: {message}')

            await redis_producer.send_message(message.model_dump_json())

def main() -> None:
    logger.info('Exchange connector started.')

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info('Interrupted by user.')
    logger.info('Exchange connector stopped.')

if __name__ == '__main__':
    main()