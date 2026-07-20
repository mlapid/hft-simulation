import asyncio
import json
from typing import Any, AsyncIterator, cast

import pytest

from market_connector.adapters.deribit.client import DeribitClient, DeribitRpcError


class FakeWebSocket:
    def __init__(self):
        self.sent: list[dict] = []
        self.closed: bool = False
        self._incoming: asyncio.Queue[str | None] = asyncio.Queue()

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def close(self) -> None:
        self.closed = True

    def queue_message(self, message: dict) -> None:
        self._incoming.put_nowait(json.dumps(message))

    def close_stream(self) -> None:
        self._incoming.put_nowait(None)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        payload = await self._incoming.get()
        if payload is None:
            raise StopAsyncIteration

        return payload


def attach_websocket(client: DeribitClient, websocket: FakeWebSocket) -> None:
    client._websocket = cast(Any, websocket)


async def wait_for_sent(websocket: FakeWebSocket, count: int = 1) -> None:
    for _ in range(20):
        if len(websocket.sent) >= count:
            return

        await asyncio.sleep(0)

    raise AssertionError(f'Expected {count} sent message(s), got {len(websocket.sent)}')


async def stop_recv_loop(websocket: FakeWebSocket, recv_task: asyncio.Task) -> None:
    if not recv_task.done():
        websocket.close_stream()

    await asyncio.wait_for(recv_task, timeout=1)


async def next_message(messages: AsyncIterator[dict]) -> dict:
    return await anext(messages)


@pytest.mark.asyncio
async def test_request_sends_json_rpc_and_returns_result():
    client = DeribitClient()
    websocket = FakeWebSocket()
    attach_websocket(client, websocket)
    recv_task = asyncio.create_task(client._recv_loop())

    try:
        request_task = asyncio.create_task(
            client.request(
                method='public/subscribe',
                params={'channels': ['trades.BTC-PERPETUAL.raw']},
            )
        )

        await wait_for_sent(websocket)

        assert websocket.sent == [
            {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'public/subscribe',
                'params': {'channels': ['trades.BTC-PERPETUAL.raw']},
            }
        ]

        websocket.queue_message({
            'jsonrpc': '2.0',
            'id': 1,
            'result': {'subscribed': True},
        })

        assert await request_task == {'subscribed': True}
        assert client._pending_requests == {}

    finally:
        await stop_recv_loop(websocket, recv_task)


@pytest.mark.asyncio
async def test_request_raises_deribit_rpc_error():
    client = DeribitClient()
    websocket = FakeWebSocket()
    attach_websocket(client, websocket)
    recv_task = asyncio.create_task(client._recv_loop())

    try:
        request_task = asyncio.create_task(client.request(method='public/test'))

        await wait_for_sent(websocket)

        websocket.queue_message({
            'jsonrpc': '2.0',
            'id': 1,
            'error': {
                'code': 10000,
                'message': 'bad request',
                'data': {'field': 'value'},
            },
        })

        with pytest.raises(DeribitRpcError) as exc_info:
            await request_task

        assert exc_info.value.code == 10000
        assert exc_info.value.message == 'bad request'
        assert exc_info.value.data == {'field': 'value'}
        assert client._pending_requests == {}

    finally:
        await stop_recv_loop(websocket, recv_task)


@pytest.mark.asyncio
async def test_recv_loop_routes_subscription_messages():
    client = DeribitClient()
    websocket = FakeWebSocket()
    attach_websocket(client, websocket)
    recv_task = asyncio.create_task(client._recv_loop())

    try:
        message = {
            'jsonrpc': '2.0',
            'method': 'subscription',
            'params': {
                'channel': 'trades.BTC-PERPETUAL.raw',
                'data': [{'price': 100}],
            },
        }

        websocket.queue_message(message)

        messages = client.messages()
        try:
            assert await asyncio.wait_for(anext(messages), timeout=1) == message
        finally:
            await cast(Any, messages).aclose()

    finally:
        await stop_recv_loop(websocket, recv_task)


@pytest.mark.asyncio
async def test_heartbeat_test_request_sends_public_test_without_pending_request():
    client = DeribitClient()
    websocket = FakeWebSocket()
    attach_websocket(client, websocket)
    recv_task = asyncio.create_task(client._recv_loop())

    try:
        websocket.queue_message({
            'jsonrpc': '2.0',
            'method': 'heartbeat',
            'params': {'type': 'test_request'},
        })

        await wait_for_sent(websocket)

        assert websocket.sent == [
            {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'public/test',
                'params': {},
            }
        ]
        assert client._last_heartbeat is not None
        assert client._pending_requests == {}

        websocket.queue_message({
            'jsonrpc': '2.0',
            'id': 1,
            'result': 'ok',
        })

    finally:
        await stop_recv_loop(websocket, recv_task)


@pytest.mark.asyncio
async def test_messages_allows_only_one_active_consumer():
    client = DeribitClient()

    first_consumer = client.messages()
    first_task = asyncio.create_task(next_message(first_consumer))
    await asyncio.sleep(0)

    second_consumer = client.messages()
    with pytest.raises(RuntimeError, match='one active consumer'):
        await anext(second_consumer)

    first_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first_task

    await cast(Any, first_consumer).aclose()
