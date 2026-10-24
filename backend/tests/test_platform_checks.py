from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.entities import (
    IdentityProfile,
    PlatformCatalogEntry,
    PlatformCheckResult,
    Result,
    Scan,
    User,
)
from app.services.platform_checks import finalize_platform_checks


def _platform(
    identifier: str,
    method: str,
    connector_id: str | None,
    priority: int,
) -> PlatformCatalogEntry:
    return PlatformCatalogEntry(
        identifier=identifier,
        display_name=identifier.title(),
        category="synthetic",
        verification_method=method,
        default_status="NOT_VERIFIABLE" if connector_id is None else "NO_PUBLIC_RESULT",
        connector_id=connector_id,
        priority=priority,
        limitations="Synthetic test entry",
    )


def test_platform_checks_only_claim_observed_or_inherently_unverifiable_states(
    tmp_path: Path,
) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/platform-checks.db")
    Base.metadata.create_all(engine)
    checked_at = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    with Session(engine) as db:
        user = User(
            email="platform-check@example.test",
            password_hash="synthetic-hash",  # noqa: S106
        )
        db.add(user)
        db.flush()
        profile = IdentityProfile(owner_id=user.id, first_name="Test", last_name="Platform")
        db.add(profile)
        db.flush()
        scan = Scan(
            owner_id=user.id,
            profile_id=profile.id,
            connector_ids=["github", "gitlab"],
        )
        db.add(scan)
        db.add_all(
            [
                _platform("github", "official_api", "github", 10),
                _platform("gitlab", "public_profile", "gitlab", 20),
                _platform("stackoverflow", "public_profile", None, 30),
                _platform("discord", "user_verification", None, 40),
                _platform("netflix", "none", None, 50),
            ]
        )
        db.flush()
        db.add(
            Result(
                owner_id=user.id,
                profile_id=profile.id,
                scan_id=scan.id,
                connector_id="github",
                canonical_url="https://github.com/synthetic",
                domain="github.com",
                title="Synthetic profile",
                snippet="Synthetic result",
                match_type="pseudonym",
                relevance_score=0.5,
                score_explanation={},
            )
        )
        db.commit()

        first = finalize_platform_checks(db, scan, now=checked_at)
        second = finalize_platform_checks(db, scan, now=checked_at)

        assert first.evaluated_count == 4
        assert first.public_match_count == 1
        assert first.not_verifiable_count == 2
        assert second == first
        checks = {
            check.platform_identifier: check
            for check in db.scalars(
                select(PlatformCheckResult).where(PlatformCheckResult.scan_id == scan.id)
            )
        }
        assert set(checks) == {"github", "gitlab", "discord", "netflix"}
        assert checks["github"].status == "PUBLIC_MATCH"
        assert checks["github"].result_count == 1
        assert checks["gitlab"].status == "NO_PUBLIC_RESULT"
        assert checks["discord"].status == "NOT_VERIFIABLE"
        assert checks["netflix"].status == "NOT_VERIFIABLE"
        assert all(check.owner_id == user.id for check in checks.values())
    engine.dispose()
