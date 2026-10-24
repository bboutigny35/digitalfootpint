from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.connectors.configuration import connector_is_enabled, connector_is_ready
from app.connectors.runtime import build_runtime_registry
from app.core.database import get_db
from app.models.entities import Result, Scan, ScanStatus, User
from app.schemas.connectors import ConnectorRead

router = APIRouter(tags=["connecteurs"])


@router.get("/connectors", response_model=list[ConnectorRead])
def list_connectors(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ConnectorRead]:
    registry = build_runtime_registry()
    scans = list(db.scalars(select(Scan).where(Scan.owner_id == user.id)))
    response: list[ConnectorRead] = []
    for connector in registry.all():
        identifier = connector.metadata.identifier
        connector_scans = [scan for scan in scans if identifier in scan.connector_ids]
        last_scan_at = max(
            (scan.finished_at or scan.started_at or scan.created_at for scan in connector_scans),
            default=None,
        )
        result_count = db.scalar(
            select(func.count(Result.id)).where(
                Result.owner_id == user.id, Result.connector_id == identifier
            )
        )
        error_count = sum(scan.status == ScanStatus.FAILED for scan in connector_scans)
        latest_scan = max(connector_scans, key=lambda scan: scan.created_at, default=None)
        health = "not_checked"
        if latest_scan is not None and latest_scan.status == ScanStatus.FAILED:
            health = "degraded"
        elif latest_scan is not None and latest_scan.status == ScanStatus.COMPLETED:
            health = "available"
        elif latest_scan is not None and latest_scan.status == ScanStatus.RUNNING:
            health = "checking"
        response.append(
            ConnectorRead(
                identifier=connector.metadata.identifier,
                version=connector.metadata.version,
                capabilities=list(connector.metadata.capabilities),
                accepted_identifiers=list(connector.metadata.accepted_identifiers),
                requires_api_key=connector.metadata.requires_api_key,
                enabled=connector_is_enabled(db, identifier),
                ready=connector_is_ready(db, identifier, connector.metadata.requires_api_key),
                health=health,
                rate_limit_per_minute=connector.metadata.rate_limit_per_minute,
                quota_status="provider_managed",
                last_scan_at=last_scan_at,
                result_count=result_count or 0,
                error_count=error_count,
            )
        )
    return response
