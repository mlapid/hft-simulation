import asyncio

from loguru import logger

from market_connector.adapters.deribit.adapter import DeribitAdapter
from market_connector.adapters.deribit.channels import DeribitChannels


async def run() -> None:
    btc_channel = DeribitChannels.book('BTC-PERPETUAL')
    eth_channel = DeribitChannels.book('ETH-PERPETUAL')

    async with DeribitAdapter(is_test=True) as adapter:
        await adapter.subscribe([btc_channel, eth_channel])

        async for message in adapter.client.messages():
            if message.get('method') != 'subscription':
                continue

            params = message.get('params', {})
            channel = params.get('channel')
            data = params.get('data')

            if channel == btc_channel:
                logger.info(f'BTC book: {data}')
            elif channel == eth_channel:
                logger.info(f'ETH book: {data}')


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info('Interrupted by user.')
