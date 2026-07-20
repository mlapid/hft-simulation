import json
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from typing import Any, Protocol, cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from market_connector.domain.events import SubscriptionEvent
from market_connector.domain.subscriptions import SubscriptionKey


class RedisStreamError(Exception):
    '''
    Raised when publishing to Redis Streams fails.
    '''


class RedisStreamClient(Protocol):
    '''
    Minimal async Redis client used by the stream publisher.
    '''

    async def xadd(
        self,
        name: str,
        fields: dict[str, str],
        id: str = '*',
        maxlen: int | None = None,
        approximate: bool = False
    ) -> str | bytes:
        '''
        Append fields to a Redis Stream.
        '''

    async def aclose(self) -> None:
        '''
        Close the Redis client.
        '''


class RedisStreamPublisher:
    '''
    Publish subscription events to Redis Streams using XADD.
    '''

    def __init__(
        self,
        *,
        host: str,
        port: int,
        service_name: str = 'market-connector',
        client: RedisStreamClient | None = None,
    ) -> None:
        self._service_name = service_name
        self._client = client or cast(
            RedisStreamClient,
            Redis(
                host=host,
                port=port,
                decode_responses=True,
            ),
        )

    async def publish(self, event: SubscriptionEvent) -> None:
        '''
        Publish an event to its Redis stream.
        '''

        stream_name = self.stream_name(event.subscription)
        fields = self.fields(event)

        try:
            await self._client.xadd(
                name=stream_name,
                fields=fields,
                maxlen=100_000,
                approximate=False
            )

        except RedisError as exc:
            raise RedisStreamError(
                f'Failed to publish event to Redis stream {stream_name}'
            ) from exc

    async def close(self) -> None:
        '''
        Close the Redis connection if open.
        '''

        await self._client.aclose()

    def stream_name(self, key: SubscriptionKey) -> str:
        '''
        Build the Redis stream name for a subscription.
        '''

        return f'{self._service_name}:{key.exchange}:{key.instrument_name}:{key.type}'

    def fields(self, event: SubscriptionEvent) -> dict[str, str]:
        '''
        Build Redis Stream fields for a subscription event.
        '''

        return {
            'service': self._service_name,
            'exchange': event.subscription.exchange,
            'type': event.subscription.type,
            'instrument_name': event.subscription.instrument_name,
            'payload': json.dumps(
                _jsonable(event.payload),
                separators=(',', ':'),
                sort_keys=True,
            ),
        }

def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)

    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))

    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, tuple | list):
        return [
            _jsonable(item)
            for item in value
        ]

    return value
