import pytest

from common.settings import Settings


class TestSettings:

    @pytest.fixture(scope="function")
    def settings(self) -> Settings:
        return Settings()
    
    def test_redis_port(self, settings: Settings):
        assert settings.redis_port == 6379