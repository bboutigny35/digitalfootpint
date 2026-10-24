from datetime import UTC, datetime
from enum import StrEnum

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.entities import (
    AuditEvent,
    IdentityProfile,
    ReportExport,
    Result,
    Scan,
    ScanStatus,
    User,
)
from app.reporting.exports import (
    ReportData,
    ReportEntry,
    ReportKind,
    render_csv,
    render_html,
    render_json,
    render_pdf,
    render_xlsx,
)
from app.schemas.reports import ReportExportRead

router = APIRouter(prefix="/reports", tags=["rapports"])


class ExportFormat(StrEnum):
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    HTML = "html"
    PDF = "pdf"


MEDIA_TYPES = {
    ExportFormat.CSV: "text/csv; charset=utf-8",
    ExportFormat.JSON: "application/json",
    ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.HTML: "text/html; charset=utf-8",
    ExportFormat.PDF: "application/pdf",
}


@router.get("", response_model=list[ReportExportRead])
def list_report_exports(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ReportExport]:
    return list(
        db.scalars(
            select(ReportExport)
            .where(ReportExport.owner_id == user.id)
            .order_by(ReportExport.created_at.desc())
            .limit(100)
        )
    )


@router.get("/export")
def export_report(
    export_format: ExportFormat = Query(alias="format"),
    kind: ReportKind = "detailed",
    profile_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    profile_statement = select(IdentityProfile).where(IdentityProfile.owner_id == user.id)
    if profile_id:
        profile_statement = profile_statement.where(IdentityProfile.id == profile_id)
    profiles = list(db.scalars(profile_statement))
    if profile_id and not profiles:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil introuvable")
    profile_names = {
        profile.id: f"{profile.first_name} {profile.last_name}" for profile in profiles
    }

    result_statement = select(Result).where(Result.owner_id == user.id)
    scan_statement = select(Scan).where(Scan.owner_id == user.id)
    if profile_id:
        result_statement = result_statement.where(Result.profile_id == profile_id)
        scan_statement = scan_statement.where(Scan.profile_id == profile_id)
    results = list(db.scalars(result_statement.order_by(Result.discovered_at.desc())))
    scans = list(db.scalars(scan_statement))
    sources = sorted({connector for scan in scans for connector in scan.connector_ids})
    unavailable = sorted(
        {
            connector
            for scan in scans
            if scan.status == ScanStatus.FAILED
            for connector in scan.connector_ids
        }
    )
    report = ReportData(
        generated_at=datetime.now(UTC),
        scope=(next(iter(profile_names.values())) if profile_id else "Tous les profils autorisés"),
        sources_queried=tuple(sources),
        sources_unavailable=tuple(unavailable),
        entries=tuple(
            ReportEntry(
                profile=profile_names.get(item.profile_id, "Profil supprimé"),
                connector=item.connector_id,
                url=item.canonical_url,
                title=item.title,
                snippet=item.snippet,
                confidence=item.relevance_score,
                verification_status=item.verification_status.value,
                discovered_at=item.discovered_at.isoformat(),
                last_checked_at=item.last_checked_at.isoformat(),
                published_at=item.published_at.isoformat() if item.published_at else None,
            )
            for item in results
        ),
    )
    renderers = {
        ExportFormat.CSV: render_csv,
        ExportFormat.JSON: render_json,
        ExportFormat.XLSX: render_xlsx,
        ExportFormat.HTML: render_html,
        ExportFormat.PDF: render_pdf,
    }
    content = renderers[export_format](report, kind)
    db.add(
        ReportExport(
            owner_id=user.id,
            profile_id=profile_id,
            export_format=export_format.value,
            report_kind=kind,
            result_count=len(results),
        )
    )
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="report.export",
            resource_type="report",
            details={"format": export_format.value, "kind": kind, "result_count": len(results)},
        )
    )
    db.commit()
    filename = f"digitalfootprint-{kind}.{export_format.value}"
    return Response(
        content=content,
        media_type=MEDIA_TYPES[export_format],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )
