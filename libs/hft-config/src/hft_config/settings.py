from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        frozen=True
    )

    grafana_port: int = Field(
        validation_alias='GRAFANA_PORT',
        description='The port of the Grafana API',
    )

    grafana_token: SecretStr = Field(
        validation_alias='GRAFANA_TOKEN',
        description='The token of the Grafana API',
    )

    redis_port: int = Field(
        validation_alias='REDIS_PORT',
        description='The port of the Redis server',
    )

    pi_tailscale_ip: str = Field(
        validation_alias='PI_TAILSCALE_IP',
        description='The IP address of the Pi Tailscale node',
    )