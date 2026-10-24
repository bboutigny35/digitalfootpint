from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.entities import utcnow, uuid4_str
from app.sensitive_monitor.types import (
    CheckStatus,
    FindingStatus,
    RiskLevel,
    SensitiveCategory,
)


class SensitiveDescriptor(Base):
    __tablename__ = "sensitive_descriptors"
    __table_args__ = (
        Index("ix_sensitive_owner_fingerprint", "owner_id", "fingerprint", unique=True),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[SensitiveCategory] = mapped_column(Enum(SensitiveCategory), index=True)
    masked_label: Mapped[str] = mapped_column(String(160))
    fingerprint: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SensitiveConsent(Base):
    __tablename__ = "sensitive_consents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[SensitiveCategory] = mapped_column(Enum(SensitiveCategory))
    authorization_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    proof_reference: Mapped[str | None] = mapped_column(String(200))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SensitiveCheck(Base):
    __tablename__ = "sensitive_checks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    descriptor_id: Mapped[str | None] = mapped_column(
        ForeignKey("sensitive_descriptors.id", ondelete="SET NULL"), index=True
    )
    category: Mapped[SensitiveCategory] = mapped_column(Enum(SensitiveCategory), index=True)
    provider_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus), default=CheckStatus.PENDING)
    external_transmission: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SensitiveFinding(Base):
    __tablename__ = "sensitive_findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    check_id: Mapped[str] = mapped_column(
        ForeignKey("sensitive_checks.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[SensitiveCategory] = mapped_column(Enum(SensitiveCategory))
    source_label: Mapped[str] = mapped_column(String(160))
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel))
    verification_status: Mapped[FindingStatus] = mapped_column(Enum(FindingStatus))
    recommendation: Mapped[str] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SensitiveAlert(Base):
    __tablename__ = "sensitive_alerts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("sensitive_findings.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[SensitiveCategory] = mapped_column(Enum(SensitiveCategory))
    source_label: Mapped[str] = mapped_column(String(160))
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel))
    recommendation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
