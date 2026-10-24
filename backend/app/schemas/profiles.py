from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from app.services.search_strategy import QueryScope, SearchMode


class ProfileBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    name_variants: list[str] = Field(default_factory=list, max_length=50)
    pseudonyms: list[str] = Field(default_factory=list, max_length=100)
    emails: list[EmailStr] = Field(default_factory=list, max_length=50)
    domains: list[str] = Field(default_factory=list, max_length=50)
    websites: list[HttpUrl] = Field(default_factory=list, max_length=50)
    social_profiles: list[HttpUrl] = Field(default_factory=list, max_length=100)
    keywords: list[str] = Field(default_factory=list, max_length=100)
    context: str | None = Field(default=None, max_length=4000)

    @field_validator("name_variants", "pseudonyms", "domains", "keywords")
    @classmethod
    def normalize_lists(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(cleaned))


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
