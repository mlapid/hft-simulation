from dataclasses import dataclass
from typing import Literal


ExchangeName = Literal['deribit']
SubscriptionType = Literal['book']


class SubscriptionError(ValueError):
    '''
    Raised when a subscription request is invalid.
    '''


@dataclass(frozen=True, slots=True)
class SubscriptionKey:
    '''
    Exchange-neutral identity for one upstream subscription.
    '''

    exchange: ExchangeName
    type: SubscriptionType
    instrument_name: str

    @classmethod
    def book(
        cls,
        instrument_name: str,
        *,
        exchange: ExchangeName = 'deribit',
    ) -> 'SubscriptionKey':
        return cls(
            exchange=exchange,
            type='book',
            instrument_name=normalize_instrument_name(instrument_name),
        )


@dataclass(frozen=True, slots=True)
class SubscriptionState:
    '''
    Public state for an active subscription.
    '''

    key: SubscriptionKey
    ref_count: int


def normalize_instrument_name(value: str) -> str:
    instrument_name = value.strip().upper()
    if not instrument_name:
        raise SubscriptionError('instrument_name is required')

    return instrument_name
