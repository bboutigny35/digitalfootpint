import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.entities import AuditEvent
from app.sensitive_monitor.models import SensitiveDescriptor


@dataclass(frozen=True)
class RetentionPurgeResult:
    deleted_descriptors: int
    completed_at: str


def purge_expired_descriptors(
    db: Session,
    *,
    now: datetime | None = None,
    batch_size: int = 500,
) -> RetentionPurgeResult:
    """Delete expired sensitive descriptors without deleting check history."""
    if not 1 <= batch_size <= 5_000:
        raise ValueError("batch_size doit être compris entre 1 et 5000")
    cutoff = now or datetime.now(UTC)
    descriptors = list(
        db.scalars(
            select(SensitiveDescriptor)
            .where(
                SensitiveDescriptor.retention_expires_at.is_not(None),
                SensitiveDescriptor.retention_expires_at <= cutoff,
            )
            .order_by(SensitiveDescriptor.retention_expires_at, SensitiveDescriptor.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
    )
    for descriptor in descriptors:
        db.add(
            AuditEvent(
                actor_id=None,
                action="sensitive_descriptor.retention_expired",
                resource_type="sensitive_descriptor",
                resource_id=descriptor.id,
                details={"category": descriptor.category.value, "reason": "retention_expired"},
            )
        )
        db.delete(descriptor)
    db.commit()
    return RetentionPurgeResult(
        deleted_descriptors=len(descriptors),
        completed_at=cutoff.isoformat(),
    )


def main() -> None:
    """Run one bounded maintenance batch and emit a non-sensitive JSON result."""
    with SessionLocal() as db:
        result = purge_expired_descriptors(db)
    print(json.dumps(asdict(result), sort_keys=True))


if __name__ == "__main__":
    main()
