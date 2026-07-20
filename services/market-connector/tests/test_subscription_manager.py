import asyncio
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any, cast

import pytest

from market_connector.adapters.deribit.mapper import DeribitBookLevel, DeribitBookUpdate
from market_connector.domain.events import SubscriptionEvent
from market_connector.domain.subscriptions import SubscriptionKey
from market_connector.subscriptions.manager import (
    SubscriptionManager,
    SubscriptionNotFoundError,
)


class FakeBookAdapter:
    def __init__(self) -> None:
        self.is_connected: bool = False
        self.connect_calls: int = 0
        self.disconnect_calls: int = 0
        self.subscribed_books: list[str] = []
        self.unsubscribed_books: list[str] = []
        self.book_event_consumers: int = 0
        self._book_events: asyncio.Queue[DeribitBookUpdate | Exception] = asyncio.Queue()

    async def connect(self) -> None:
        self.connect_calls += 1
        self.is_connected = True

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        self.is_connected = False

    async def subscribe_book(self, instrument_name: str) -> str:
        self.subscribed_books.append(instrument_name)
        return f'book.{instrument_name}.none.10.100ms'

    async def unsubscribe_book(self, instrument_name: str) -> str:
        self.unsubscribed_books.append(instrument_name)
        return f'book.{instrument_name}.none.10.100ms'

    async def book_events(self) -> AsyncIterator[DeribitBookUpdate]:
        self.book_event_consumers += 1
        while True:
            item = await self._book_events.get()
            if isinstance(item, Exception):
                raise item

            yield item

    def queue_book_event(self, event: DeribitBookUpdate) -> None:
        self._book_events.put_nowait(event)

    def queue_error(self, error: Exception) -> None:
        self._book_events.put_nowait(error)


class FakeEventSink:
    def __init__(self) -> None:
        self.events: list[SubscriptionEvent] = []
        self.is_closed = False

    async def publish(self, event: SubscriptionEvent) -> None:
        self.events.append(event)

    async def close(self) -> None:
        self.is_closed = True


