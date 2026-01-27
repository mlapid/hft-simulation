import json
from typing import AsyncGenerator

from common.redis.redis_client import RedisClient


class RedisConsumer(RedisClient):
    '''
    Redis consumer for consuming data from a stream.
    '''

    def __init__(self, stream_name: str):
        super().__init__(stream_name)

        self.last_message_id: str = '$'

    async def disconnect(self) -> None:
        '''
        Close the connection.
        '''

        await self._close_connection()

    async def _read_message(self) -> dict | None:
        '''
        Read a message from the stream.
        '''

        if not self._redis_client:
            raise ConnectionError(f'{self} is not connected.')

        message: list = await self._redis_client.xread(
            streams={self.stream_name: self.last_message_id},
            count=1,
            block=0
        )

        self.stream_length = await self._get_stream_length()

        for stream, payload in message:
            for message_id, message_data in payload:
                self.last_message_id = message_id.decode('utf-8')
                message: str = message_data[b'message'].decode('utf-8')
                message_dict: dict = json.loads(message)
                
                return message_dict

        return None

    async def read_stream(self) -> AsyncGenerator[dict, None]:
        '''
        Read the stream.
        '''

        if not self._redis_client:
            raise ConnectionError(f'{self} is not connected.')

        while self._redis_client:
            message: dict | None = await self._read_message()
            if message is not None:
                yield message