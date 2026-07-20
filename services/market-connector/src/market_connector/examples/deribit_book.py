import asyncio

from loguru import logger

from market_connector.adapters.deribit.adapter import DeribitAdapter


async def run() -> None:
    async with DeribitAdapter(is_test=True) as adapter:
        async for book in adapter.book_updates('BTC-PERPETUAL'):
            logger.info(book)


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info('Interrupted by user.')
