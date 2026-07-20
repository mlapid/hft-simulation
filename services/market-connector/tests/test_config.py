import pytest

from market_connector.config import ConfigError, Settings


def test_settings_defaults_to_safe_local_testnet_values():
    settings = Settings.from_env({})

    assert settings.api_host == '127.0.0.1'
    assert settings.api_port == 8000
    assert settings.api_reload is False
    assert settings.deribit_testnet is True
    assert settings.deribit_heartbeat_interval == 10
    assert settings.redis_enabled is True
    assert settings.redis_host == '100.117.164.15'
    assert settings.redis_port == 6379
    assert settings.service_name == 'market-connector'


def test_settings_reads_environment_values():
    settings = Settings.from_env({
        'MARKET_CONNECTOR_API_HOST': '0.0.0.0',
        'MARKET_CONNECTOR_API_PORT': '9000',
        'MARKET_CONNECTOR_API_RELOAD': 'yes',
        'MARKET_CONNECTOR_DERIBIT_TESTNET': 'false',
        'MARKET_CONNECTOR_DERIBIT_HEARTBEAT_INTERVAL': '30',
        'MARKET_CONNECTOR_REDIS_ENABLED': 'false',
        'MARKET_CONNECTOR_REDIS_HOST': 'localhost',
        'MARKET_CONNECTOR_REDIS_PORT': '6380',
        'MARKET_CONNECTOR_SERVICE_NAME': 'custom-service',
    })

    assert settings.api_host == '0.0.0.0'
    assert settings.api_port == 9000
    assert settings.api_reload is True
    assert settings.deribit_testnet is False
    assert settings.deribit_heartbeat_interval == 30
    assert settings.redis_enabled is False
    assert settings.redis_host == 'localhost'
    assert settings.redis_port == 6380
    assert settings.service_name == 'custom-service'


def test_settings_allows_disabling_deribit_heartbeat():
    settings = Settings.from_env({
        'MARKET_CONNECTOR_DERIBIT_HEARTBEAT_INTERVAL': 'none',
    })

    assert settings.deribit_heartbeat_interval is None


@pytest.mark.parametrize(
    ('env', 'message'),
    [
        ({
            'MARKET_CONNECTOR_API_RELOAD': 'sometimes',
        }, 'MARKET_CONNECTOR_API_RELOAD must be a boolean'),
        ({
            'MARKET_CONNECTOR_API_PORT': '0',
        }, 'MARKET_CONNECTOR_API_PORT must be >= 1'),
        ({
            'MARKET_CONNECTOR_API_PORT': '70000',
        }, 'MARKET_CONNECTOR_API_PORT must be <= 65535'),
        ({
            'MARKET_CONNECTOR_DERIBIT_HEARTBEAT_INTERVAL': '9',
        }, 'MARKET_CONNECTOR_DERIBIT_HEARTBEAT_INTERVAL must be >= 10'),
        ({
            'MARKET_CONNECTOR_REDIS_HOST': ' ',
        }, 'MARKET_CONNECTOR_REDIS_HOST is required'),
        ({
            'MARKET_CONNECTOR_REDIS_PORT': '0',
        }, 'MARKET_CONNECTOR_REDIS_PORT must be >= 1'),
        ({
            'MARKET_CONNECTOR_SERVICE_NAME': ' ',
        }, 'MARKET_CONNECTOR_SERVICE_NAME is required'),
    ],
)
def test_settings_rejects_invalid_environment_values(env, message):
    with pytest.raises(ConfigError, match=message):
        Settings.from_env(env)
