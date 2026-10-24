from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.entities import IdentityProfile, Result, User, VerificationStatus
from app.schemas.dashboard import DashboardPoint, DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["tableau de bord"])


@router.get("", response_model=DashboardSummary)
def get_dashboard(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DashboardSummary:
    now = datetime.now(UTC)
    start_date = now.date() - timedelta(days=29)
    start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
    owner_filter = Result.owner_id == user.id
    total_mentions = db.scalar(select(func.count(Result.id)).where(owner_filter)) or 0
    total_domains = (
        db.scalar(select(func.count(func.distinct(Result.domain))).where(owner_filter)) or 0
    )
    total_profiles = (
        db.scalar(
            select(func.count(IdentityProfile.id)).where(IdentityProfile.owner_id == user.id)
        )
        or 0
    )
    new_mentions_7d = (
        db.scalar(
            select(func.count(Result.id)).where(
                owner_filter,
                Result.discovered_at >= now - timedelta(days=7),
            )
        )
        or 0
    )
    needs_verification = (
        db.scalar(
            select(func.count(Result.id)).where(
                owner_filter,
                Result.verification_status == VerificationStatus.UNCERTAIN,
            )
        )
        or 0
    )
    discovered_dates = db.scalars(
        select(Result.discovered_at).where(
            owner_filter,
            Result.discovered_at >= start_datetime,
        )
    )
    counts: dict[date, int] = {}
    for discovered_at in discovered_dates:
        day = discovered_at.date()
        counts[day] = counts.get(day, 0) + 1
    evolution = []
    for offset in range(30):
        day = start_date + timedelta(days=offset)
        evolution.append(DashboardPoint(date=day, mentions=counts.get(day, 0)))
    return DashboardSummary(
        total_mentions=total_mentions,
        total_domains=total_domains,
        total_profiles=total_profiles,
        new_mentions_7d=new_mentions_7d,
        needs_verification=needs_verification,
        evolution=evolution,
    )
