from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_csrf
from app.connectors.configuration import connector_is_ready, enabled_registry
from app.connectors.runtime import build_runtime_registry
from app.core.database import get_db
from app.models.entities import AuditEvent, IdentityProfile, ScanSchedule, User
from app.schemas.schedules import ScheduleCreate, ScheduleRead, ScheduleUpdate

router = APIRouter(prefix="/schedules", tags=["surveillance"])


def _owned_schedule(schedule_id: str, user: User, db: Session) -> ScanSchedule:
    schedule = db.scalar(
        select(ScanSchedule).where(
            ScanSchedule.id == schedule_id, ScanSchedule.owner_id == user.id
        )
    )
    if schedule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Planification introuvable")
    return schedule


@router.get("", response_model=list[ScheduleRead])
def list_schedules(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ScanSchedule]:
    return list(
        db.scalars(
            select(ScanSchedule)
            .where(ScanSchedule.owner_id == user.id)
            .order_by(ScanSchedule.created_at.desc())
        )
    )


@router.post(
    "",
    response_model=ScheduleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_schedule(
    payload: ScheduleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanSchedule:
    profile = db.scalar(
        select(IdentityProfile).where(
            IdentityProfile.id == payload.profile_id,
            IdentityProfile.owner_id == user.id,
        )
    )
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil introuvable")
    connector_ids = list(dict.fromkeys(value.strip() for value in payload.connector_ids))
    allowed = set(enabled_registry(db, build_runtime_registry()).identifiers())
    if not connector_ids or set(connector_ids) - allowed:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Connecteur inconnu ou désactivé",
        )
    registry = build_runtime_registry()
    if any(
        not connector_is_ready(
            db,
            connector_id,
            registry.get(connector_id).metadata.requires_api_key,
        )
        for connector_id in connector_ids
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Un connecteur sélectionné n’est pas configuré",
        )
    if set(connector_ids) & {"brave", "searxng"} and not payload.external_search_consent:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Confirmation requise pour la transmission à un moteur de recherche externe",
        )
    schedule = ScanSchedule(
        owner_id=user.id,
        profile_id=profile.id,
        connector_ids=connector_ids,
        cadence=payload.cadence,
        next_run_at=datetime.now(UTC),
    )
    db.add(schedule)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="schedule.create",
            resource_type="schedule",
            resource_id=schedule.id,
            details={
                "cadence": payload.cadence,
                "external_search_consent": payload.external_search_consent,
            },
        )
    )
    db.commit()
    db.refresh(schedule)
    return schedule


@router.patch(
    "/{schedule_id}",
    response_model=ScheduleRead,
    dependencies=[Depends(require_csrf)],
)
def update_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanSchedule:
    schedule = _owned_schedule(schedule_id, user, db)
    schedule.enabled = payload.enabled
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="schedule.update",
            resource_type="schedule",
            resource_id=schedule.id,
            details={"enabled": payload.enabled},
        )
    )
    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_schedule(
    schedule_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    schedule = _owned_schedule(schedule_id, user, db)
    resource_id = schedule.id
    db.delete(schedule)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="schedule.delete",
            resource_type="schedule",
            resource_id=resource_id,
        )
    )
    db.commit()
