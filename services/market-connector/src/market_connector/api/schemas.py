from typing import Literal

from pydantic import BaseModel, Field

from market_connector.domain.subscriptions import SubscriptionKey, SubscriptionState


class SubscriptionCreate(BaseModel):
    '''
    Request body for creating a subscription.
    '''

    exchange: Literal['deribit'] = 'deribit'
    type: Literal['book'] = 'book'
    instrument_name: str = Field(min_length=1)


class SubscriptionKeyResponse(BaseModel):
    '''
    API representation of a subscription key.
    '''

    exchange: Literal['deribit']
    type: Literal['book']
    instrument_name: str

    @classmethod
    def from_key(cls, key: SubscriptionKey) -> 'SubscriptionKeyResponse':
        return cls(
            exchange=key.exchange,
            type=key.type,
            instrument_name=key.instrument_name,
        )


class SubscriptionResponse(BaseModel):
    '''
    API representation of active subscription state.
    '''

    key: SubscriptionKeyResponse
    ref_count: int

    @classmethod
    def from_state(cls, state: SubscriptionState) -> 'SubscriptionResponse':
        return cls(
            key=SubscriptionKeyResponse.from_key(state.key),
            ref_count=state.ref_count,
        )
