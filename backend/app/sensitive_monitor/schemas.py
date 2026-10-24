from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.sensitive_monitor.types import (
    CheckStatus,
    FindingStatus,
    RiskLevel,
    SensitiveCategory,
)
from app.sensitive_monitor.validation import (
    SensitiveValueError,
    validate_address,
    validate_iban,
    validate_phone,
)


class EphemeralValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Literal[SensitiveCategory.NIR, SensitiveCategory.ID_DOCUMENT]
    value: str = Field(min_length=5, max_length=64)


class EphemeralValidationRead(BaseModel):
    category: SensitiveCategory
    valid: bool
    masked_value: str | None = None


class DescriptorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Literal[
        SensitiveCategory.IBAN,
        SensitiveCategory.PHONE,
        SensitiveCategory.POSTAL_ADDRESS,
    ]
    value: str = Field(min_length=8, max_length=300)
    retention_days: int | None = Field(default=None, ge=1, le=365)

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str, info: Any) -> str:
        category = info.data.get("category")
        validators = {
            SensitiveCategory.IBAN: validate_iban,
            SensitiveCategory.PHONE: validate_phone,
            SensitiveCategory.POSTAL_ADDRESS: validate_address,
        }
        try:
            return validators[category](value)
        except (KeyError, SensitiveValueError) as exc:
            raise ValueError("Valeur sensible invalide") from exc


class CardDescriptorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payment_network: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9 -]+$")
    last_four: str = Field(pattern=r"^\d{4}$")


class DescriptorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    category: SensitiveCategory
    masked_label: str
    metadata_json: dict[str, object]
    retention_expires_at: datetime | None
    created_at: datetime


class CheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    descriptor_id: str | None
    category: SensitiveCategory
    provider_id: str
    status: CheckStatus
    external_transmission: bool
    error_code: str | None
    started_at: datetime
    completed_at: datetime | None


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    check_id: str
    category: SensitiveCategory
    source_label: str
    risk_level: RiskLevel
    verification_status: FindingStatus
    recommendation: str
    detected_at: datetime


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    finding_id: str
    category: SensitiveCategory
    source_label: str
    risk_level: RiskLevel
    recommendation: str
    created_at: datetime
    acknowledged_at: datetime | None


class LocalCheckCreate(BaseModel):
    descriptor_id: str


class ConsentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_id: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9_.-]+$")
    category: SensitiveCategory
    authorization_confirmed: Literal[True]
    proof_reference: str | None = Field(default=None, max_length=200)
    expires_at: datetime | None = None
