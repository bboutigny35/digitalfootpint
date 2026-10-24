from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.entities import RemovalRequestStatus


class RemovalRequestCreate(BaseModel):
    result_id: str | None = None
    organization: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("organization")
    @classmethod
    def normalize_organization(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("L'organisme est requis")
        return normalized


class RemovalRequestUpdate(BaseModel):
    status: RemovalRequestStatus | None = None
    requested_at: datetime | None = None
    response_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=5000)
    response_notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def reject_empty_update(self) -> "RemovalRequestUpdate":
        if not self.model_fields_set:
            raise ValueError("Au moins une modification est requise")
        return self


class RemovalRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    result_id: str | None
    organization: str
    status: RemovalRequestStatus
    requested_at: datetime | None
    response_at: datetime | None
    notes: str | None
    response_notes: str | None
    created_at: datetime
    updated_at: datetime


class RemovalLetterRead(BaseModel):
    request_id: str
    subject: str
    body: str
    warning: str
