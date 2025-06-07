from pydantic import (
    PostgresDsn,
    computed_field,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_key: str
    api_key_header_name: str

    gemini_api_key: str
    gemini_model: str
    gemini_tts_model: str

    exa_api_key: str

    postgres_password: str
    postgres_user: str
    postgres_db: str
    postgres_server: str
    postgres_port: int

    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_server: str
    minio_port: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_url(self) -> PostgresDsn:
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
