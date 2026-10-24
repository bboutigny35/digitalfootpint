from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.services.normalization import normalize_text

PlatformStatus = Literal[
    "PUBLIC_MATCH",
    "POSSIBLE_MATCH",
    "NO_PUBLIC_RESULT",
    "USER_VERIFIED",
    "NOT_VERIFIABLE",
    "RATE_LIMITED",
    "ACCESS_RESTRICTED",
    "ERROR",
]


class PlatformCatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    identifier: str
    display_name: str
    category: str
    verification_method: str
    default_status: PlatformStatus
    connector_id: str | None
    priority: int
    limitations: str | None
    last_checked_at: datetime | None
    last_error_code: str | None


class WebSourceCreate(BaseModel):
    base_url: HttpUrl
    category: str = Field(min_length=1, max_length=80)
    access_method: Literal["api", "sitemap", "feed", "archive", "public_html", "manual"]
    priority: int = Field(default=100, ge=1, le=1000)
    cache_ttl_seconds: int = Field(default=86400, ge=300, le=2592000)
    rate_limit_per_minute: int = Field(default=5, ge=1, le=120)
    restrictions: list[str] = Field(default_factory=list, max_length=25)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        return normalize_text(value).casefold().replace(" ", "_")

    @field_validator("restrictions")
    @classmethod
    def normalize_restrictions(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(normalize_text(value) for value in values if value.strip()))


class WebSourceUpdate(BaseModel):
    state: Literal["pending", "active", "suspended", "error"] | None = None
    priority: int | None = Field(default=None, ge=1, le=1000)
    cache_ttl_seconds: int | None = Field(default=None, ge=300, le=2592000)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=120)
    restrictions: list[str] | None = Field(default=None, max_length=25)

    @field_validator("restrictions")
    @classmethod
    def normalize_optional_restrictions(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        return list(dict.fromkeys(normalize_text(value) for value in values if value.strip()))


class WebSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    domain: str
    base_url: str
    category: str
    access_method: str
    state: str
    priority: int
    cache_ttl_seconds: int
    rate_limit_per_minute: int
    restrictions: list[str]
    discovered_url_count: int
    crawled_page_count: int
    last_checked_at: datetime | None
    last_error_code: str | None
    created_at: datetime
    updated_at: datetime
