"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated configuration required by database and protected features."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: PostgresDsn = Field(validation_alias="DATABASE_URL")
    jwt_secret: SecretStr = Field(validation_alias="JWT_SECRET")
    jwt_issuer: str = Field(validation_alias="JWT_ISSUER")
    jwt_audience: str = Field(validation_alias="JWT_AUDIENCE")
    jwt_expire_minutes: int = Field(default=30, validation_alias="JWT_EXPIRE_MINUTES", gt=0)
    mock_webhook_secret: SecretStr = Field(validation_alias="MOCK_WEBHOOK_SECRET")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    alembic_expected_revision: str | None = Field(
        default=None,
        validation_alias="ALEMBIC_EXPECTED_REVISION",
    )
    seed_admin_email: str = Field(validation_alias="SEED_ADMIN_EMAIL")
    seed_admin_password: SecretStr = Field(validation_alias="SEED_ADMIN_PASSWORD")


@lru_cache
def get_settings() -> Settings:
    """Load configuration lazily so public liveness checks need no secrets or DB."""
    return Settings()
