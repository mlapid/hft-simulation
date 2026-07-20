from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder

from market_connector.api.dependencies import get_websocket_manager
from market_connector.domain.subscriptions import SubscriptionKey
from market_connector.subscriptions.manager import (
    SubscriptionManager,
    SubscriptionNotFoundError,
)


router = APIRouter(tags=['streams'])


@router.websocket('/streams/book/{instrument_name}')
async def stream_book(
    websocket: WebSocket,
    instrument_name: str,
    manager: SubscriptionManager = Depends(get_websocket_manager),
) -> None:
    '''
    Stream normalized order-book events for an active subscription.
    '''

    key = SubscriptionKey.book(instrument_name=instrument_name)

    if manager.get_state(key) is None:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason='Subscription is not active',
        )
        return

    await websocket.accept()

    try:
        async for event in manager.stream(key):
            await websocket.send_json(jsonable_encoder(event))

    except WebSocketDisconnect:
        return

    except SubscriptionNotFoundError:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason='Subscription is not active',
        )
