from typing import Literal

from pydantic import (
    HttpUrl,
    PostgresDsn,
    computed_field,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal["development", "production"] = "development"

    admin_api_key: str
    client_api_key: str

    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expire_days: int

    database_url: str | None = None

    gemini_api_key: str
    gemini_model: str
    gemini_pro_model: str
    gemini_lite_model: str
    gemini_tts_model: str

    exa_api_key: str

    # Local development only
    postgres_password: str | None = None
    postgres_user: str | None = None
    postgres_db: str | None = None
    postgres_server: str | None = None
    postgres_port: int | None = None

    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_server: str

    s3_public_domain: str | None = None

    sentry_dsn: HttpUrl | None = None
    sentry_traces_sample_rate: float | None = None

    credit_per_episode: int = 1
    credit_per_extended_episode: int = 2

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_url(self) -> PostgresDsn:
        if self.database_url:
            # Ensure the async driver is used.
            return self.database_url.replace("postgresql://", "postgresql+psycopg://")

        # Fallback during local development
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_server,
            port=self.postgres_port,
            path=self.postgres_db,
        )

    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )


settings = Settings()
