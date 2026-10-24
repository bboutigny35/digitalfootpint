from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_csrf
from app.core.database import get_db
from app.models.entities import AuditEvent, RemovalRequest, Result, User
from app.schemas.removal_requests import (
    RemovalLetterRead,
    RemovalRequestCreate,
    RemovalRequestRead,
    RemovalRequestUpdate,
)
from app.services.removal_letters import prepare_removal_letter

router = APIRouter(prefix="/removal-requests", tags=["demandes de suppression"])


def _owned_request(request_id: str, user: User, db: Session) -> RemovalRequest:
    removal = db.scalar(
        select(RemovalRequest).where(
            RemovalRequest.id == request_id,
            RemovalRequest.owner_id == user.id,
        )
    )
    if removal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande introuvable")
    return removal


@router.get("", response_model=list[RemovalRequestRead])
def list_removal_requests(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[RemovalRequest]:
    return list(
        db.scalars(
            select(RemovalRequest)
            .where(RemovalRequest.owner_id == user.id)
            .order_by(RemovalRequest.updated_at.desc())
        )
    )


@router.post(
    "",
    response_model=RemovalRequestRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_removal_request(
    payload: RemovalRequestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RemovalRequest:
    if payload.result_id is not None:
        result = db.scalar(
            select(Result).where(Result.id == payload.result_id, Result.owner_id == user.id)
        )
        if result is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mention introuvable")
    removal = RemovalRequest(
        owner_id=user.id,
        result_id=payload.result_id,
        organization=payload.organization.strip(),
        notes=payload.notes,
    )
    db.add(removal)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="removal_request.create",
            resource_type="removal_request",
            resource_id=removal.id,
        )
    )
    db.commit()
    db.refresh(removal)
    return removal


@router.patch(
    "/{request_id}",
    response_model=RemovalRequestRead,
    dependencies=[Depends(require_csrf)],
)
def update_removal_request(
    request_id: str,
    payload: RemovalRequestUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RemovalRequest:
    removal = _owned_request(request_id, user, db)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(removal, field, value)
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="removal_request.update",
            resource_type="removal_request",
            resource_id=removal.id,
            details={"fields": sorted(changes)},
        )
    )
    db.commit()
    db.refresh(removal)
    return removal


@router.get("/{request_id}/letter", response_model=RemovalLetterRead)
def get_removal_letter(
    request_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RemovalLetterRead:
    removal = _owned_request(request_id, user, db)
    result = (
        db.scalar(
            select(Result).where(
                Result.id == removal.result_id,
                Result.owner_id == user.id,
            )
        )
        if removal.result_id
        else None
    )
    subject, body = prepare_removal_letter(removal, result)
    return RemovalLetterRead(
        request_id=removal.id,
        subject=subject,
        body=body,
        warning=(
            "Modèle à vérifier et envoyer manuellement. "
            "Aucun envoi automatique n'est effectué."
        ),
    )


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_removal_request(
    request_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    removal = _owned_request(request_id, user, db)
    resource_id = removal.id
    db.delete(removal)
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="removal_request.delete",
            resource_type="removal_request",
            resource_id=resource_id,
        )
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