def book_update(instrument_name: str) -> DeribitBookUpdate:
    return DeribitBookUpdate(
        instrument_name=instrument_name,
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


async def next_event(
    events: AsyncIterator[SubscriptionEvent],
) -> SubscriptionEvent:
    return await anext(events)


async def wait_for_sink_events(
    sink: FakeEventSink,
    count: int,
) -> list[SubscriptionEvent]:
    for _ in range(10):
        if len(sink.events) >= count:
            return sink.events

        await asyncio.sleep(0.01)

    raise AssertionError(f'Expected {count} sink event(s), got {len(sink.events)}')


@pytest.mark.asyncio
async def test_subscribe_book_connects_and_deduplicates_upstream_subscription():
    adapter = FakeBookAdapter()
    manager = SubscriptionManager(adapter=adapter)

    key = await manager.subscribe_book('btc-perpetual')
    duplicate_key = await manager.subscribe_book('BTC-PERPETUAL')

    assert key == SubscriptionKey.book('BTC-PERPETUAL')
    assert duplicate_key == key
    assert adapter.connect_calls == 1
    assert adapter.subscribed_books == ['BTC-PERPETUAL']
    assert manager.active_subscriptions[0].key == key
    assert manager.active_subscriptions[0].ref_count == 2

    await manager.disconnect()


@pytest.mark.asyncio
async def test_unsubscribe_releases_reference_and_unsubscribes_on_last_reference():
    adapter = FakeBookAdapter()
    manager = SubscriptionManager(adapter=adapter)
    key = await manager.subscribe_book('BTC-PERPETUAL')
    await manager.subscribe_book('BTC-PERPETUAL')

    await manager.unsubscribe(key)

    assert adapter.unsubscribed_books == []
    assert manager.active_subscriptions[0].ref_count == 1

    await manager.unsubscribe(key)

    assert adapter.unsubscribed_books == ['BTC-PERPETUAL']
    assert manager.active_subscriptions == ()

    await manager.disconnect()


@pytest.mark.asyncio
async def test_stream_fans_out_book_events_to_multiple_consumers():
    adapter = FakeBookAdapter()
    manager = SubscriptionManager(adapter=adapter)
    key = await manager.subscribe_book('BTC-PERPETUAL')

    first_stream = manager.stream(key)
    second_stream = manager.stream(key)
    first_task = asyncio.create_task(next_event(first_stream))
    second_task = asyncio.create_task(next_event(second_stream))
    await asyncio.sleep(0)

    update = book_update('BTC-PERPETUAL')
    adapter.queue_book_event(update)

    try:
        first_event = await asyncio.wait_for(first_task, timeout=1)
        second_event = await asyncio.wait_for(second_task, timeout=1)

        assert first_event == SubscriptionEvent(subscription=key, payload=update)
        assert second_event == SubscriptionEvent(subscription=key, payload=update)
        assert adapter.book_event_consumers == 1

    finally:
        await cast(Any, first_stream).aclose()
        await cast(Any, second_stream).aclose()
        await manager.disconnect()


@pytest.mark.asyncio
async def test_subscribe_book_publishes_events_to_sinks():
    adapter = FakeBookAdapter()
    sink = FakeEventSink()
    manager = SubscriptionManager(
        adapter=adapter,
        event_sinks=[sink],
    )
    key = await manager.subscribe_book('BTC-PERPETUAL')

    update = book_update('BTC-PERPETUAL')
    adapter.queue_book_event(update)

    events = await wait_for_sink_events(sink, count=1)

    assert events == [
        SubscriptionEvent(
            subscription=key,
            payload=update,
        )
    ]

    await manager.disconnect()
    assert sink.is_closed is True


@pytest.mark.asyncio
async def test_stream_ignores_events_for_other_subscriptions():
    adapter = FakeBookAdapter()
    manager = SubscriptionManager(adapter=adapter)
    key = await manager.subscribe_book('BTC-PERPETUAL')

    stream = manager.stream(key)
    event_task = asyncio.create_task(next_event(stream))
    await asyncio.sleep(0)

    adapter.queue_book_event(book_update('ETH-PERPETUAL'))
    await asyncio.sleep(0)

    assert not event_task.done()

    adapter.queue_book_event(book_update('BTC-PERPETUAL'))

    try:
        event = await asyncio.wait_for(event_task, timeout=1)
        assert event.subscription == key
        assert event.payload.instrument_name == 'BTC-PERPETUAL'

    finally:
        await cast(Any, stream).aclose()
        await manager.disconnect()


@pytest.mark.asyncio
async def test_unsubscribe_closes_consumers_for_subscription():
    adapter = FakeBookAdapter()
    manager = SubscriptionManager(adapter=adapter)
    key = await manager.subscribe_book('BTC-PERPETUAL')

    stream = manager.stream(key)
    event_task = asyncio.create_task(next_event(stream))
    await asyncio.sleep(0)

    await manager.unsubscribe(key)

    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(event_task, timeout=1)

    await manager.disconnect()


@pytest.mark.asyncio
async def test_stream_rejects_inactive_subscription():
    adapter = FakeBookAdapter()
    manager = SubscriptionManager(adapter=adapter)
    key = SubscriptionKey.book('BTC-PERPETUAL')

    with pytest.raises(SubscriptionNotFoundError):
        async for _event in manager.stream(key):
            raise AssertionError('stream should not yield')


@pytest.mark.asyncio
async def test_adapter_event_errors_are_broadcast_to_consumers():
    adapter = FakeBookAdapter()
    manager = SubscriptionManager(adapter=adapter)
    key = await manager.subscribe_book('BTC-PERPETUAL')

    stream = manager.stream(key)
    event_task = asyncio.create_task(next_event(stream))
    await asyncio.sleep(0)

    adapter.queue_error(RuntimeError('adapter failed'))

    try:
        with pytest.raises(RuntimeError, match='adapter failed'):
            await asyncio.wait_for(event_task, timeout=1)

    finally:
        await cast(Any, stream).aclose()
        await manager.disconnect()
