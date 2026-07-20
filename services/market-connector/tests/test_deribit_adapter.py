import asyncio
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any, cast

import pytest

from market_connector.adapters.deribit.adapter import DeribitAdapter
from market_connector.adapters.deribit.errors import DeribitSubscriptionError
from market_connector.adapters.deribit.mapper import DeribitBookLevel, DeribitBookUpdate


class FakeDeribitClient:
    def __init__(self) -> None:
        self.is_connected: bool = False
        self.connect_calls: list[bool] = []
        self.heartbeat_intervals: list[int] = []
        self.subscribed: list[list[str]] = []
        self.unsubscribed: list[list[str]] = []
        self.disconnected: bool = False
        self.subscribe_result: Any | None = None
        self.unsubscribe_result: Any | None = None
        self._messages: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def connect(self, is_test: bool = False) -> None:
        self.connect_calls.append(is_test)
        self.is_connected = True

    async def disconnect(self) -> None:
        self.disconnected = True
        self.is_connected = False

    async def set_heartbeat(self, interval: int) -> None:
        self.heartbeat_intervals.append(interval)

    async def subscribe(self, channels: list[str]) -> Any:
        self.subscribed.append(channels)
        return self.subscribe_result if self.subscribe_result is not None else channels

    async def unsubscribe(self, channels: list[str]) -> Any:
        self.unsubscribed.append(channels)
        return self.unsubscribe_result if self.unsubscribe_result is not None else channels

    async def messages(self) -> AsyncIterator[dict[str, Any]]:
        while True:
            yield await self._messages.get()

    def queue_message(self, message: dict[str, Any]) -> None:
        self._messages.put_nowait(message)


def adapter_with_fake_client() -> tuple[DeribitAdapter, FakeDeribitClient]:
    client = FakeDeribitClient()
    adapter = DeribitAdapter(client=cast(Any, client), is_test=True)
    return adapter, client


async def next_book_update(
    updates: AsyncIterator[DeribitBookUpdate],
) -> DeribitBookUpdate:
    return await anext(updates)


@pytest.mark.asyncio
async def test_connect_uses_configured_environment_and_heartbeat():
    adapter, client = adapter_with_fake_client()

    await adapter.connect()
    await adapter.connect()

    assert adapter.is_connected is True
    assert client.connect_calls == [True]
    assert client.heartbeat_intervals == [10]


@pytest.mark.asyncio
async def test_context_manager_disconnects_and_clears_subscriptions():
    adapter, client = adapter_with_fake_client()

    async with adapter as active_adapter:
        assert active_adapter is adapter
        await adapter.subscribe_book('BTC-PERPETUAL')

    assert client.disconnected is True
    assert adapter.subscribed_channels == frozenset()


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe_book_track_channel_state():
    adapter, client = adapter_with_fake_client()

    channel = await adapter.subscribe_book('btc-perpetual')

    assert channel == 'book.BTC-PERPETUAL.none.10.100ms'
    assert client.subscribed == [[channel]]
    assert adapter.subscribed_channels == frozenset({channel})

    unsubscribed_channel = await adapter.unsubscribe_book('btc-perpetual')

    assert unsubscribed_channel == channel
    assert client.unsubscribed == [[channel]]
    assert adapter.subscribed_channels == frozenset()


