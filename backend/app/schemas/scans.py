from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import ScanStatus, VerificationStatus
from app.schemas.discovery import PlatformStatus
from app.services.scan_comparison import ComparisonCategory


class ScanCreate(BaseModel):
    profile_id: str
    connector_ids: list[str] = Field(min_length=1, max_length=25)
    external_search_consent: bool = False


class ScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    status: ScanStatus
    connector_ids: list[str]
    progress: float
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    scan_id: str
    connector_id: str
    canonical_url: str
    domain: str
    title: str
    snippet: str
    match_type: str
    verification_status: VerificationStatus
    relevance_score: float
    score_explanation: dict[str, object]
    discovered_at: datetime
    last_checked_at: datetime
    published_at: datetime | None


class ResultVerificationUpdate(BaseModel):
    verification_status: VerificationStatus


class EvidenceMatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    criterion_type: str
    match_kind: str
    weight: float
    explanation: str


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    evidence_type: str
    excerpt: str
    source_url: str
    source_hash: str
    provenance: dict[str, object]
    observed_at: datetime
    matches: list[EvidenceMatchRead]


class ValidationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    decision: Literal["confirmed", "rejected", "uncertain"]
    exclusion_kind: Literal["homonym"] | None
    attributed_profile_id: str | None
    reused_from_validation_id: str | None
    created_at: datetime
    updated_at: datetime


class CorrelationRead(BaseModel):
    id: str
    result_id: str
    relevance_score: float
    attribution_score: float
    explanation: dict[str, object]
    contradictions: list[str]
    evidence_count: int
    evidence: list[EvidenceRead]
    validation: ValidationRead | None


class ValidationUpdate(BaseModel):
    decision: Literal["confirmed", "rejected", "uncertain"]
    exclusion_kind: Literal["homonym"] | None = None
    attributed_profile_id: str | None = None
    add_confirmed_profile: bool = False


class ResultPageRead(BaseModel):
    items: list[ResultRead]
    total: int
    page: int
    page_size: int
    pages: int


class CrawlQueueStatusRead(BaseModel):
    scan_id: str
    counts: dict[str, int]


class PlatformCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    platform_identifier: str
    connector_id: str | None
    verification_method: str
    status: PlatformStatus
    result_count: int
    error_code: str | None
    checked_at: datetime


class PlatformCheckListRead(BaseModel):
    scan_id: str
    items: list[PlatformCheckRead]
    methodology_note: str


class ScanComparisonItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: ComparisonCategory
    canonical_url: str
    domain: str
    connector_id: str
    title: str
    baseline_result_id: str | None
    current_result_id: str | None
    changed_fields: tuple[str, ...]


class ScanComparisonRead(BaseModel):
    baseline_scan_id: str
    current_scan_id: str
    profile_id: str
    counts: dict[ComparisonCategory, int]
    items: list[ScanComparisonItemRead]
    methodology_note: str
