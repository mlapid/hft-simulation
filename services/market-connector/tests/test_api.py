from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any, cast

import httpx
import pytest
from fastapi import WebSocket

from market_connector.app.main import create_app
from market_connector.api.routes.streams import stream_book
from market_connector.domain.events import SubscriptionEvent
from market_connector.domain.subscriptions import SubscriptionKey, SubscriptionState
from market_connector.subscriptions.manager import (
    SubscriptionManager,
    SubscriptionNotFoundError,
)


class FakeApiManager:
    def __init__(self) -> None:
        self.disconnected: bool = False
        self._states: dict[SubscriptionKey, int] = {}
        self._stream_events: list[SubscriptionEvent] = []

    @property
    def active_subscriptions(self) -> tuple[SubscriptionState, ...]:
        return tuple(
            SubscriptionState(
                key=key,
                ref_count=ref_count,
            )
            for key, ref_count in self._states.items()
        )

    async def disconnect(self) -> None:
        self.disconnected = True

    async def subscribe_book(self, instrument_name: str) -> SubscriptionKey:
        key = SubscriptionKey.book(instrument_name)
        self._states[key] = self._states.get(key, 0) + 1
        return key

    async def unsubscribe(self, key: SubscriptionKey) -> None:
        ref_count = self._states.get(key)
        if ref_count is None:
            raise SubscriptionNotFoundError(f'Subscription is not active: {key}')

        if ref_count <= 1:
            self._states.pop(key)
            return

        self._states[key] = ref_count - 1

    def get_state(self, key: SubscriptionKey) -> SubscriptionState | None:
        ref_count = self._states.get(key)
        if ref_count is None:
            return None

        return SubscriptionState(
            key=key,
            ref_count=ref_count,
        )

    async def stream(
        self,
        key: SubscriptionKey,
    ) -> AsyncIterator[SubscriptionEvent]:
        if key not in self._states:
            raise SubscriptionNotFoundError(f'Subscription is not active: {key}')

        for event in self._stream_events:
            yield event

    def queue_event(self, event: SubscriptionEvent) -> None:
        self._stream_events.append(event)


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted: bool = False
        self.closed: tuple[int, str] | None = None
        self.sent: list[Any] = []

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.closed = (code, reason or '')

    async def send_json(self, data: Any) -> None:
        self.sent.append(data)


def app_with_manager(
    manager: FakeApiManager,
):
    return create_app(manager=cast(SubscriptionManager, manager))


@pytest.mark.asyncio
async def test_http_health_and_lifespan_disconnects_manager():
    manager = FakeApiManager()
    app = app_with_manager(manager)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url='http://testserver',
        ) as client:
            response = await client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
    assert manager.disconnected is True


@pytest.mark.asyncio
async def test_http_subscription_routes_create_list_and_delete_subscription():
    manager = FakeApiManager()
    app = app_with_manager(manager)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url='http://testserver',
        ) as client:
            created = await client.post(
                '/subscriptions',
                json={
                    'exchange': 'deribit',
                    'type': 'book',
                    'instrument_name': 'btc-perpetual',
                },
            )

            duplicate = await client.post(
                '/subscriptions',
                json={
                    'exchange': 'deribit',
                    'type': 'book',
                    'instrument_name': 'BTC-PERPETUAL',
                },
            )

            listed = await client.get('/subscriptions')
            deleted = await client.delete('/subscriptions/book/btc-perpetual')

    assert created.status_code == 201
    assert created.json() == {
        'key': {
            'exchange': 'deribit',
            'type': 'book',
            'instrument_name': 'BTC-PERPETUAL',
        },
        'ref_count': 1,
    }

    assert duplicate.status_code == 201
    assert duplicate.json()['ref_count'] == 2

    assert listed.status_code == 200
    assert listed.json() == [
        {
            'key': {
                'exchange': 'deribit',
                'type': 'book',
                'instrument_name': 'BTC-PERPETUAL',
            },
            'ref_count': 2,
        }
    ]

    assert deleted.status_code == 204
    assert deleted.content == b''

    state = manager.get_state(SubscriptionKey.book('BTC-PERPETUAL'))
    assert state is not None
    assert state.ref_count == 1
    assert manager.disconnected is True


@pytest.mark.asyncio
async def test_http_delete_subscription_returns_404_for_inactive_subscription():
    manager = FakeApiManager()
    app = app_with_manager(manager)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url='http://testserver',
        ) as client:
            response = await client.delete('/subscriptions/book/BTC-PERPETUAL')

    assert response.status_code == 404
    assert response.json() == {'detail': 'Subscription is not active'}


@pytest.mark.asyncio
async def test_websocket_stream_book_sends_encoded_subscription_events():
    manager = FakeApiManager()
    key = SubscriptionKey.book('BTC-PERPETUAL')
    manager._states[key] = 1
    manager.queue_event(
        SubscriptionEvent(
            subscription=key,
            payload={
                'price': Decimal('50000.5'),
            },
        )
    )

    websocket = FakeWebSocket()

    await stream_book(
        websocket=cast(WebSocket, websocket),
        instrument_name='btc-perpetual',
        manager=cast(SubscriptionManager, manager),
    )

    assert websocket.accepted is True
    assert websocket.closed is None
    assert websocket.sent == [
        {
            'subscription': {
                'exchange': 'deribit',
                'type': 'book',
                'instrument_name': 'BTC-PERPETUAL',
            },
            'payload': {
                'price': 50000.5,
            },
        }
    ]


@pytest.mark.asyncio
async def test_websocket_stream_book_rejects_inactive_subscription():
    manager = FakeApiManager()
    websocket = FakeWebSocket()

    await stream_book(
        websocket=cast(WebSocket, websocket),
        instrument_name='btc-perpetual',
        manager=cast(SubscriptionManager, manager),
    )

    assert websocket.accepted is False
    assert websocket.closed == (1008, 'Subscription is not active')
    assert websocket.sent == []
