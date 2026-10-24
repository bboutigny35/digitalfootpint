import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def uuid4_str() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VerificationStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    UNCERTAIN = "uncertain"
    FALSE_POSITIVE = "false_positive"
    IGNORED = "ignored"


class RemovalRequestStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user: Mapped[User] = relationship()


class IdentityProfile(Base):
    __tablename__ = "identity_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    name_variants: Mapped[list[str]] = mapped_column(JSON, default=list)
    pseudonyms: Mapped[list[str]] = mapped_column(JSON, default=list)
    former_pseudonyms: Mapped[list[str]] = mapped_column(JSON, default=list)
    emails: Mapped[list[str]] = mapped_column(JSON, default=list)
    phone_numbers: Mapped[list[str]] = mapped_column(JSON, default=list)
    city_region: Mapped[str | None] = mapped_column(String(255))
    profession: Mapped[str | None] = mapped_column(String(255))
    employers: Mapped[list[str]] = mapped_column(JSON, default=list)
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    websites: Mapped[list[str]] = mapped_column(JSON, default=list)
    social_profiles: Mapped[list[str]] = mapped_column(JSON, default=list)
    confirmed_profiles: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    exact_phrases: Mapped[list[str]] = mapped_column(JSON, default=list)
    exclusions: Mapped[list[str]] = mapped_column(JSON, default=list)
    context: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Scan(Base):
    __tablename__ = "scans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("identity_profiles.id", ondelete="CASCADE"))
    status: Mapped[ScanStatus] = mapped_column(Enum(ScanStatus), default=ScanStatus.QUEUED)
    connector_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_code: Mapped[str | None] = mapped_column(String(100))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    lease_owner: Mapped[str | None] = mapped_column(String(100), index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScanSchedule(Base):
    __tablename__ = "scan_schedules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("identity_profiles.id", ondelete="CASCADE"), index=True
    )
    connector_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    cadence: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProviderThrottle(Base):
    __tablename__ = "provider_throttles"
    connector_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    next_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ConnectorSecret(Base):
    __tablename__ = "connector_secrets"
    connector_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    ciphertext: Mapped[str] = mapped_column(Text)
    key_version: Mapped[str] = mapped_column(String(50), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ConnectorConfiguration(Base):
    __tablename__ = "connector_configurations"
    connector_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class PlatformCatalogEntry(Base):
    __tablename__ = "platform_catalog"
    identifier: Mapped[str] = mapped_column(String(100), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80), index=True)
    verification_method: Mapped[str] = mapped_column(String(80))
    default_status: Mapped[str] = mapped_column(String(40))
    connector_id: Mapped[str | None] = mapped_column(String(100), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    limitations: Mapped[str | None] = mapped_column(Text)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class WebSource(Base):
    __tablename__ = "web_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    base_url: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), index=True)
    access_method: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    cache_ttl_seconds: Mapped[int] = mapped_column(Integer, default=86400)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=5)
    restrictions: Mapped[list[str]] = mapped_column(JSON, default=list)
    discovered_url_count: Mapped[int] = mapped_column(Integer, default=0)
    crawled_page_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class DiscoveryJob(Base):
    __tablename__ = "discovery_jobs"
    __table_args__ = (
        UniqueConstraint("scan_id", "source_id", name="uq_discovery_job_scan_source"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("web_sources.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    lease_owner: Mapped[str | None] = mapped_column(String(100), index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DiscoveredURL(Base):
    __tablename__ = "discovered_urls"
    __table_args__ = (UniqueConstraint("scan_id", "url_hash", name="uq_discovered_url_scan_hash"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("web_sources.id", ondelete="SET NULL"), index=True
    )
    original_url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64))
    domain: Mapped[str] = mapped_column(String(255), index=True)
    discovery_method: Mapped[str] = mapped_column(String(80))
    depth: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), index=True)
    discovered_url_id: Mapped[str] = mapped_column(
        ForeignKey("discovered_urls.id", ondelete="CASCADE"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    lease_owner: Mapped[str | None] = mapped_column(String(100), index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CrawlResult(Base):
    __tablename__ = "crawl_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    crawl_job_id: Mapped[str] = mapped_column(
        ForeignKey("crawl_jobs.id", ondelete="CASCADE"), unique=True, index=True
    )
    http_status: Mapped[int | None] = mapped_column(Integer)
    final_url: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(255))
    content_length: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    cache_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class CrawlStatistics(Base):
    __tablename__ = "crawl_statistics"
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), primary_key=True
    )
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    queued_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    bytes_downloaded: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), index=True)
    result_id: Mapped[str | None] = mapped_column(
        ForeignKey("results.id", ondelete="CASCADE"), index=True
    )
    crawl_result_id: Mapped[str | None] = mapped_column(
        ForeignKey("crawl_results.id", ondelete="CASCADE"), index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(80), index=True)
    excerpt: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvidenceMatch(Base):
    __tablename__ = "evidence_matches"
    __table_args__ = (
        UniqueConstraint(
            "evidence_id", "criterion_type", "criterion_hash", name="uq_evidence_match"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True
    )
    criterion_type: Mapped[str] = mapped_column(String(80), index=True)
    criterion_hash: Mapped[str] = mapped_column(String(64))
    match_kind: Mapped[str] = mapped_column(String(40))
    weight: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)


class IdentityCorrelation(Base):
    __tablename__ = "identity_correlations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    result_id: Mapped[str] = mapped_column(
        ForeignKey("results.id", ondelete="CASCADE"), unique=True, index=True
    )
    relevance_score: Mapped[float] = mapped_column(Float)
    attribution_score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSON)
    contradictions: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class UserValidation(Base):
    __tablename__ = "user_validations"
    __table_args__ = (
        UniqueConstraint("owner_id", "correlation_id", name="uq_user_validation_correlation"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    correlation_id: Mapped[str] = mapped_column(
        ForeignKey("identity_correlations.id", ondelete="CASCADE"), index=True
    )
    decision: Mapped[str] = mapped_column(String(30), index=True)
    exclusion_kind: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ReportExport(Base):
    __tablename__ = "report_exports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("identity_profiles.id", ondelete="SET NULL"), index=True
    )
    export_format: Mapped[str] = mapped_column(String(10))
    report_kind: Mapped[str] = mapped_column(String(20))
    result_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (Index("ix_result_scan_canonical", "scan_id", "canonical_url", unique=True),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("identity_profiles.id", ondelete="CASCADE"))
    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"))
    connector_id: Mapped[str] = mapped_column(String(100), index=True)
    canonical_url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(Text)
    snippet: Mapped[str] = mapped_column(Text)
    match_type: Mapped[str] = mapped_column(String(100))
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.UNCERTAIN
    )
    relevance_score: Mapped[float] = mapped_column(Float)
    score_explanation: Mapped[dict[str, Any]] = mapped_column(JSON)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RemovalRequest(Base):
    __tablename__ = "removal_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    result_id: Mapped[str | None] = mapped_column(
        ForeignKey("results.id", ondelete="SET NULL"), index=True
    )
    organization: Mapped[str] = mapped_column(String(255))
    status: Mapped[RemovalRequestStatus] = mapped_column(
        Enum(RemovalRequestStatus), default=RemovalRequestStatus.DRAFT, index=True
    )
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    response_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    notify_new_mentions: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("owner_id", "scan_id", "kind", name="uq_notification_scan_kind"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scan_id: Mapped[str | None] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
