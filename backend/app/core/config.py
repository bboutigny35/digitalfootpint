from functools import lru_cache
from pathlib import Path
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).parents[3] / ".env",
            ".env",
            "/etc/digitalfootprint/digitalfootprint.env",
        ),
        env_prefix="DIGITALFOOTPRINT_",
        extra="ignore",
    )

    app_name: str = "DigitalFootprint"
    environment: str = "development"
    database_url: str = "sqlite:///./digitalfootprint.db"
    secret_key: str = Field(default="development-only-change-this-key-now", min_length=32)
    allowed_hosts: Annotated[list[str], NoDecode] = ["localhost", "127.0.0.1"]
    cors_origins: Annotated[list[str], NoDecode] = ["http://127.0.0.1:5173"]
    cookie_secure: bool = False
    session_ttl_hours: int = Field(default=12, ge=1, le=168)
    login_window_seconds: int = Field(default=300, ge=60)
    login_max_attempts: int = Field(default=5, ge=1, le=20)
    sensitive_retention_interval_seconds: int = Field(default=86400, ge=300, le=604800)
    scan_worker_poll_seconds: float = Field(default=2.0, ge=0.2, le=60)
    github_api_token: str | None = Field(default=None, repr=False)
    brave_api_token: str | None = Field(default=None, repr=False)
    searxng_url: str | None = Field(default=None, repr=False)
    connector_secret_keys: Annotated[list[str], NoDecode] = Field(
        default_factory=list, repr=False
    )
    connector_secret_active_key: str | None = None

    @field_validator("allowed_hosts", "cors_origins", "connector_secret_keys", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("searxng_url")
    @classmethod
    def validate_searxng_url(cls, value: str | None) -> str | None:
        allowed = {
            "http://127.0.0.1:8888/search",
            "http://searxng:8080/search",
        }
        if value is not None and value.rstrip("/") not in allowed:
            raise ValueError("DIGITALFOOTPRINT_SEARXNG_URL doit viser l’instance SearXNG locale")
        return value.rstrip("/") if value else None

    @model_validator(mode="after")
    def reject_insecure_production_secret(self) -> Self:
        insecure_prefixes = ("development-", "replace-with-", "test-secret-")
        if self.environment == "production" and self.secret_key.startswith(insecure_prefixes):
            raise ValueError("DIGITALFOOTPRINT_SECRET_KEY doit être remplacée en production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
