from collections.abc import AsyncIterator
from typing import Any, Protocol


class BookAdapter(Protocol):
    '''
    Protocol for adapters that can stream order-book updates.
    '''

    @property
    def is_connected(self) -> bool:
        '''
        Return whether the adapter is connected.
        '''

    async def connect(self) -> None:
        '''
        Connect to the exchange.
        '''

    async def disconnect(self) -> None:
        '''
        Disconnect from the exchange.
        '''

    async def subscribe_book(self, instrument_name: str) -> str:
        '''
        Subscribe to order-book updates for an instrument.
        '''

    async def unsubscribe_book(self, instrument_name: str) -> str:
        '''
        Unsubscribe from order-book updates for an instrument.
        '''

    def book_events(self) -> AsyncIterator[Any]:
        '''
        Yield mapped order-book updates for all subscribed instruments.
        '''
