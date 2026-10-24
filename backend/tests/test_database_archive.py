import os
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text

from app.admin.database_archive import _run_postgres, create_archive, restore_archive


def test_sqlite_backup_restore_and_private_permissions(tmp_path: Path) -> None:
    database = tmp_path / "source.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample VALUES ('avant')")
        connection.commit()
    database_url = f"sqlite:///{database}"
    archive = create_archive(database_url, tmp_path / "backup.tar.gz")
    assert archive.stat().st_mode & 0o777 == 0o600

    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE sample SET value = 'après'")
        connection.commit()
    restore_archive(database_url, archive, confirmed=True)
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone() == ("avant",)


def test_restore_requires_explicit_confirmation(tmp_path: Path) -> None:
    with pytest.raises(PermissionError, match="--yes"):
        restore_archive("sqlite:///unused.db", tmp_path / "absent.tar.gz", confirmed=False)


def test_backup_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    database = tmp_path / "source.db"
    sqlite3.connect(database).close()
    destination = tmp_path / "backup.tar.gz"
    destination.touch()
    with pytest.raises(FileExistsError):
        create_archive(f"sqlite:///{database}", destination)


def test_postgres_tools_receive_parsed_connection_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subprocess_run = Mock()
    monkeypatch.setattr("app.admin.database_archive.subprocess.run", subprocess_run)
    monkeypatch.setenv("PGSERVICE", "untrusted-inherited-service")
    database_url = (
        "postgresql+psycopg://archive-user:synthetic%40password@/archive-db"
        "?host=%2Ftmp%2Fpg-socket&port=55433&sslmode=disable"
    )

    _run_postgres(["pg_dump", "--format=custom"], database_url)

    command = subprocess_run.call_args.args[0]
    environment = subprocess_run.call_args.kwargs["env"]
    assert command == ["pg_dump", "--format=custom"]
    assert environment["PGDATABASE"] == "archive-db"
    assert environment["PGUSER"] == "archive-user"
    assert environment["PGPASSWORD"] == "synthetic@password"
    assert environment["PGHOST"] == "/tmp/pg-socket"  # noqa: S108 - synthetic URL fixture
    assert environment["PGPORT"] == "55433"
    assert environment["PGSSLMODE"] == "disable"
    assert "PGSERVICE" not in environment
    assert "synthetic" not in " ".join(command)


@pytest.mark.skipif(
    not os.getenv("DIGITALFOOTPRINT_TEST_POSTGRES_BACKUP_URL"),
    reason="requires the opt-in isolated PostgreSQL backup test database",
)
def test_postgres_backup_restore_roundtrip(tmp_path: Path) -> None:
    database_url = os.environ["DIGITALFOOTPRINT_TEST_POSTGRES_BACKUP_URL"]
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS digitalfootprint_backup_probe "
                    "(value TEXT NOT NULL)"
                )
            )
            connection.execute(text("TRUNCATE digitalfootprint_backup_probe"))
            connection.execute(
                text("INSERT INTO digitalfootprint_backup_probe VALUES ('synthetic-before')")
            )

        archive = create_archive(database_url, tmp_path / "postgres-backup.tar.gz")
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE digitalfootprint_backup_probe SET value='synthetic-after'")
            )

        restore_archive(database_url, archive, confirmed=True)
        with engine.begin() as connection:
            restored: str = connection.execute(
                text("SELECT value FROM digitalfootprint_backup_probe")
            ).scalar_one()
            connection.execute(text("DROP TABLE digitalfootprint_backup_probe"))
        assert restored == "synthetic-before"
    finally:
        engine.dispose()
