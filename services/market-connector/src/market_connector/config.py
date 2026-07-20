from dataclasses import dataclass
from os import environ
from typing import Mapping


class ConfigError(ValueError):
    '''
    Raised when environment configuration is invalid.
    '''


DEFAULT_API_HOST = '127.0.0.1'
DEFAULT_API_PORT = 8000
DEFAULT_API_RELOAD = False
DEFAULT_DERIBIT_TESTNET = True
DEFAULT_DERIBIT_HEARTBEAT_INTERVAL = 10
DEFAULT_REDIS_ENABLED = True
DEFAULT_REDIS_HOST = '100.117.164.15'
DEFAULT_REDIS_PORT = 6379
DEFAULT_SERVICE_NAME = 'market-connector'


@dataclass(frozen=True, slots=True)
class Settings:
    '''
    Runtime settings for market-connector.
    '''

    api_host: str = DEFAULT_API_HOST
    api_port: int = DEFAULT_API_PORT
    api_reload: bool = DEFAULT_API_RELOAD
    deribit_testnet: bool = DEFAULT_DERIBIT_TESTNET
    deribit_heartbeat_interval: int | None = DEFAULT_DERIBIT_HEARTBEAT_INTERVAL
    redis_enabled: bool = DEFAULT_REDIS_ENABLED
    redis_host: str = DEFAULT_REDIS_HOST
    redis_port: int = DEFAULT_REDIS_PORT
    service_name: str = DEFAULT_SERVICE_NAME

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> 'Settings':
        '''
        Build settings from environment variables.
        '''

        env = environ if env is None else env

        return cls(
            api_host=env.get('MARKET_CONNECTOR_API_HOST', DEFAULT_API_HOST).strip(),
            api_port=_int_env(
                env=env,
                name='MARKET_CONNECTOR_API_PORT',
                default=DEFAULT_API_PORT,
                minimum=1,
                maximum=65535,
            ),
            api_reload=_bool_env(
                env=env,
                name='MARKET_CONNECTOR_API_RELOAD',
                default=DEFAULT_API_RELOAD,
            ),
            deribit_testnet=_bool_env(
                env=env,
                name='MARKET_CONNECTOR_DERIBIT_TESTNET',
                default=DEFAULT_DERIBIT_TESTNET,
            ),
            deribit_heartbeat_interval=_optional_int_env(
                env=env,
                name='MARKET_CONNECTOR_DERIBIT_HEARTBEAT_INTERVAL',
                default=DEFAULT_DERIBIT_HEARTBEAT_INTERVAL,
                minimum=10,
            ),
            redis_enabled=_bool_env(
                env=env,
                name='MARKET_CONNECTOR_REDIS_ENABLED',
                default=DEFAULT_REDIS_ENABLED,
            ),
            redis_host=_required_env(
                value=env.get('MARKET_CONNECTOR_REDIS_HOST', DEFAULT_REDIS_HOST),
                name='MARKET_CONNECTOR_REDIS_HOST',
            ),
            redis_port=_int_env(
                env=env,
                name='MARKET_CONNECTOR_REDIS_PORT',
                default=DEFAULT_REDIS_PORT,
                minimum=1,
                maximum=65535,
            ),
            service_name=_required_env(
                value=env.get('MARKET_CONNECTOR_SERVICE_NAME', DEFAULT_SERVICE_NAME),
                name='MARKET_CONNECTOR_SERVICE_NAME',
            ),
        )


def _bool_env(
    *,
    env: Mapping[str, str],
    name: str,
    default: bool,
) -> bool:
    value = env.get(name)
    if value is None:
        return default

    normalized_value = value.strip().lower()
    if normalized_value in {'1', 'true', 'yes', 'on'}:
        return True

    if normalized_value in {'0', 'false', 'no', 'off'}:
        return False

    raise ConfigError(f'{name} must be a boolean')


def _int_env(
    *,
    env: Mapping[str, str],
    name: str,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw_value = env.get(name)
    if raw_value is None:
        value = default
    else:
        try:
            value = int(raw_value.strip())
        except ValueError as exc:
            raise ConfigError(f'{name} must be an integer') from exc

    if minimum is not None and value < minimum:
        raise ConfigError(f'{name} must be >= {minimum}')

    if maximum is not None and value > maximum:
        raise ConfigError(f'{name} must be <= {maximum}')

    return value


def _optional_int_env(
    *,
    env: Mapping[str, str],
    name: str,
    default: int | None,
    minimum: int | None = None,
) -> int | None:
    raw_value = env.get(name)
    if raw_value is None:
        return default

    if raw_value.strip().lower() in {'', 'none', 'null', 'off'}:
        return None

    return _int_env(
        env=env,
        name=name,
        default=default or 0,
        minimum=minimum,
    )


def _required_env(*, value: str, name: str) -> str:
    value = value.strip()
    if not value:
        raise ConfigError(f'{name} is required')

    return value
