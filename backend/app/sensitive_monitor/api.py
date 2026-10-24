from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_csrf
from app.core.database import get_db
from app.models.entities import AuditEvent, User
from app.sensitive_monitor.models import (
    SensitiveAlert,
    SensitiveCheck,
    SensitiveConsent,
    SensitiveDescriptor,
    SensitiveFinding,
)
from app.sensitive_monitor.privacy import fingerprint, mask_value
from app.sensitive_monitor.schemas import (
    AlertRead,
    CardDescriptorCreate,
    CheckRead,
    ConsentCreate,
    DescriptorCreate,
    DescriptorRead,
    EphemeralValidationRead,
    EphemeralValidationRequest,
    FindingRead,
    LocalCheckCreate,
)
from app.sensitive_monitor.types import CheckStatus, SensitiveCategory
from app.sensitive_monitor.validation import (
    SensitiveValueError,
    validate_id_document,
    validate_nir,
)

router = APIRouter(prefix="/sensitive-monitor", tags=["exposition sensible"])


def _owned_descriptor(identifier: str, user: User, db: Session) -> SensitiveDescriptor:
    descriptor = db.scalar(
        select(SensitiveDescriptor).where(
            SensitiveDescriptor.id == identifier,
            SensitiveDescriptor.owner_id == user.id,
        )
    )
    if descriptor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Élément surveillé introuvable")
    return descriptor


@router.post(
    "/validate",
    response_model=EphemeralValidationRead,
    dependencies=[Depends(require_csrf)],
)
def validate_ephemeral(payload: EphemeralValidationRequest) -> EphemeralValidationRead:
    try:
        if payload.category == SensitiveCategory.NIR:
            normalized = validate_nir(payload.value)
        else:
            normalized = validate_id_document(payload.value)
    except SensitiveValueError:
        return EphemeralValidationRead(category=payload.category, valid=False)
    return EphemeralValidationRead(
        category=payload.category,
        valid=True,
        masked_value=mask_value(payload.category, normalized),
    )


@router.post(
    "/descriptors",
    response_model=DescriptorRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_descriptor(
    payload: DescriptorCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SensitiveDescriptor:
    expires_at = (
        datetime.now(UTC) + timedelta(days=payload.retention_days)
        if payload.retention_days
        else None
    )
    descriptor = SensitiveDescriptor(
        owner_id=user.id,
        category=payload.category,
        masked_label=mask_value(payload.category, payload.value),
        fingerprint=fingerprint(payload.category, payload.value),
        retention_expires_at=expires_at,
    )
    db.add(descriptor)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Cet élément est déjà surveillé") from exc
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="sensitive_descriptor.create",
            resource_type="sensitive_descriptor",
            resource_id=descriptor.id,
            details={"category": payload.category.value},
        )
    )
    db.commit()
    db.refresh(descriptor)
    return descriptor


@router.post(
    "/cards",
    response_model=DescriptorRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_card_descriptor(
    payload: CardDescriptorCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SensitiveDescriptor:
    normalized = f"{payload.payment_network.lower()}:{payload.last_four}"
    descriptor = SensitiveDescriptor(
        owner_id=user.id,
        category=SensitiveCategory.PAYMENT_CARD,
        masked_label=f"{payload.payment_network} •••• {payload.last_four}",
        fingerprint=fingerprint(SensitiveCategory.PAYMENT_CARD, normalized),
        metadata_json={"payment_network": payload.payment_network, "last_four": payload.last_four},
    )
    db.add(descriptor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette carte est déjà référencée") from exc
    db.refresh(descriptor)
    return descriptor


@router.get("/descriptors", response_model=list[DescriptorRead])
def list_descriptors(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SensitiveDescriptor]:
    return list(
        db.scalars(
            select(SensitiveDescriptor)
            .where(SensitiveDescriptor.owner_id == user.id)
            .order_by(SensitiveDescriptor.created_at.desc())
        )
    )


@router.delete(
    "/descriptors/{descriptor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_descriptor(
    descriptor_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    descriptor = _owned_descriptor(descriptor_id, user, db)
    category = descriptor.category.value
    db.delete(descriptor)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="sensitive_descriptor.delete",
            resource_type="sensitive_descriptor",
            resource_id=descriptor_id,
            details={"category": category},
        )
    )
    db.commit()


@router.post(
    "/checks/local",
    response_model=CheckRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_local_check(
    payload: LocalCheckCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SensitiveCheck:
    descriptor = _owned_descriptor(payload.descriptor_id, user, db)
    check = SensitiveCheck(
        owner_id=user.id,
        descriptor_id=descriptor.id,
        category=descriptor.category,
        provider_id="local-validation",
        status=CheckStatus.COMPLETED,
        external_transmission=False,
        completed_at=datetime.now(UTC),
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


@router.get("/checks", response_model=list[CheckRead])
def list_checks(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SensitiveCheck]:
    return list(
        db.scalars(
            select(SensitiveCheck)
            .where(SensitiveCheck.owner_id == user.id)
            .order_by(SensitiveCheck.started_at.desc())
        )
    )


@router.get("/findings", response_model=list[FindingRead])
def list_findings(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SensitiveFinding]:
    return list(
        db.scalars(
            select(SensitiveFinding)
            .where(SensitiveFinding.owner_id == user.id)
            .order_by(SensitiveFinding.detected_at.desc())
        )
    )


@router.get("/alerts", response_model=list[AlertRead])
def list_alerts(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SensitiveAlert]:
    return list(
        db.scalars(
            select(SensitiveAlert)
            .where(SensitiveAlert.owner_id == user.id)
            .order_by(SensitiveAlert.created_at.desc())
        )
    )


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertRead,
    dependencies=[Depends(require_csrf)],
)
def acknowledge_alert(
    alert_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SensitiveAlert:
    alert = db.scalar(
        select(SensitiveAlert).where(
            SensitiveAlert.id == alert_id,
            SensitiveAlert.owner_id == user.id,
        )
    )
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerte introuvable")
    if alert.acknowledged_at is None:
        alert.acknowledged_at = datetime.now(UTC)
        db.add(
            AuditEvent(
                actor_id=user.id,
                action="sensitive_alert.acknowledge",
                resource_type="sensitive_alert",
                resource_id=alert.id,
                details={"category": alert.category.value, "risk_level": alert.risk_level.value},
            )
        )
        db.commit()
        db.refresh(alert)
    return alert


@router.post(
    "/consents",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_consent(
    payload: ConsentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    consent = SensitiveConsent(owner_id=user.id, **payload.model_dump())
    db.add(consent)
    db.commit()
    return {"id": consent.id, "status": "granted"}


@router.post(
    "/consents/{consent_id}/revoke",
    dependencies=[Depends(require_csrf)],
)
def revoke_consent(
    consent_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    consent = db.scalar(
        select(SensitiveConsent).where(
            SensitiveConsent.id == consent_id, SensitiveConsent.owner_id == user.id
        )
    )
    if consent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consentement introuvable")
    consent.revoked_at = datetime.now(UTC)
    db.commit()
    return {"id": consent.id, "status": "revoked"}
