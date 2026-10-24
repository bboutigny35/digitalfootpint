from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import ScanStatus, VerificationStatus
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


class ResultPageRead(BaseModel):
    items: list[ResultRead]
    total: int
    page: int
    page_size: int
    pages: int


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
