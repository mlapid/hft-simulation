from typing import Self, Any
from abc import ABC, abstractmethod

import redis.asyncio as redis
from loguru import logger

from common.settings import Settings


class RedisClient(ABC):
    '''
    Abstract class for Redis producers and consumers
    '''

    def __init__(self, stream_name: str):
        self.stream_name: str = stream_name

        self._redis_client: redis.Redis | None = None
        self.stream_length: int = 0

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(' \
            f'stream_name={self.stream_name}, ' \
            f'is_connected={self.is_connected}, ' \
            f'stream_length={self.stream_length})'

    def __repr__(self) -> str:
        return self.__str__()

    async def __aenter__(self) -> Self:
        '''
        Usage::
        ```python
        async with await RedisProducer.connect('stream_name') as producer:
            await producer.send_message('message')
        ```
        '''

        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        '''
        Check if the Redis client is connected.
        '''

        return self._redis_client is not None

    @classmethod
    async def connect(cls, stream_name: str) -> Self:
        '''
        Connect to Redis

        Use configuration from settings.
        '''

        settings: Settings = cls._get_settings()

        instance: Self = cls(stream_name)

        try:
            instance._redis_client = await redis.from_url(
                f'redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}'
            )
        except Exception as e:
            raise ConnectionError(f'Failed to connect to Redis: {e}')
        else:
            instance.stream_length = await instance._get_stream_length()
            logger.info(f'{instance} is connected to {stream_name}.')
            return instance

    @staticmethod
    def _get_settings() -> Settings:
        '''
        Get the settings for the Redis client.
        '''

        return Settings()
    
    @abstractmethod
    async def disconnect(self) -> None:
        '''
        Subclass responsibility to implement this method.
        '''

        pass

    async def _close_connection(self) -> None:
        '''
        Close the connection to the Redis client.
        '''

        if not self._redis_client:
            raise ConnectionError(f'{self} is not connected.')

        await self._redis_client.aclose()
        self._redis_client = None
        logger.info(f'{self} is disconnected from {self.stream_name}.')

    async def _get_stream_length(self) -> int:
        if not self._redis_client:
            raise ConnectionError(f'{self} is not connected.')

        return await self._redis_client.xlen(name=self.stream_name)