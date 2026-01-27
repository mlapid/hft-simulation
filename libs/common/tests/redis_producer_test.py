from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from common.redis_producer import RedisProducer


class TestRedisProducer:

    @pytest_asyncio.fixture(scope='function')
    async def redis_producer(self) -> AsyncGenerator:
        async with await RedisProducer.connect('test') as producer:
            yield producer

    @pytest.mark.asyncio
    async def test_stream_length(self, redis_producer: RedisProducer):
        await redis_producer.send_message('Hello, World!')
        assert redis_producer.stream_length == 1