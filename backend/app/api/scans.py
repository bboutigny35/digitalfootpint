from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_csrf
from app.connectors.configuration import connector_is_ready, enabled_registry
from app.connectors.runtime import build_runtime_registry
from app.core.database import get_db
from app.models.entities import (
    AuditEvent,
    IdentityProfile,
    PlatformCheckResult,
    Result,
    Scan,
    ScanStatus,
    User,
    VerificationStatus,
)
from app.schemas.scans import (
    CrawlQueueStatusRead,
    PlatformCheckListRead,
    PlatformCheckRead,
    ResultPageRead,
    ResultRead,
    ResultVerificationUpdate,
    ScanComparisonItemRead,
    ScanComparisonRead,
    ScanCreate,
    ScanRead,
)
from app.services.crawl_queue import crawl_queue_counts, set_scan_crawl_paused
from app.services.scan_comparison import ComparisonCategory, compare_results

router = APIRouter(tags=["recherches"])


def _owned_scan(scan_id: str, user: User, db: Session) -> Scan:
    scan = db.scalar(select(Scan).where(Scan.id == scan_id, Scan.owner_id == user.id))
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan introuvable")
    return scan


@router.post(
    "/scans",
    response_model=ScanRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_scan(
    payload: ScanCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Scan:
    profile = db.scalar(
        select(IdentityProfile).where(
            IdentityProfile.id == payload.profile_id,
            IdentityProfile.owner_id == user.id,
        )
    )
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil introuvable")
    connectors = list(
        dict.fromkeys(value.strip() for value in payload.connector_ids if value.strip())
    )
    if not connectors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Connecteur requis")
    active_connectors = set(enabled_registry(db, build_runtime_registry()).identifiers())
    unknown_connectors = sorted(set(connectors) - active_connectors)
    if unknown_connectors:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Connecteur inconnu ou désactivé",
        )
    registry = build_runtime_registry()
    unready_connectors = [
        connector_id
        for connector_id in connectors
        if not connector_is_ready(
            db,
            connector_id,
            registry.get(connector_id).metadata.requires_api_key,
        )
    ]
    if unready_connectors:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Un connecteur sélectionné n’est pas configuré",
        )
    if set(connectors) & {"brave", "searxng"} and not payload.external_search_consent:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Confirmation requise pour la transmission à un moteur de recherche externe",
        )
    scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=connectors)
    db.add(scan)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="scan.create",
            resource_type="scan",
            resource_id=scan.id,
            details={
                "connector_count": len(connectors),
                "external_search_consent": payload.external_search_consent,
            },
        )
    )
    db.commit()
    db.refresh(scan)
    return scan


@router.get("/scans", response_model=list[ScanRead])
def list_scans(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Scan]:
    return list(
        db.scalars(select(Scan).where(Scan.owner_id == user.id).order_by(Scan.created_at.desc()))
    )


@router.get("/scans/{scan_id}", response_model=ScanRead)
def get_scan(
    scan_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Scan:
    return _owned_scan(scan_id, user, db)


@router.get("/scans/compare/results", response_model=ScanComparisonRead)
def compare_scans(
    baseline_scan_id: str,
    current_scan_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanComparisonRead:
    if baseline_scan_id == current_scan_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Deux scans distincts sont requis",
        )
    baseline_scan = _owned_scan(baseline_scan_id, user, db)
    current_scan = _owned_scan(current_scan_id, user, db)
    if baseline_scan.profile_id != current_scan.profile_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Les scans doivent concerner le même profil",
        )
    if baseline_scan.status != ScanStatus.COMPLETED or current_scan.status != ScanStatus.COMPLETED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Seuls deux scans terminés peuvent être comparés",
        )
    baseline = list(db.scalars(select(Result).where(Result.scan_id == baseline_scan.id)))
    current = list(db.scalars(select(Result).where(Result.scan_id == current_scan.id)))
    items = compare_results(baseline, current)
    counts = {category: 0 for category in ComparisonCategory}
    for item in items:
        counts[item.category] += 1
    return ScanComparisonRead(
        baseline_scan_id=baseline_scan.id,
        current_scan_id=current_scan.id,
        profile_id=baseline_scan.profile_id,
        counts=counts,
        items=[ScanComparisonItemRead.model_validate(item) for item in items],
        methodology_note=(
            "Une URL absente du scan récent est classée non revérifiée. "
            "Elle n'est jamais considérée comme supprimée ou inaccessible sans contrôle explicite."
        ),
    )


@router.post(
    "/scans/{scan_id}/cancel",
    response_model=ScanRead,
    dependencies=[Depends(require_csrf)],
)
def cancel_scan(
    scan_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Scan:
    scan = _owned_scan(scan_id, user, db)
    if scan.status not in {ScanStatus.QUEUED, ScanStatus.RUNNING}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce scan ne peut plus être annulé")
    scan.status = ScanStatus.CANCELLED
    scan.finished_at = datetime.now(UTC)
    scan.lease_owner = None
    scan.lease_expires_at = None
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="scan.cancel",
            resource_type="scan",
            resource_id=scan.id,
        )
    )
    db.commit()
    db.refresh(scan)
    return scan


