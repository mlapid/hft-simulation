import json
import time
from typing import Self, Any, ClassVar, AsyncGenerator

from loguru import logger

from websockets.exceptions import InvalidHandshake, ConnectionClosed
import websockets.asyncio.client as websockets_client


class DeribitConnector:
    '''
    Deribit connector for getting market data from the exchange.
    '''

    URI: ClassVar[str] = "wss://www.deribit.com/ws/api/v2"
    URI_TEST: ClassVar[str] = "wss://test.deribit.com/ws/api/v2"

    def __init__(self):
        self._websocket_client: websockets_client.ClientConnection | None = None

        self._client_send: float = 0.0
        self._server_recv: float = 0.0
        self._server_send: float = 0.0
        self._client_recv: float = 0.0
        self.offset: float = 0.0

    def __str__(self):

        if self._websocket_client:
            return f'{self.__class__.__name__}(' \
                f'remote={self._websocket_client.remote_address}, ' \
                f'id={self._websocket_client.id})'

        return f'{self.__class__.__name__}(disconnected)'

    def __repr__(self):
        return self.__str__()

    async def __aenter__(self) -> Self:
        '''
        Usage::
        ```python
        async with await DeribitConnector.connect() as connector:
            await connector.subscribe()
        ```
        '''

        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.disconnect()

    @classmethod
    async def connect(cls, is_test: bool = False) -> Self:

        uri: str = cls.URI_TEST if is_test else cls.URI

        instance: Self = cls()

        try:
            instance._websocket_client = await websockets_client.connect(
                uri=uri
            )
        except (OSError, TimeoutError, InvalidHandshake) as e:
            raise ConnectionError(f'Failed to connect to Deribit WebSocket: {e}') from e
        
        logger.info(f'{instance} is connected to {uri}.')
        return instance

    async def disconnect(self) -> None:
        '''
        Close the connection.
        '''

        if not self._websocket_client:
            return

        await self._websocket_client.close()
        self._websocket_client = None
        logger.info(f'{self} is disconnected.')

    async def subscribe(self, channels: list[str]) -> None:
        '''
        Subscribe to a list of channels.

        Example:
        ```python
        await connector.subscribe(channels=['book.ETH-PERPETUAL.none.10.100ms'])
        ```
        '''

        message: dict = {
            "jsonrpc" : "2.0",
            "id" : 3600,
            "method" : "public/subscribe",
            "params" : {
                    "channels" : channels
                }
        }

        try:
            await self._websocket_client.send(json.dumps(message))
            response: dict = json.loads(await self._websocket_client.recv())
        except ConnectionClosed as e:
            raise ConnectionError(f'{self} connection closed while sending: {e}') from e

        if 'error' in response:
            raise RuntimeError(f'Subscription failed: {response["error"]}')
        
        logger.info(f'{self} subscribed to channel(s): {", ".join(channels)}. Response: {response}')
    
    async def set_heartbeat(self, interval: int = 10) -> None:
        '''
        Set the heartbeat interval.
        '''

        message: dict = {
            "jsonrpc" : "2.0",
            "id" : 9098,
            "method" : "public/set_heartbeat",
            "params" : {
                "interval" : interval
            }
        }

        try:
            await self._websocket_client.send(json.dumps(message))
            response: dict = json.loads(await self._websocket_client.recv())
        except ConnectionClosed as e:
            raise ConnectionError(f'{self} connection closed while sending: {e}') from e

        if 'error' in response:
            raise RuntimeError(f'Failed to set heartbeat: {response["error"]}')

        logger.info(f'{self} set heartbeat interval to {interval} seconds.')

    async def receive(self) -> AsyncGenerator[dict, None]:
        '''
        Receive a message from the WebSocket client.
        '''

        async for raw_message in self._websocket_client:
            self._client_recv = time.time()
            message: dict = json.loads(raw_message)

            if message.get('id') == 8192:
                self._server_recv = message.get('usIn', 0) / 1e6
                self._server_send = message.get('usOut', 0) / 1e6
                self.offset = ((self._server_recv - self._client_send) + (self._server_send - self._client_recv)) / 2
                logger.debug(f'Offset recalculated: {self.offset}')
                continue

            if message.get('method') == 'heartbeat':
                if message.get('params', {}).get('type') == 'test_request':
                    self._client_send = time.time()
                    await self._websocket_client.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": 8192,
                        "method": "public/test",
                        "params": {}
                    }))
                continue

            if message.get('method') == 'subscription':
                params: dict = message.get('params', {})
                data: dict = params.get('data', {})
                
                yield {
                    'channel': params.get('channel', ''),
                    'data': data,
                    'timestamp': self._client_recv,
                    'offset': self.offset
                }