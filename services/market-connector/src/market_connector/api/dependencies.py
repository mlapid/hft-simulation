from fastapi import Request, WebSocket

from market_connector.subscriptions.manager import SubscriptionManager


def get_manager(request: Request) -> SubscriptionManager:
    '''
    Return the app's subscription manager for HTTP routes.
    '''

    return request.app.state.manager


def get_websocket_manager(websocket: WebSocket) -> SubscriptionManager:
    '''
    Return the app's subscription manager for WebSocket routes.
    '''

    return websocket.app.state.manager
