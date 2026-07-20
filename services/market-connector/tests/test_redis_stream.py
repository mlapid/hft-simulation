import json
from decimal import Decimal

import pytest
from redis.exceptions import RedisError

from market_connector.adapters.deribit.mapper import DeribitBookLevel, DeribitBookUpdate
from market_connector.domain.events import SubscriptionEvent
from market_connector.domain.subscriptions import SubscriptionKey
from market_connector.sinks.redis_stream import RedisStreamError, RedisStreamPublisher


class FakeRedisClient:
    def __init__(self) -> None:
        self.xadd_calls: list[tuple[str, dict[str, str], str, int | None, bool]] = []
        self.is_closed = False

    async def xadd(
        self,
        name: str,
        fields: dict[str, str],
        id: str = '*',
        maxlen: int | None = None,
        approximate: bool = False,
    ) -> str:
        self.xadd_calls.append((name, fields, id, maxlen, approximate))
        return '1-0'

    async def aclose(self) -> None:
        self.is_closed = True


class FailingRedisClient:
    async def xadd(
        self,
        name: str,
        fields: dict[str, str],
        id: str = '*',
        maxlen: int | None = None,
        approximate: bool = False,
    ) -> str:
        raise RedisError('redis unavailable')

    async def aclose(self) -> None:
        pass


def book_update() -> DeribitBookUpdate:
    return DeribitBookUpdate(
        instrument_name='BTC-PERPETUAL',
        timestamp=1535098298227,
        change_id=123456,
        bids=(
            DeribitBookLevel(
                side='bid',
                price=Decimal('50000.0'),
                volume=Decimal('10.5'),
            ),
        ),
        asks=(
            DeribitBookLevel(
                side='ask',
                price=Decimal('50001.0'),
                volume=Decimal('8.3'),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_redis_stream_publisher_builds_stream_name_and_fields():
    publisher = RedisStreamPublisher(
        host='127.0.0.1',
        port=6379,
        service_name='market-connector',
    )
    key = SubscriptionKey.book('btc-perpetual')
    event = SubscriptionEvent(
        subscription=key,
        payload=book_update(),
    )

    assert publisher.stream_name(key) == 'market-connector:deribit:BTC-PERPETUAL:book'

    fields = publisher.fields(event)
    payload = json.loads(fields['payload'])

    assert fields['service'] == 'market-connector'
    assert fields['exchange'] == 'deribit'
    assert fields['type'] == 'book'
    assert fields['instrument_name'] == 'BTC-PERPETUAL'
    assert payload['instrument_name'] == 'BTC-PERPETUAL'
    assert payload['bids'][0]['price'] == '50000.0'
    assert payload['asks'][0]['volume'] == '8.3'


@pytest.mark.asyncio
async def test_redis_stream_publisher_sends_xadd():
    client = FakeRedisClient()
    publisher = RedisStreamPublisher(
        host='127.0.0.1',
        port=6379,
        service_name='market-connector',
        client=client,
    )
    event = SubscriptionEvent(
        subscription=SubscriptionKey.book('BTC-PERPETUAL'),
        payload=book_update(),
    )

    await publisher.publish(event)
    await publisher.close()

    assert len(client.xadd_calls) == 1
    stream_name, fields, stream_id, maxlen, approximate = client.xadd_calls[0]

    assert stream_name == 'market-connector:deribit:BTC-PERPETUAL:book'
    assert fields['exchange'] == 'deribit'
    assert fields['instrument_name'] == 'BTC-PERPETUAL'
    assert stream_id == '*'
    assert maxlen == 100_000
    assert approximate is False
    assert client.is_closed is True


@pytest.mark.asyncio
async def test_redis_stream_publisher_wraps_publish_errors():
    publisher = RedisStreamPublisher(
        host='127.0.0.1',
        port=6379,
        service_name='market-connector',
        client=FailingRedisClient(),
    )
    event = SubscriptionEvent(
        subscription=SubscriptionKey.book('BTC-PERPETUAL'),
        payload=book_update(),
    )

    with pytest.raises(
        RedisStreamError,
        match='Failed to publish event to Redis stream '
        'market-connector:deribit:BTC-PERPETUAL:book',
    ):
        await publisher.publish(event)
