import pytest

from pathlib import Path

from common.settings import Settings


class TestSettings:

    @pytest.fixture(scope="function")
    def settings(self) -> Settings:
        return Settings()

    
    def test_grafana_host(self, settings: Settings):
        assert settings.grafana_host == 'localhost'

    def test_grafana_port(self, settings: Settings):
        assert settings.grafana_port == 3000

    def test_grafana_user(self, settings: Settings):
        assert settings.grafana_user == 'root'

    def test_grafana_password(self, settings: Settings):
        assert settings.grafana_password == 'root'

    def test_grafana_token(self, settings: Settings):
        token = Path('/run/shared/grafana_token').read_text().strip()
        assert settings.grafana_token == token

    def test_redis_host(self, settings: Settings):
        assert settings.redis_host == 'localhost'

    def test_redis_port(self, settings: Settings):
        assert settings.redis_port == 6379

    def test_redis_db(self, settings: Settings):
        assert settings.redis_db == 0