from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from app.services.normalization import normalize_phone, normalize_text
from app.services.search_strategy import QueryScope, SearchMode


class ProfileBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    name_variants: list[str] = Field(default_factory=list, max_length=50)
    pseudonyms: list[str] = Field(default_factory=list, max_length=100)
    former_pseudonyms: list[str] = Field(default_factory=list, max_length=100)
    emails: list[EmailStr] = Field(default_factory=list, max_length=50)
    phone_numbers: list[str] = Field(default_factory=list, max_length=25)
    city_region: str | None = Field(default=None, max_length=255)
    profession: str | None = Field(default=None, max_length=255)
    employers: list[str] = Field(default_factory=list, max_length=50)
    domains: list[str] = Field(default_factory=list, max_length=50)
    websites: list[HttpUrl] = Field(default_factory=list, max_length=50)
    social_profiles: list[HttpUrl] = Field(default_factory=list, max_length=100)
    confirmed_profiles: list[HttpUrl] = Field(default_factory=list, max_length=100)
    keywords: list[str] = Field(default_factory=list, max_length=100)
    exact_phrases: list[str] = Field(default_factory=list, max_length=50)
    exclusions: list[str] = Field(default_factory=list, max_length=100)
    context: str | None = Field(default=None, max_length=4000)

    @field_validator(
        "name_variants",
        "pseudonyms",
        "former_pseudonyms",
        "employers",
        "domains",
        "keywords",
        "exact_phrases",
        "exclusions",
    )
    @classmethod
    def normalize_lists(cls, values: list[str]) -> list[str]:
        cleaned = [normalize_text(value) for value in values if normalize_text(value)]
        unique: dict[str, str] = {}
        for value in cleaned:
            unique.setdefault(value.casefold(), value)
        return list(unique.values())

    @field_validator("phone_numbers")
    @classmethod
    def normalize_phone_numbers(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(normalize_phone(value) for value in values))

    @field_validator("first_name", "last_name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("city_region", "profession", "context")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_text(value)
        return normalized or None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileRead(ProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class PlannedQueryRead(BaseModel):
    text: str
    kind: str
    priority: int
    scope: QueryScope
    criteria: tuple[str, ...]
    requires_corroboration: bool


class SearchPlanRead(BaseModel):
    mode: SearchMode
    queries: list[PlannedQueryRead]
    budget: int
    truncated: bool
    stages: tuple[str, ...]
