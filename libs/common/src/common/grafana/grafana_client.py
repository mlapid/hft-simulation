from typing import Self, Any

from loguru import logger
import websockets.asyncio.client as websockets_client
from websockets.exceptions import InvalidHandshake, ConnectionClosed

from common.settings import Settings

settings: Settings = Settings()


class GrafanaClient:
    '''
    Grafana client for sending data to a Grafana instance.
    '''

    def __init__(self, stream_name: str):
        self.stream_name: str = stream_name

        self._websocket: websockets_client.ClientConnection | None = None

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(' \
            f'stream_name={self.stream_name}, ' \
            f'is_connected={self.is_connected})'

    def __repr__(self) -> str:
        return self.__str__()

    async def __aenter__(self) -> Self:
        '''
        Usage::
        ```python
        async with await GrafanaClient.connect('stream_name') as client:
            await client.send_event('channel_name', 'data', 'timestamp')
        ```
        '''

        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        return bool(self._websocket)

    @classmethod
    async def connect(cls, stream_name: str) -> Self:
        '''
        Connect to Grafana WebSocket

        Use configuration from settings.
        '''

        instance: Self = cls(stream_name)

        try:
            instance._websocket = await websockets_client.connect(
                uri = f'ws://{settings.grafana_host}:{settings.grafana_port}/api/live/push/{stream_name}',
                additional_headers = {
                    'Authorization': f'Bearer {settings.grafana_token}'
                }
            )
        except (OSError, TimeoutError, InvalidHandshake) as e:
            raise ConnectionError(f'Failed to connect to Grafana WebSocket: {e}')

        logger.info(f'{instance} is connected to {stream_name}')
        return instance

    async def disconnect(self) -> None:
        if not self._websocket:
            return

        await self._websocket.close()
        self._websocket = None
        logger.info(f'{self} is disconnected from {self.stream_name}.')

    async def send_event(self, channel_name: str, data: dict, timestamp: int) -> None:
        '''
        Send an event to Grafana.

        Args:
            channel_name: The name of the channel to send the event to.
            data: The data to send to Grafana.
            timestamp: The timestamp of the event in nanoseconds.
        '''

        if not self._websocket:
            raise ConnectionError(f'{self} is not connected.')

        if not data:
            raise ValueError('Data is required.')

        if len(str(timestamp)) != 19:
            raise ValueError(f'Timestamp must be in nanoseconds (19 digits), got {len(str(timestamp))} digits.')

        data_str: str = ','.join(f"{key}={value}" for key, value in data.items())

        metric: str = f'{channel_name},stream={self.stream_name} {data_str} {timestamp}'

        try:
            await self._websocket.send(metric.encode('utf-8'))
        except ConnectionClosed as e:
            raise ConnectionError(f'{self} connection closed while sending metric: {e}') from e