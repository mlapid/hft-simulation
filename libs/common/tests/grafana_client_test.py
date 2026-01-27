from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from common.grafana_client import GrafanaClient


class TestGrafanaClient:

    @pytest_asyncio.fixture(scope='function')
    async def grafana_client(self) -> AsyncGenerator:
        async with await GrafanaClient.connect('test') as client:
            yield client

    @pytest.mark.asyncio
    async def test_send_event(self, grafana_client: GrafanaClient):
        await grafana_client.send_event(
            channel_name='test',
            data={'value': 1},
            timestamp=1714857600000000000
        )
        assert True