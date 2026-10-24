import asyncio

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import User
from app.security.passwords import hash_password
from app.sensitive_monitor.connectors import (
    LocalMatchCandidate,
    SensitiveProvider,
    SensitiveProviderMetadata,
)
from app.sensitive_monitor.models import SensitiveAlert, SensitiveDescriptor
from app.sensitive_monitor.service import SensitiveMonitorService
from app.sensitive_monitor.types import CheckStatus, SensitiveCategory


class TestProvider(SensitiveProvider):
    __test__ = False
    metadata = SensitiveProviderMetadata(
        identifier="authorized-test-source",
        version="1",
        categories=(SensitiveCategory.PHONE,),
        external_transmission=False,
    )

    def __init__(self, *, match: bool = False, fail: bool = False) -> None:
        self.match = match
        self.fail = fail

    async def check_local(self, candidate: LocalMatchCandidate) -> bool:
        if self.fail:
            raise RuntimeError("synthetic provider secret")
        return self.match


def _database() -> tuple[Session, SensitiveDescriptor]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine, expire_on_commit=False)
    user = User(email="sensitive@example.com", password_hash=hash_password("unused-password"))
    db.add(user)
    db.flush()
    descriptor = SensitiveDescriptor(
        owner_id=user.id,
        category=SensitiveCategory.PHONE,
        masked_label="••••••5678",
        fingerprint="a" * 64,
    )
    db.add(descriptor)
    db.commit()
    return db, descriptor


def test_confirmed_local_match_creates_masked_alert() -> None:
    db, descriptor = _database()
    check = asyncio.run(
        SensitiveMonitorService().run_local_provider(descriptor, TestProvider(match=True), db)
    )
    alert = db.scalar(select(SensitiveAlert))
    assert check.status == CheckStatus.COMPLETED
    assert alert is not None
    assert "5678" not in alert.recommendation
    assert alert.source_label == "authorized-test-source"
    db.close()


def test_provider_error_is_reduced_to_safe_code() -> None:
    db, descriptor = _database()
    check = asyncio.run(
        SensitiveMonitorService().run_local_provider(descriptor, TestProvider(fail=True), db)
    )
    assert check.status == CheckStatus.FAILED
    assert check.error_code == "provider_failure"
    assert "secret" not in check.error_code
    db.close()
