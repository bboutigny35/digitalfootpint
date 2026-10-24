from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base, build_engine
from app.models.entities import AuditEvent, User
from app.security.passwords import hash_password
from app.sensitive_monitor.models import (
    SensitiveAlert,
    SensitiveCheck,
    SensitiveDescriptor,
    SensitiveFinding,
)
from app.sensitive_monitor.types import (
    CheckStatus,
    FindingStatus,
    RiskLevel,
    SensitiveCategory,
)
from app.workers.retention import purge_expired_descriptors


def test_retention_purge_removes_secret_material_but_preserves_history() -> None:
    engine = build_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    raw_value = "+33612345678"
    with Session(engine, expire_on_commit=False) as db:
        user = User(email="retention@example.test", password_hash=hash_password("not-used-here"))
        db.add(user)
        db.flush()
        expired = SensitiveDescriptor(
            owner_id=user.id,
            category=SensitiveCategory.PHONE,
            masked_label="••••••5678",
            fingerprint="a" * 64,
            retention_expires_at=now - timedelta(seconds=1),
        )
        active = SensitiveDescriptor(
            owner_id=user.id,
            category=SensitiveCategory.IBAN,
            masked_label="FR•• •••• 4321",
            fingerprint="b" * 64,
            retention_expires_at=now + timedelta(days=1),
        )
        db.add_all([expired, active])
        db.flush()
        check = SensitiveCheck(
            owner_id=user.id,
            descriptor_id=expired.id,
            category=SensitiveCategory.PHONE,
            provider_id="authorized-test-source",
            status=CheckStatus.COMPLETED,
            external_transmission=False,
        )
        db.add(check)
        db.flush()
        finding = SensitiveFinding(
            owner_id=user.id,
            check_id=check.id,
            category=SensitiveCategory.PHONE,
            source_label="authorized-test-source",
            risk_level=RiskLevel.HIGH,
            verification_status=FindingStatus.CONFIRMED,
            recommendation="Contacter l’opérateur.",
        )
        db.add(finding)
        db.flush()
        alert = SensitiveAlert(
            owner_id=user.id,
            finding_id=finding.id,
            category=SensitiveCategory.PHONE,
            source_label="authorized-test-source",
            risk_level=RiskLevel.HIGH,
            recommendation=finding.recommendation,
        )
        db.add(alert)
        db.commit()
        expired_id, active_id, check_id, finding_id, alert_id = (
            expired.id,
            active.id,
            check.id,
            finding.id,
            alert.id,
        )

        result = purge_expired_descriptors(db, now=now)

        assert result.deleted_descriptors == 1
        assert db.get(SensitiveDescriptor, expired_id) is None
        assert db.get(SensitiveDescriptor, active_id) is not None
        preserved_check = db.get(SensitiveCheck, check_id)
        assert preserved_check is not None
        db.refresh(preserved_check)
        assert preserved_check.descriptor_id is None
        assert db.get(SensitiveFinding, finding_id) is not None
        assert db.get(SensitiveAlert, alert_id) is not None
        audit = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "sensitive_descriptor.retention_expired")
        )
        assert audit is not None
        assert audit.actor_id is None
        assert audit.details == {"category": "phone", "reason": "retention_expired"}
        assert raw_value not in str(audit.details)
        assert "5678" not in str(audit.details)


def test_retention_purge_is_bounded_and_idempotent() -> None:
    engine = build_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = User(email="batch@example.test", password_hash=hash_password("not-used-here"))
        db.add(user)
        db.flush()
        for position in range(3):
            db.add(
                SensitiveDescriptor(
                    owner_id=user.id,
                    category=SensitiveCategory.PHONE,
                    masked_label=f"••••••{position:04d}",
                    fingerprint=str(position) * 64,
                    retention_expires_at=now - timedelta(minutes=1),
                )
            )
        db.commit()

        assert purge_expired_descriptors(db, now=now, batch_size=2).deleted_descriptors == 2
        assert purge_expired_descriptors(db, now=now, batch_size=2).deleted_descriptors == 1
        assert purge_expired_descriptors(db, now=now, batch_size=2).deleted_descriptors == 0
