import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.admin.database_archive import create_archive
from app.api.dependencies import require_admin, require_csrf
from app.connectors.production import build_production_registry
from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import (
    AuditEvent,
    ConnectorConfiguration,
    ConnectorSecret,
    Scan,
    ScanSchedule,
    ScanStatus,
    User,
)
from app.schemas.admin import (
    AdminOverviewRead,
    AuditEventPageRead,
    AuditEventRead,
    ConnectorConfigurationRead,
    ConnectorConfigurationUpdate,
    ConnectorSecretRead,
    ConnectorSecretRotationRead,
    ConnectorSecretWrite,
)
from app.security.connector_secrets import ConnectorSecretVault, SecretVaultError

router = APIRouter(prefix="/admin", tags=["administration"])
_backup_lock = Lock()
_SAFE_AUDIT_DETAIL_KEYS = {
    "connector_count",
    "fields",
    "format",
    "is_admin",
    "kind",
    "key_version",
    "notify_new_mentions",
    "result_count",
    "status",
}


def _vault() -> ConnectorSecretVault:
    try:
        vault = ConnectorSecretVault()
    except SecretVaultError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    if not vault.configured:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Coffre de secrets non configuré")
    return vault


def _known_connector(connector_id: str) -> None:
    if connector_id not in build_production_registry().identifiers():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connecteur inconnu")


def _finish_backup(temporary_directory: Path) -> None:
    try:
        shutil.rmtree(temporary_directory)
    finally:
        _backup_lock.release()


