import asyncio
from typing import NoReturn

from loguru import logger

from common.redis.redis_consumer import RedisConsumer


async def run() -> NoReturn:
    async with await RedisConsumer.connect('test') as consumer:
        async for message in consumer.read_stream():
            logger.info(f'Processing message: {message}')


def main() -> NoReturn:
    logger.info('Processing engine started.')

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info('Interrupted by user.')
    logger.info('Processing engine stopped.')


if __name__ == "__main__":
    main()
