from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Notification, NotificationPreference, Result, Scan, ScanStatus
from app.services.scan_comparison import ComparisonCategory, compare_results


def create_new_mention_notification(scan: Scan, db: Session) -> Notification | None:
    preference = db.get(NotificationPreference, scan.owner_id)
    if preference is not None and not preference.notify_new_mentions:
        return None
    previous = db.scalar(
        select(Scan)
        .where(
            Scan.owner_id == scan.owner_id,
            Scan.profile_id == scan.profile_id,
            Scan.id != scan.id,
            Scan.status == ScanStatus.COMPLETED,
            Scan.created_at < scan.created_at,
        )
        .order_by(Scan.created_at.desc())
        .limit(1)
    )
    if previous is None:
        return None
    exists = db.scalar(
        select(Notification.id).where(
            Notification.owner_id == scan.owner_id,
            Notification.scan_id == scan.id,
            Notification.kind == "new_mentions",
        )
    )
    if exists is not None:
        return None
    baseline = list(db.scalars(select(Result).where(Result.scan_id == previous.id)))
    current = list(db.scalars(select(Result).where(Result.scan_id == scan.id)))
    count = sum(
        item.category == ComparisonCategory.NEW for item in compare_results(baseline, current)
    )
    if count == 0:
        return None
    notification = Notification(
        owner_id=scan.owner_id,
        scan_id=scan.id,
        kind="new_mentions",
        title="Nouvelles mentions détectées",
        message=f"{count} nouvelle(s) mention(s) publique(s) nécessitent votre vérification.",
    )
    db.add(notification)
    return notification
