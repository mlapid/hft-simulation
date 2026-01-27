from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    grafana_host: str = Field(default='localhost', validation_alias='GRAFANA_HOST')
    grafana_port: int = Field(default=3000, validation_alias='GRAFANA_PORT')
    grafana_user: str = Field(default='root', validation_alias='GRAFANA_USER')
    grafana_password: str = Field(default='root', validation_alias='GRAFANA_PASSWORD')
    grafana_token: str = Field(default='', validation_alias='grafana_token')

    redis_host: str = Field(default='localhost', validation_alias='REDIS_HOST')
    redis_port: int = Field(default=6379, validation_alias='REDIS_PORT')
    redis_db: int = Field(default=0, validation_alias='REDIS_DB')

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / '.env',
        secrets_dir='/run/secrets',
        extra='ignore'
    )