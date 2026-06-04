from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gpms_base_url: str = "https://apimx.gpms-vt.com"
    gpms_email: str = ""
    gpms_password: str = ""

    database_url: str = (
        "postgresql+psycopg2://brazos:brazos@localhost:5432/brazos_gpms"
    )

    hums_poll_interval_seconds: int = 600
    fdm_poll_interval_seconds: int = 600
    gpms_token_renewal_days: int = 7

    fdm_operations_fetch_limit: int = 500

    gpms_portal_asset_url: str = ""

    @field_validator("database_url")
    @classmethod
    def database_must_be_postgres(cls, value: str) -> str:
        if not value.startswith("postgresql"):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL URL "
                "(postgresql+psycopg2://...). SQLite is not supported."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
