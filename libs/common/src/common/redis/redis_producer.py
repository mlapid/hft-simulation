from loguru import logger

from common.redis.redis_client import RedisClient


class RedisProducer(RedisClient):
    '''
    Redis producer for sending data to a stream.
    '''

    async def disconnect(self) -> None:
        '''
        Flush the stream and close the connection.
        '''

        await self.flush_stream()

        await self._close_connection()

    async def send_message(self, message: str) -> None:
        '''
        Send a message to the Redis stream.
        '''

        if not self._redis_client:
            raise ConnectionError(f'{self} is not connected.')

        await self._redis_client.xadd(name=self.stream_name, fields={
            'message': message
        })
        self.stream_length = await self._get_stream_length()
        logger.info(f'{self} sent message: {message}')

    async def flush_stream(self) -> None:
        '''Delete all messages from the stream.'''

        if not self._redis_client:
            raise ConnectionError(f'{self} is not connected.')

        await self._redis_client.delete(self.stream_name)
        self.stream_length = 0
        logger.info(f'{self} flushed stream {self.stream_name}.')