from dataclasses import dataclass
from typing import Any

from market_connector.domain.subscriptions import SubscriptionKey


@dataclass(frozen=True, slots=True)
class SubscriptionEvent:
    '''
    Event emitted for one active subscription.
    '''

    subscription: SubscriptionKey
    payload: Any
