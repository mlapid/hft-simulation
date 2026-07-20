from fastapi import APIRouter, Depends, HTTPException, status

from market_connector.api.dependencies import get_manager
from market_connector.api.schemas import SubscriptionCreate, SubscriptionResponse
from market_connector.domain.subscriptions import SubscriptionKey
from market_connector.subscriptions.manager import (
    SubscriptionManager,
    SubscriptionNotFoundError,
)


router = APIRouter(
    prefix='/subscriptions',
    tags=['subscriptions'],
)


@router.get('', response_model=list[SubscriptionResponse])
async def list_subscriptions(
    manager: SubscriptionManager = Depends(get_manager),
) -> list[SubscriptionResponse]:
    '''
    List active subscriptions.
    '''

    return [
        SubscriptionResponse.from_state(state)
        for state in manager.active_subscriptions
    ]


@router.post(
    '',
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    request: SubscriptionCreate,
    manager: SubscriptionManager = Depends(get_manager),
) -> SubscriptionResponse:
    '''
    Create or reference an order-book subscription.
    '''

    key = await manager.subscribe_book(request.instrument_name)
    state = manager.get_state(key)

    if state is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Subscription was not registered',
        )

    return SubscriptionResponse.from_state(state)


@router.delete(
    '/book/{instrument_name}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_book_subscription(
    instrument_name: str,
    manager: SubscriptionManager = Depends(get_manager),
) -> None:
    '''
    Release one reference to an order-book subscription.
    '''

    try:
        await manager.unsubscribe(
            SubscriptionKey.book(instrument_name=instrument_name)
        )
    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Subscription is not active',
        ) from exc
