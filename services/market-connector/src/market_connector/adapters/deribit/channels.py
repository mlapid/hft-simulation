from typing import ClassVar, Literal

from market_connector.adapters.deribit.errors import DeribitChannelError


DeribitBookInterval = Literal['100ms']
DeribitBookGroup = Literal['none']
DeribitBookDepth = Literal[10]


class DeribitChannels:
    '''
    Build Deribit subscription channel names.
    '''

    BOOK_GROUP: ClassVar[DeribitBookGroup] = 'none'
    BOOK_DEPTH: ClassVar[DeribitBookDepth] = 10
    BOOK_INTERVAL: ClassVar[DeribitBookInterval] = '100ms'

    @classmethod
    def book(cls, instrument_name: str) -> str:
        '''
        Build the supported Deribit order book channel.
        '''

        instrument_name = cls._instrument_name(instrument_name)

        return (
            f'book.{instrument_name}.{cls.BOOK_GROUP}.'
            f'{cls.BOOK_DEPTH}.{cls.BOOK_INTERVAL}'
        )

    @classmethod
    def _instrument_name(cls, value: str) -> str:
        value = cls._required(value, name='instrument_name')
        return value.upper()

    @staticmethod
    def _required(value: str, *, name: str) -> str:
        value = value.strip()
        if not value:
            raise DeribitChannelError(f'{name} is required')

        if '.' in value:
            raise DeribitChannelError(f'{name} cannot contain "."')

        return value