@router.get("/overview", response_model=AdminOverviewRead)
def admin_overview(
    _admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> AdminOverviewRead:
    settings = get_settings()
    database_backend = "postgresql" if settings.database_url.startswith("postgresql") else "sqlite"
    return AdminOverviewRead(
        application_version="0.1.0-dev",
        environment=settings.environment,
        database_backend=database_backend,
        cookie_secure=settings.cookie_secure,
        github_token_configured=bool(
            settings.github_api_token or db.get(ConnectorSecret, "github")
        ),
        backup_command_available=True,
    )


@router.get("/audit-events", response_model=AuditEventPageRead)
def list_audit_events(
    action: str | None = Query(default=None, max_length=100),
    resource_type: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AuditEventPageRead:
    filters = []
    if action:
        filters.append(AuditEvent.action == action)
    if resource_type:
        filters.append(AuditEvent.resource_type == resource_type)
    total = db.scalar(select(func.count(AuditEvent.id)).where(*filters)) or 0
    stored_events = list(
        db.scalars(
            select(AuditEvent)
            .where(*filters)
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    events = [
        AuditEventRead.model_validate(event).model_copy(
            update={
                "details": {
                    key: value
                    for key, value in event.details.items()
                    if key in _SAFE_AUDIT_DETAIL_KEYS
                }
            }
        )
        for event in stored_events
    ]
    return AuditEventPageRead(
        items=events,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/connector-secrets", response_model=list[ConnectorSecretRead])
def list_connector_secrets(
    _admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[ConnectorSecretRead]:
    stored = {item.connector_id: item for item in db.scalars(select(ConnectorSecret))}
    return [
        ConnectorSecretRead(
            connector_id=connector_id,
            configured=connector_id in stored,
            key_version=stored[connector_id].key_version if connector_id in stored else None,
            updated_at=stored[connector_id].updated_at if connector_id in stored else None,
        )
        for connector_id in build_production_registry().identifiers()
    ]


@router.put(
    "/connector-secrets/{connector_id}",
    response_model=ConnectorSecretRead,
    dependencies=[Depends(require_csrf)],
)
def set_connector_secret(
    connector_id: str,
    payload: ConnectorSecretWrite,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ConnectorSecretRead:
    _known_connector(connector_id)
    encrypted = _vault().encrypt(connector_id, payload.value.get_secret_value())
    stored = db.get(ConnectorSecret, connector_id)
    if stored is None:
        stored = ConnectorSecret(connector_id=connector_id)
        db.add(stored)
    stored.ciphertext = encrypted.ciphertext
    stored.key_version = encrypted.key_version
    db.add(
        AuditEvent(
            actor_id=admin.id,
            action="connector_secret.set",
            resource_type="connector",
            resource_id=None,
            details={"key_version": encrypted.key_version},
        )
    )
    db.commit()
    db.refresh(stored)
    return ConnectorSecretRead(
        connector_id=stored.connector_id,
        configured=True,
        key_version=stored.key_version,
        updated_at=stored.updated_at,
    )


@router.delete(
    "/connector-secrets/{connector_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_connector_secret(
    connector_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    _known_connector(connector_id)
    stored = db.get(ConnectorSecret, connector_id)
    if stored is not None:
        db.delete(stored)
    db.add(
        AuditEvent(
            actor_id=admin.id,
            action="connector_secret.delete",
            resource_type="connector",
            resource_id=None,
            details={},
        )
    )
    db.commit()


@router.post(
    "/connector-secrets/rotate",
    response_model=ConnectorSecretRotationRead,
    dependencies=[Depends(require_csrf)],
)
def rotate_connector_secrets(
    admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> ConnectorSecretRotationRead:
    vault = _vault()
    assert vault.active_version is not None
    rotated = 0
    try:
        for stored in db.scalars(select(ConnectorSecret)):
            if stored.key_version == vault.active_version:
                continue
            plaintext = vault.decrypt(stored.connector_id, stored.ciphertext, stored.key_version)
            encrypted = vault.encrypt(stored.connector_id, plaintext)
            stored.ciphertext = encrypted.ciphertext
            stored.key_version = encrypted.key_version
            rotated += 1
    except SecretVaultError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.add(
        AuditEvent(
            actor_id=admin.id,
            action="connector_secret.rotate",
            resource_type="connector_secret",
            resource_id=None,
            details={"key_version": vault.active_version},
        )
    )
    db.commit()
    return ConnectorSecretRotationRead(rotated=rotated, active_key_version=vault.active_version)


@router.patch(
    "/connectors/{connector_id}",
    response_model=ConnectorConfigurationRead,
    dependencies=[Depends(require_csrf)],
)
def configure_connector(
    connector_id: str,
    payload: ConnectorConfigurationUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ConnectorConfigurationRead:
    _known_connector(connector_id)
    configuration = db.get(ConnectorConfiguration, connector_id)
    if configuration is None:
        configuration = ConnectorConfiguration(connector_id=connector_id)
        db.add(configuration)
    configuration.enabled = payload.enabled
    if not payload.enabled:
        for schedule in db.scalars(select(ScanSchedule).where(ScanSchedule.enabled.is_(True))):
            if connector_id in schedule.connector_ids:
                schedule.enabled = False
        now = datetime.now(UTC)
        for scan in db.scalars(
            select(Scan).where(Scan.status.in_([ScanStatus.QUEUED, ScanStatus.RUNNING]))
        ):
            if connector_id in scan.connector_ids:
                scan.status = ScanStatus.CANCELLED
                scan.error_code = "connector_disabled"
                scan.finished_at = now
                scan.lease_owner = None
                scan.lease_expires_at = None
    db.add(
        AuditEvent(
            actor_id=admin.id,
            action="connector.configure",
            resource_type="connector",
            resource_id=None,
            details={"status": "enabled" if payload.enabled else "disabled"},
        )
    )
    db.commit()
    db.refresh(configuration)
    return ConnectorConfigurationRead.model_validate(configuration, from_attributes=True)


@router.post(
    "/backups/download",
    response_class=FileResponse,
    dependencies=[Depends(require_csrf)],
)
def download_backup(
    admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> FileResponse:
    if not _backup_lock.acquire(blocking=False):
        raise HTTPException(status.HTTP_409_CONFLICT, "Une sauvegarde est déjà en cours")
    temporary_directory = Path(tempfile.mkdtemp(prefix="digitalfootprint-admin-backup-"))
    try:
        archive = create_archive(
            get_settings().database_url,
            temporary_directory / "digitalfootprint-backup.tar.gz",
        )
        db.add(
            AuditEvent(
                actor_id=admin.id,
                action="backup.download",
                resource_type="database",
                resource_id=None,
                details={"kind": "database"},
            )
        )
        db.commit()
        filename = f"digitalfootprint-backup-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.tar.gz"
        return FileResponse(
            archive,
            media_type="application/gzip",
            filename=filename,
            headers={"Cache-Control": "no-store"},
            background=BackgroundTask(_finish_backup, temporary_directory),
        )
    except Exception as exc:
        shutil.rmtree(temporary_directory, ignore_errors=True)
        _backup_lock.release()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Création de la sauvegarde impossible"
        ) from exc
