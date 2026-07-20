from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from market_connector.adapters.deribit.adapter import DeribitAdapter
from market_connector.api.routes import health, streams, subscriptions
from market_connector.config import Settings
from market_connector.sinks.redis_stream import RedisStreamPublisher
from market_connector.subscriptions.manager import SubscriptionManager


def create_manager(
    settings: Settings | None = None,
) -> SubscriptionManager:
    '''
    Build the default subscription manager.
    '''

    settings = settings or Settings.from_env()
    event_sinks = []

    if settings.redis_enabled:
        event_sinks.append(
            RedisStreamPublisher(
                host=settings.redis_host,
                port=settings.redis_port,
                service_name=settings.service_name,
            )
        )

    return SubscriptionManager(
        adapter=DeribitAdapter(
            is_test=settings.deribit_testnet,
            heartbeat_interval=settings.deribit_heartbeat_interval,
        ),
        event_sinks=event_sinks,
    )


def create_app(
    manager: SubscriptionManager | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    '''
    Build the FastAPI application.
    '''

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings or Settings.from_env()
        app.state.manager = manager or create_manager(app.state.settings)
        try:
            yield
        finally:
            await app.state.manager.disconnect()

    app = FastAPI(
        title='market-connector',
        version='0.1.0',
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(subscriptions.router)
    app.include_router(streams.router)

    return app


app = create_app()
