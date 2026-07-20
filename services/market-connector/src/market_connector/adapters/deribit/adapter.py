from collections.abc import AsyncIterator, Iterable
from typing import Any

from market_connector.adapters.deribit.channels import DeribitChannels
from market_connector.adapters.deribit.client import DeribitClient
from market_connector.adapters.deribit.errors import (
    DeribitAdapterError,
    DeribitSubscriptionError,
)
from market_connector.adapters.deribit.mapper import DeribitBookUpdate, DeribitMapper


class DeribitAdapter:
    '''
    High-level market-data adapter for Deribit.

    DeribitClient owns the WebSocket and JSON-RPC mechanics. The adapter owns
    intent-level operations: connect, subscribe to supported channels, and yield
    channel data without exposing callers to the JSON-RPC notification envelope.
    '''

    def __init__(
        self,
        client: DeribitClient | None = None,
        *,
        is_test: bool = False,
        heartbeat_interval: int | None = 10,
    ) -> None:
        if heartbeat_interval is not None and heartbeat_interval < 10:
            raise DeribitAdapterError('heartbeat_interval must be >= 10')

        self._client = client or DeribitClient()
        self._is_test = is_test
        self._heartbeat_interval = heartbeat_interval
        self._subscriptions: set[str] = set()

    @property
    def client(self) -> DeribitClient:
        '''
        Return the underlying low-level Deribit client.
        '''

        return self._client

    @property
    def is_connected(self) -> bool:
        '''
        Return whether the underlying client is connected.
        '''

        return self._client.is_connected

    @property
    def subscribed_channels(self) -> frozenset[str]:
        '''
        Return the channels this adapter has successfully subscribed to.
        '''

        return frozenset(self._subscriptions)

    async def __aenter__(self) -> 'DeribitAdapter':
        await self.connect()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        '''
        Connect to Deribit and configure heartbeat if enabled.
        '''

        if self.is_connected:
            return

        await self._client.connect(is_test=self._is_test)

        if self._heartbeat_interval is not None:
            await self._client.set_heartbeat(interval=self._heartbeat_interval)

    async def disconnect(self) -> None:
        '''
        Disconnect from Deribit and clear local subscription state.
        '''

        try:
            await self._client.disconnect()
        finally:
            self._subscriptions.clear()

    async def subscribe(self, channels: Iterable[str]) -> list[str]:
        '''
        Subscribe to one or more Deribit channels.
        '''

        channels = self._unique_channels(channels)
        if not channels:
            return []

        result = await self._client.subscribe(channels)
        subscribed_channels = self._coerce_channel_list(
            result=result,
            action='subscribe',
        )

        self._subscriptions.update(subscribed_channels)
        return subscribed_channels

    async def unsubscribe(self, channels: Iterable[str]) -> list[str]:
        '''
        Unsubscribe from one or more Deribit channels.
        '''

        channels = self._unique_channels(channels)
        if not channels:
            return []

        result = await self._client.unsubscribe(channels)
        unsubscribed_channels = self._coerce_channel_list(
            result=result,
            action='unsubscribe',
        )

        self._subscriptions.difference_update(unsubscribed_channels)
        return unsubscribed_channels

    async def subscribe_book(self, instrument_name: str) -> str:
        '''
        Subscribe to the supported Deribit order-book channel.
        '''

        channel = DeribitChannels.book(instrument_name)
        await self.subscribe([channel])
        return channel

    async def unsubscribe_book(self, instrument_name: str) -> str:
        '''
        Unsubscribe from the supported Deribit order-book channel.
        '''

        channel = DeribitChannels.book(instrument_name)
        await self.unsubscribe([channel])
        return channel

    async def subscription_data(self, channel: str) -> AsyncIterator[Any]:
        '''
        Yield data payloads for a subscribed channel.

        Deribit notifications arrive as JSON-RPC messages with params.channel
        and params.data. This stream filters by channel and yields params.data.
        The underlying client supports one active message consumer at a time.
        '''

        channel = self._required_channel(channel)

        async for message in self._client.messages():
            data = self._extract_subscription_data(
                message=message,
                channel=channel,
            )

            if data is not None:
                yield data

    async def book_events(self) -> AsyncIterator[DeribitBookUpdate]:
        '''
        Yield mapped order-book updates for all subscribed book channels.

        This method consumes the underlying client's single message stream once
        and is intended for service-level fanout.
        '''

        async for message in self._client.messages():
            notification = self._extract_subscription_notification(message=message)
            if notification is None:
                continue

            channel, data = notification
            if channel not in self._subscriptions:
                continue

            if not channel.startswith('book.'):
                continue

            if not isinstance(data, dict):
                raise DeribitSubscriptionError(
                    f'Deribit book notification for {channel} must contain an object'
                )

            yield DeribitMapper.book_snapshot(data)

    async def book_updates(
        self,
        instrument_name: str,
        *,
        subscribe: bool = True,
    ) -> AsyncIterator[DeribitBookUpdate]:
        '''
        Yield mapped order-book snapshots for an instrument.

        Supported Deribit book channels are grouped depth snapshots like
        book.BTC-PERPETUAL.none.10.100ms. Raw payloads remain available through
        subscription_data().
        '''

        channel = DeribitChannels.book(instrument_name)

        if subscribe and channel not in self._subscriptions:
            await self.subscribe([channel])

        async for data in self.subscription_data(channel):
            if not isinstance(data, dict):
                raise DeribitSubscriptionError(
                    f'Deribit book notification for {channel} must contain an object'
                )

            yield DeribitMapper.book_snapshot(data)

    @staticmethod
    def _unique_channels(channels: Iterable[str]) -> list[str]:
        unique_channels: list[str] = []
        seen: set[str] = set()

        for channel in channels:
            channel = DeribitAdapter._required_channel(channel)
            if channel in seen:
                continue

            seen.add(channel)
            unique_channels.append(channel)

        return unique_channels

    @staticmethod
    def _required_channel(channel: str) -> str:
        channel = channel.strip()
        if not channel:
            raise DeribitSubscriptionError('channel is required')

        return channel

    @staticmethod
    def _coerce_channel_list(result: Any, *, action: str) -> list[str]:
        if not isinstance(result, list):
            raise DeribitSubscriptionError(
                f'Deribit {action} response must be a list of channels'
            )

        for channel in result:
            if not isinstance(channel, str) or not channel:
                raise DeribitSubscriptionError(
                    f'Deribit {action} response must be a list of channels'
                )

        return result

    @staticmethod
    def _extract_subscription_data(
        *,
        message: dict[str, Any],
        channel: str,
    ) -> Any | None:
        notification = DeribitAdapter._extract_subscription_notification(
            message=message,
        )

        if notification is None:
            return None

        message_channel, data = notification

        if message_channel != channel:
            return None

        return data

    @staticmethod
    def _extract_subscription_notification(
        *,
        message: dict[str, Any],
    ) -> tuple[str, Any] | None:
        if message.get('method') != 'subscription':
            return None

        params = message.get('params')
        if not isinstance(params, dict):
            raise DeribitSubscriptionError(
                'Deribit subscription notification is missing params'
            )

        channel = params.get('channel')
        if not isinstance(channel, str) or not channel:
            raise DeribitSubscriptionError(
                'Deribit subscription notification is missing channel'
            )

        if 'data' not in params:
            raise DeribitSubscriptionError(
                f'Deribit subscription notification for {channel} is missing data'
            )

        return channel, params['data']