@pytest.mark.asyncio
async def test_book_updates_subscribes_and_yields_matching_channel_data():
    adapter, client = adapter_with_fake_client()
    channel = 'book.BTC-PERPETUAL.none.10.100ms'
    payload = {
        'timestamp': 1535098298227,
        'instrument_name': 'BTC-PERPETUAL',
        'change_id': 123456,
        'bids': [[50000.0, 10.5]],
        'asks': [[50001.0, 8.3]],
    }
    expected_update = DeribitBookUpdate(
        instrument_name='BTC-PERPETUAL',
        timestamp=1535098298227,
        change_id=123456,
        bids=(
            DeribitBookLevel(
                side='bid',
                price=Decimal('50000.0'),
                volume=Decimal('10.5'),
            ),
        ),
        asks=(
            DeribitBookLevel(
                side='ask',
                price=Decimal('50001.0'),
                volume=Decimal('8.3'),
            ),
        ),
    )

    updates = adapter.book_updates('btc-perpetual')
    update_task = asyncio.create_task(next_book_update(updates))
    await asyncio.sleep(0)

    assert client.subscribed == [[channel]]

    client.queue_message({
        'jsonrpc': '2.0',
        'method': 'subscription',
        'params': {
            'channel': 'ticker.BTC-PERPETUAL.100ms',
            'data': {'ignored': True},
        },
    })
    client.queue_message({
        'jsonrpc': '2.0',
        'method': 'subscription',
        'params': {
            'channel': channel,
            'data': payload,
        },
    })

    try:
        assert await asyncio.wait_for(update_task, timeout=1) == expected_update
    finally:
        await cast(Any, updates).aclose()


@pytest.mark.asyncio
async def test_book_events_yields_all_subscribed_book_updates():
    adapter, client = adapter_with_fake_client()
    btc_channel = await adapter.subscribe_book('BTC-PERPETUAL')
    eth_channel = await adapter.subscribe_book('ETH-PERPETUAL')

    events = adapter.book_events()
    event_task = asyncio.create_task(next_book_update(events))
    await asyncio.sleep(0)

    btc_payload = {
        'timestamp': 1535098298227,
        'instrument_name': 'BTC-PERPETUAL',
        'change_id': 123456,
        'bids': [[50000.0, 10.5]],
        'asks': [[50001.0, 8.3]],
    }
    eth_payload = {
        'timestamp': 1535098298228,
        'instrument_name': 'ETH-PERPETUAL',
        'change_id': 123457,
        'bids': [[3000.0, 1.5]],
        'asks': [[3001.0, 2.3]],
    }

    client.queue_message({
        'jsonrpc': '2.0',
        'method': 'subscription',
        'params': {
            'channel': 'trades.BTC-PERPETUAL.raw',
            'data': {'ignored': True},
        },
    })
    client.queue_message({
        'jsonrpc': '2.0',
        'method': 'subscription',
        'params': {
            'channel': btc_channel,
            'data': btc_payload,
        },
    })

    try:
        btc_update = await asyncio.wait_for(event_task, timeout=1)
        assert btc_update.instrument_name == 'BTC-PERPETUAL'
        assert btc_update.change_id == 123456

        next_event_task = asyncio.create_task(next_book_update(events))
        client.queue_message({
            'jsonrpc': '2.0',
            'method': 'subscription',
            'params': {
                'channel': eth_channel,
                'data': eth_payload,
            },
        })

        eth_update = await asyncio.wait_for(next_event_task, timeout=1)
        assert eth_update.instrument_name == 'ETH-PERPETUAL'
        assert eth_update.change_id == 123457

    finally:
        await cast(Any, events).aclose()


@pytest.mark.asyncio
async def test_book_updates_rejects_malformed_book_data():
    adapter, client = adapter_with_fake_client()
    channel = 'book.BTC-PERPETUAL.none.10.100ms'

    updates = adapter.book_updates('BTC-PERPETUAL', subscribe=False)
    update_task = asyncio.create_task(next_book_update(updates))
    await asyncio.sleep(0)

    client.queue_message({
        'jsonrpc': '2.0',
        'method': 'subscription',
        'params': {
            'channel': channel,
            'data': ['not', 'a', 'book', 'object'],
        },
    })

    with pytest.raises(DeribitSubscriptionError, match='must contain an object'):
        await asyncio.wait_for(update_task, timeout=1)


@pytest.mark.asyncio
async def test_subscribe_rejects_unexpected_response_shape():
    adapter, client = adapter_with_fake_client()
    client.subscribe_result = {'channel': 'book.BTC-PERPETUAL.none.10.100ms'}

    with pytest.raises(DeribitSubscriptionError, match='list of channels'):
        await adapter.subscribe_book('BTC-PERPETUAL')