@router.get("/scans/{scan_id}/crawl", response_model=CrawlQueueStatusRead)
def get_crawl_queue_status(
    scan_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CrawlQueueStatusRead:
    scan = _owned_scan(scan_id, user, db)
    return CrawlQueueStatusRead(scan_id=scan.id, counts=crawl_queue_counts(db, scan.id))


@router.get("/scans/{scan_id}/platform-checks", response_model=PlatformCheckListRead)
def get_platform_checks(
    scan_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlatformCheckListRead:
    scan = _owned_scan(scan_id, user, db)
    checks = list(
        db.scalars(
            select(PlatformCheckResult)
            .where(
                PlatformCheckResult.scan_id == scan.id,
                PlatformCheckResult.owner_id == user.id,
            )
            .order_by(
                PlatformCheckResult.platform_identifier,
                PlatformCheckResult.id,
            )
        )
    )
    return PlatformCheckListRead(
        scan_id=scan.id,
        items=[PlatformCheckRead.model_validate(item) for item in checks],
        methodology_note=(
            "NO_PUBLIC_RESULT et NOT_VERIFIABLE ne prouvent jamais l’absence d’un compte. "
            "Une entrée n’est créée que pour un connecteur exécuté ou une plateforme sans "
            "méthode publique fiable."
        ),
    )


@router.post(
    "/scans/{scan_id}/crawl/pause",
    response_model=CrawlQueueStatusRead,
    dependencies=[Depends(require_csrf)],
)
def pause_crawl_queue(
    scan_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CrawlQueueStatusRead:
    scan = _owned_scan(scan_id, user, db)
    set_scan_crawl_paused(db, scan.id, True)
    return CrawlQueueStatusRead(scan_id=scan.id, counts=crawl_queue_counts(db, scan.id))


@router.post(
    "/scans/{scan_id}/crawl/resume",
    response_model=CrawlQueueStatusRead,
    dependencies=[Depends(require_csrf)],
)
def resume_crawl_queue(
    scan_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CrawlQueueStatusRead:
    scan = _owned_scan(scan_id, user, db)
    set_scan_crawl_paused(db, scan.id, False)
    return CrawlQueueStatusRead(scan_id=scan.id, counts=crawl_queue_counts(db, scan.id))


@router.get("/results", response_model=list[ResultRead])
def list_results(
    scan_id: str | None = None,
    profile_id: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Result]:
    statement = select(Result).where(Result.owner_id == user.id)
    if scan_id:
        statement = statement.where(Result.scan_id == scan_id)
    if profile_id:
        statement = statement.where(Result.profile_id == profile_id)
    return list(
        db.scalars(statement.order_by(Result.discovered_at.desc()).offset(offset).limit(limit))
    )


@router.get("/results/search", response_model=ResultPageRead)
def search_results(
    query: str | None = Query(default=None, max_length=200),
    connector_id: str | None = Query(default=None, max_length=100),
    domain: str | None = Query(default=None, max_length=255),
    verification_status: VerificationStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: Literal["date", "title", "score", "domain"] = "date",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResultPageRead:
    filters = [Result.owner_id == user.id]
    normalized_query = query.strip() if query else ""
    if normalized_query:
        pattern = f"%{normalized_query}%"
        filters.append(
            or_(
                Result.title.ilike(pattern),
                Result.snippet.ilike(pattern),
                Result.canonical_url.ilike(pattern),
            )
        )
    if connector_id:
        filters.append(Result.connector_id == connector_id)
    if domain:
        filters.append(Result.domain == domain.strip().lower())
    if verification_status:
        filters.append(Result.verification_status == verification_status)
    if date_from:
        filters.append(Result.discovered_at >= date_from)
    if date_to:
        filters.append(Result.discovered_at <= date_to)

    total = db.scalar(select(func.count(Result.id)).where(*filters)) or 0
    sort_columns = {
        "date": Result.discovered_at,
        "title": Result.title,
        "score": Result.relevance_score,
        "domain": Result.domain,
    }
    sort_column = sort_columns[sort_by]
    ordering = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    items = list(
        db.scalars(
            select(Result)
            .where(*filters)
            .order_by(ordering, Result.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return ResultPageRead(
        items=[ResultRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.patch(
    "/results/{result_id}/verification",
    response_model=ResultRead,
    dependencies=[Depends(require_csrf)],
)
def update_verification(
    result_id: str,
    payload: ResultVerificationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Result:
    result = db.scalar(select(Result).where(Result.id == result_id, Result.owner_id == user.id))
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Résultat introuvable")
    result.verification_status = payload.verification_status
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="result.verify",
            resource_type="result",
            resource_id=result.id,
            details={"status": payload.verification_status.value},
        )
    )
    db.commit()
    db.refresh(result)
    return result
