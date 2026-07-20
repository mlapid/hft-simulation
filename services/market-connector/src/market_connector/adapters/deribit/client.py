import time
import json
from typing import AsyncIterator, ClassVar, Any

import asyncio
from loguru import logger
import websockets.asyncio.client as websockets_client

from market_connector.adapters.deribit.errors import (
    DeribitConnectionError,
    DeribitRpcError,
)


class DeribitClient:

    URI: ClassVar[str] = 'wss://www.deribit.com/ws/api/v2'
    URI_TEST: ClassVar[str] = 'wss://test.deribit.com/ws/api/v2'
    
    def __init__(self):

        self._websocket: websockets_client.ClientConnection | None = None
        self._is_test: bool = False

        self._recv_task: asyncio.Task | None = None

        self._pending_requests: dict[int, asyncio.Future[dict]] = {}
        self._messages: asyncio.Queue[dict | Exception] = asyncio.Queue()
        self._request_id: int = 0
        self._messages_active: bool = False

        self._request_timeout: int = 10 # seconds
        self._last_heartbeat: int | None = None

        self._offset_probes: dict[int, int] = {}   # request_id -> client_send_us
        self._clock_offset_us: int | None = None
        self._rtt_us: int | None = None

    @property
    def is_connected(self) -> bool:
        return self._websocket is not None

    @property
    def clock_offset_us(self) -> int | None:
        '''
        Estimated clock skew: server_time - client_time, in microseconds (µs).

        Positive means Deribit's clock is ahead of the local clock.
        '''
        return self._clock_offset_us

    @property
    def rtt_us(self) -> int | None:
        '''
        Round-trip time (network delay), in microseconds (µs).
        '''
        return self._rtt_us

    def _now_us(self) -> int:
        return int(time.time_ns() // 1_000)

    async def connect(self, is_test: bool = False) -> None:
        '''
        Connect to Deribit and start the background receive loop.
        '''

        self._is_test = is_test

        if self.is_connected:
            return

        self._messages = asyncio.Queue()
        self._messages_active = False

        uri: str = self.URI_TEST if self._is_test else self.URI

        try:
            self._websocket = await websockets_client.connect(
                uri=uri,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=10
            )
        except (OSError, TimeoutError) as e:
            raise DeribitConnectionError(
                f'Failed to connect to Deribit WebSocket: {e}'
            ) from e

        self._recv_task = asyncio.create_task(self._recv_loop())
        logger.info(f'Connected to Deribit WebSocket: {uri}')

    async def disconnect(self, error: Exception | None = None) -> None:
        '''
        Disconnect from Deribit and stop the background receive loop.
        '''

        websocket: websockets_client.ClientConnection | None = self._websocket
        recv_task: asyncio.Task | None = self._recv_task

        if websocket is None and recv_task is None:
            return

        self._websocket = None
        self._recv_task = None

        if recv_task is not None:
            recv_task.cancel()
            try:
                await recv_task
            except asyncio.CancelledError:
                pass

        disconnect_error = error or DeribitConnectionError(
            'Disconnected from Deribit WebSocket'
        )

        try:  
            if websocket is not None:
                await websocket.close()
                logger.info('Disconnected from Deribit WebSocket')

        finally:
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(disconnect_error)

            self._pending_requests.clear()
            self._offset_probes.clear()
            await self._messages.put(disconnect_error)

    async def request(self, method: str, params: dict | None = None) -> Any:
        '''
        Send a JSON-RPC command and return its result.
        '''

        websocket: websockets_client.ClientConnection | None = self._websocket
        if websocket is None:
            raise DeribitConnectionError('Not connected to Deribit WebSocket')

        request_id: int = self._next_request_id()
        future: asyncio.Future[dict] = asyncio.get_running_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            await websocket.send(json.dumps({
                'jsonrpc': '2.0',
                'id': request_id,
                'method': method,
                'params': params or {},
            }))

            response: dict = await asyncio.wait_for(
                future,
                timeout=self._request_timeout
            )
        
        except Exception:
            self._pending_requests.pop(request_id, None)
            raise

        error: dict | None = response.get('error')
        if error is not None:
            rpc_error = DeribitRpcError.from_error(error)
            logger.warning(f'Deribit RPC error for {method}: {rpc_error}')
            raise rpc_error

        return response.get('result')

    async def subscribe(self, channels: list[str]) -> Any:
        '''
        Subscribe to Deribit channels.
        '''

        return await self.request(
            method='public/subscribe',
            params={
                'channels': channels,
            }
        )

    async def unsubscribe(self, channels: list[str]) -> Any:
        '''
        Unsubscribe from Deribit channels.
        '''

        return await self.request(
            method='public/unsubscribe',
            params={
                'channels': channels
            }
        )

    async def set_heartbeat(self, interval: int) -> Any:
        '''
        Set the heartbeat interval in seconds.
        '''

        return await self.request(
            method='public/set_heartbeat',
            params={
                'interval': interval
            }
        )
    
    async def messages(self) -> AsyncIterator[dict]:
        '''
        Single-consumer async iterator for receiving pushed messages.
        '''

        if self._messages_active:
            raise RuntimeError('messages() only supports one active consumer')

        self._messages_active = True
        
        try:
            while True:
                item = await self._messages.get()

                if isinstance(item, Exception):
                    raise item

                yield item

        finally:
            self._messages_active = False

    async def _recv_loop(self) -> None:
        '''
        Receive messages from Deribit and route them to requests or subscribers.
        '''

        websocket: websockets_client.ClientConnection | None = self._websocket
        if websocket is None:
            raise DeribitConnectionError('Not connected to Deribit WebSocket')
        
        try:
            async for payload in websocket:
                received_at: int = self._now_us()
                message: dict = json.loads(payload)

                request_id: Any = message.get('id')
                if isinstance(request_id, int):
                    self._handle_response(
                        message=message,
                        request_id=request_id,
                        received_at=received_at
                    )
                    continue

                if isinstance(request_id, str) and request_id.isdigit():
                    self._handle_response(
                        message=message,
                        request_id=int(request_id),
                        received_at=received_at
                    )
                    continue
                
                if request_id is not None:
                    logger.warning(f'Ignoring Deribit response with invalid request id: {request_id!r}')
                    continue

                method: str | None = message.get('method')

                if method == 'subscription':
                    await self._messages.put(message)
                    continue

                if method == 'heartbeat':
                    await self._handle_heartbeat(
                        message=message,
                        received_at=received_at
                    )
                    continue

                logger.debug(f'Received Deribit message with unknown method: {method}')
                await self._messages.put(message)

        except asyncio.CancelledError:
            raise

        except Exception as e:
            logger.exception('Error receiving Deribit message')
            await self.disconnect(
                error=DeribitConnectionError(f'Error receiving Deribit message: {e}')
            )

    def _handle_response(self, message: dict, request_id: int, received_at: int) -> None:
        '''
        Route a JSON-RPC response to the request waiting for this id.
        '''

        client_send_us: int | None = self._offset_probes.pop(request_id, None)
        if client_send_us is not None:
            self._update_clock_offset(
                client_send_us=client_send_us,
                client_recv_us=received_at,
                message=message,
            )
            return

        future: asyncio.Future[dict] | None = self._pending_requests.pop(request_id, None)
        if future is None:
            logger.debug(f'Ignoring Deribit response for unknown request id: {request_id}')
            return

        if future.done():
            logger.debug(f'Ignoring Deribit response for completed request id: {request_id}')
            return

        future.set_result(message)

    async def _handle_heartbeat(self, message: dict, received_at: int) -> None:
        '''
        Handle a heartbeat from the server.
        '''

        self._last_heartbeat = received_at

        if message.get('params', {}).get('type') != 'test_request':
            return

        logger.debug('Received Deribit heartbeat test_request')

        request_id: int = self._next_request_id()
        client_send_us: int = self._now_us()
        self._offset_probes[request_id] = client_send_us
            
        await self._send_json(
            message={
                'jsonrpc': '2.0',
                'id': request_id,
                'method': 'public/test',
                'params': {}
            }
        )

    async def _send_json(self, message: dict) -> None:
        '''
        Send a JSON message to Deribit.
        '''

        websocket = self._websocket
        if websocket is None:
            raise DeribitConnectionError('Cannot send message: not connected to Deribit WebSocket')

        await websocket.send(json.dumps(message))
        logger.debug(f'Sent Deribit message: {message}')

    def _next_request_id(self) -> int:
        '''
        Generate a new request ID.
        '''
        
        self._request_id += 1
        return self._request_id

    def _update_clock_offset(
        self,
        client_send_us: int,
        client_recv_us: int,
        message: dict,
    ) -> None:
        us_in: int | None = message.get('usIn')
        us_out: int | None = message.get('usOut')

        if not isinstance(us_in, int) or not isinstance(us_out, int):
            logger.debug('Deribit response missing usIn/usOut; skipping clock offset update')
            return

        # Clock skew
        offset_us: int = ((us_in - client_send_us) + (us_out - client_recv_us)) // 2
        
        # Round-trip time (network delay)
        rtt_us: int = (client_recv_us - client_send_us) - (us_out - us_in)

        self._clock_offset_us = offset_us
        self._rtt_us = rtt_us
        
        logger.debug(
            f'Deribit clock offset={offset_us} µs, rtt={rtt_us} µs'
        )
