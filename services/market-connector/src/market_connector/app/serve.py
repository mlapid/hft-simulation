import uvicorn

from market_connector.config import Settings


def main() -> None:
    '''
    Run the market-connector FastAPI application.
    '''

    settings = Settings.from_env()

    uvicorn.run(
        'market_connector.app.main:app',
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
