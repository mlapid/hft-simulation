import asyncio
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol

from market_connector.adapters.base import BookAdapter
from market_connector.domain.events import SubscriptionEvent
from market_connector.domain.subscriptions import (
    ExchangeName,
    SubscriptionKey,
    SubscriptionState,
)


class SubscriptionManagerError(Exception):
    '''
    Base class for subscription manager errors.
    '''


class SubscriptionNotFoundError(SubscriptionManagerError):
    '''
    Raised when a subscription is not active.
    '''


class EventSink(Protocol):
    '''
    Destination for normalized subscription events.
    '''

    async def publish(self, event: SubscriptionEvent) -> None:
        '''
        Publish a subscription event.
        '''

    async def close(self) -> None:
        '''
        Close the sink.
        '''


class _Stop:
    pass


_STOP = _Stop()
_QueueItem = Any | Exception | _Stop


@dataclass(slots=True)
class _ManagedSubscription:
    key: SubscriptionKey
    ref_count: int = 1
    consumers: set[asyncio.Queue[_QueueItem]] = field(default_factory=set)


class SubscriptionManager:
    '''
    Manage active subscriptions and fan out adapter events to consumers.
    '''

    def __init__(
        self,
        adapter: BookAdapter,
        *,
        exchange: ExchangeName = 'deribit',
        consumer_queue_size: int = 0,
        event_sinks: Iterable[EventSink] = (),
    ) -> None:
        self._adapter = adapter
        self._exchange = exchange
        self._consumer_queue_size = consumer_queue_size
        self._event_sinks = tuple(event_sinks)
        self._subscriptions: dict[SubscriptionKey, _ManagedSubscription] = {}
        self._event_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    @property
    def active_subscriptions(self) -> tuple[SubscriptionState, ...]:
        '''
        Return public state for all active subscriptions.
        '''

        return tuple(
            SubscriptionState(
                key=state.key,
                ref_count=state.ref_count,
            )
            for state in self._subscriptions.values()
        )

    def get_state(self, key: SubscriptionKey) -> SubscriptionState | None:
        '''
        Return public state for one active subscription.
        '''

        state = self._subscriptions.get(key)
        if state is None:
            return None

        return SubscriptionState(
            key=state.key,
            ref_count=state.ref_count,
        )

    async def connect(self) -> None:
        '''
        Connect the underlying adapter.
        '''

        if not self._adapter.is_connected:
            await self._adapter.connect()

    async def disconnect(self) -> None:
        '''
        Stop event fanout, disconnect the adapter, and close consumers.
        '''

        async with self._lock:
            states = tuple(self._subscriptions.values())
            self._subscriptions.clear()

        await self._stop_event_task()
        await self._adapter.disconnect()
        await self._close_event_sinks()

        for state in states:
            await self._close_consumers(state)

    async def subscribe_book(self, instrument_name: str) -> SubscriptionKey:
        '''
        Subscribe to order-book updates for an instrument.
        '''

        key = SubscriptionKey.book(
            instrument_name=instrument_name,
            exchange=self._exchange,
        )

        async with self._lock:
            state = self._subscriptions.get(key)
            if state is not None:
                state.ref_count += 1
                return key

            if not self._adapter.is_connected:
                await self._adapter.connect()

            await self._adapter.subscribe_book(key.instrument_name)
            self._subscriptions[key] = _ManagedSubscription(key=key)
            self._ensure_event_task_locked()

        return key

    async def unsubscribe(self, key: SubscriptionKey) -> None:
        '''
        Release one reference to an active subscription.
        '''

        stop_event_task = False
        state_to_close: _ManagedSubscription | None = None

        async with self._lock:
            state = self._subscriptions.get(key)
            if state is None:
                raise SubscriptionNotFoundError(f'Subscription is not active: {key}')

            if state.ref_count > 1:
                state.ref_count -= 1
                return

            self._subscriptions.pop(key)
            state_to_close = state
            stop_event_task = not self._subscriptions

        await self._adapter.unsubscribe_book(key.instrument_name)

        if state_to_close is not None:
            await self._close_consumers(state_to_close)

        if stop_event_task:
            await self._stop_event_task()

    async def unsubscribe_book(self, instrument_name: str) -> None:
        '''
        Release one reference to an active order-book subscription.
        '''

        await self.unsubscribe(
            SubscriptionKey.book(
                instrument_name=instrument_name,
                exchange=self._exchange,
            )
        )

    async def stream(self, key: SubscriptionKey) -> AsyncIterator[SubscriptionEvent]:
        '''
        Yield events for an active subscription.
        '''

        queue: asyncio.Queue[_QueueItem] = asyncio.Queue(
            maxsize=self._consumer_queue_size,
        )

        async with self._lock:
            state = self._subscriptions.get(key)
            if state is None:
                raise SubscriptionNotFoundError(f'Subscription is not active: {key}')

            state.consumers.add(queue)

        try:
            while True:
                item = await queue.get()

                if item is _STOP:
                    return

                if isinstance(item, Exception):
                    raise item

                yield SubscriptionEvent(
                    subscription=key,
                    payload=item,
                )

        finally:
            async with self._lock:
                state = self._subscriptions.get(key)
                if state is not None:
                    state.consumers.discard(queue)

    def _ensure_event_task_locked(self) -> None:
        if self._event_task is None or self._event_task.done():
            self._event_task = asyncio.create_task(self._run_events())

    async def _stop_event_task(self) -> None:
        event_task = self._event_task
        self._event_task = None

        if event_task is None or event_task.done():
            return

        event_task.cancel()
        try:
            await event_task
        except asyncio.CancelledError:
            pass

    async def _run_events(self) -> None:
        try:
            async for payload in self._adapter.book_events():
                key = SubscriptionKey.book(
                    instrument_name=payload.instrument_name,
                    exchange=self._exchange,
                )
                event = SubscriptionEvent(
                    subscription=key,
                    payload=payload,
                )
                await self._publish(event)
                await self._broadcast(event)

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            await self._broadcast_all(exc)

    async def _broadcast(self, event: SubscriptionEvent) -> None:
        async with self._lock:
            state = self._subscriptions.get(event.subscription)
            if state is None:
                return

            consumers = tuple(state.consumers)

        for queue in consumers:
            await queue.put(event.payload)

    async def _publish(self, event: SubscriptionEvent) -> None:
        for sink in self._event_sinks:
            await sink.publish(event)

    async def _close_event_sinks(self) -> None:
        for sink in self._event_sinks:
            await sink.close()

    async def _broadcast_all(self, item: Exception) -> None:
        async with self._lock:
            consumers = tuple(
                queue
                for state in self._subscriptions.values()
                for queue in state.consumers
            )

        for queue in consumers:
            await queue.put(item)

    @staticmethod
    async def _close_consumers(state: _ManagedSubscription) -> None:
        consumers = tuple(state.consumers)
        state.consumers.clear()

        for queue in consumers:
            await queue.put(_STOP)
