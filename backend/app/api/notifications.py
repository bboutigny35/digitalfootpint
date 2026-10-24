from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_csrf
from app.core.database import get_db
from app.models.entities import AuditEvent, Notification, NotificationPreference, User
from app.schemas.notifications import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    NotificationRead,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.owner_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
    )


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    dependencies=[Depends(require_csrf)],
)
def mark_notification_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.owner_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification introuvable")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
    return notification


@router.get("/preferences", response_model=NotificationPreferenceRead)
def get_notification_preferences(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> NotificationPreferenceRead:
    preference = db.get(NotificationPreference, user.id)
    return NotificationPreferenceRead(
        notify_new_mentions=preference.notify_new_mentions if preference else True
    )


@router.patch(
    "/preferences",
    response_model=NotificationPreferenceRead,
    dependencies=[Depends(require_csrf)],
)
def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPreference:
    preference = db.get(NotificationPreference, user.id)
    if preference is None:
        preference = NotificationPreference(owner_id=user.id)
        db.add(preference)
    preference.notify_new_mentions = payload.notify_new_mentions
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="notification_preferences.update",
            resource_type="notification_preferences",
            resource_id=None,
            details={"notify_new_mentions": payload.notify_new_mentions},
        )
    )
    db.commit()
    db.refresh(preference)
    return preference
