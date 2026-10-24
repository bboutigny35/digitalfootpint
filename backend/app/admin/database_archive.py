"""Sauvegarde et restauration contrôlées de la base applicative."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from app.core.config import get_settings

FORMAT_VERSION = 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _database_kind(database_url: str) -> str:
    backend = make_url(database_url).get_backend_name()
    if backend not in {"sqlite", "postgresql"}:
        raise ValueError(f"Moteur de base non pris en charge: {backend}")
    return backend


def _sqlite_path(database_url: str) -> Path:
    database = make_url(database_url).database
    if not database or database == ":memory:":
        raise ValueError("Une base SQLite persistante est requise")
    return Path(database).resolve()


def _run_postgres(command: list[str], database_url: str) -> None:
    environment = os.environ.copy()
    for name in (
        "PGDATABASE",
        "PGHOST",
        "PGPORT",
        "PGUSER",
        "PGPASSWORD",
        "PGSSLMODE",
        "PGSERVICE",
        "PGSERVICEFILE",
    ):
        environment.pop(name, None)
    url = make_url(database_url)
    if url.database:
        environment["PGDATABASE"] = url.database
    if url.username:
        environment["PGUSER"] = url.username
    if url.password is not None:
        environment["PGPASSWORD"] = url.password
    query = url.query
    def query_value(name: str) -> str | None:
        value = query.get(name)
        return value[0] if isinstance(value, tuple) else value

    if host := query_value("host") or url.host:
        environment["PGHOST"] = host
    if port := query_value("port") or url.port:
        environment["PGPORT"] = str(port)
    if sslmode := query_value("sslmode"):
        environment["PGSSLMODE"] = sslmode
    subprocess.run(command, env=environment, check=True)  # noqa: S603


def create_archive(database_url: str, destination: Path) -> Path:
    """Crée une archive privée sans y inclure la configuration ni les secrets."""
    kind = _database_kind(database_url)
    destination = destination.resolve()
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"La sauvegarde existe déjà: {destination}")

    with tempfile.TemporaryDirectory(prefix="digitalfootprint-backup-") as temporary:
        temporary_path = Path(temporary)
        payload_name = "database.sqlite3" if kind == "sqlite" else "database.dump"
        payload = temporary_path / payload_name
        if kind == "sqlite":
            source = sqlite3.connect(_sqlite_path(database_url))
            target = sqlite3.connect(payload)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
        else:
            _run_postgres(
                ["pg_dump", "--format=custom", "--file", str(payload), "--no-owner"],
                database_url,
            )

        manifest = {
            "format_version": FORMAT_VERSION,
            "created_at": datetime.now(UTC).isoformat(),
            "database_kind": kind,
            "payload": payload_name,
            "sha256": _sha256(payload),
        }
        manifest_path = temporary_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        try:
            with destination.open("xb") as archive_stream:
                destination.chmod(0o600)
                with tarfile.open(fileobj=archive_stream, mode="w:gz") as archive:
                    archive.add(manifest_path, arcname="manifest.json")
                    archive.add(payload, arcname=payload_name)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return destination


def _read_archive(archive_path: Path, temporary_path: Path) -> tuple[dict[str, Any], Path]:
    with tarfile.open(archive_path, mode="r:gz") as archive:
        manifest_member = archive.getmember("manifest.json")
        manifest_stream = archive.extractfile(manifest_member)
        if manifest_stream is None:
            raise ValueError("Manifeste absent")
        manifest: dict[str, Any] = json.loads(manifest_stream.read())
        if manifest.get("format_version") != FORMAT_VERSION:
            raise ValueError("Version de sauvegarde non prise en charge")
        payload_name = manifest.get("payload")
        if payload_name not in {"database.sqlite3", "database.dump"}:
            raise ValueError("Nom de contenu invalide")
        payload_stream = archive.extractfile(archive.getmember(payload_name))
        if payload_stream is None:
            raise ValueError("Contenu de sauvegarde absent")
        payload_path = temporary_path / payload_name
        with payload_path.open("xb") as destination:
            while chunk := payload_stream.read(1024 * 1024):
                destination.write(chunk)
    if _sha256(payload_path) != manifest.get("sha256"):
        raise ValueError("Somme de contrôle invalide")
    return manifest, payload_path


def restore_archive(database_url: str, archive_path: Path, *, confirmed: bool) -> None:
    """Restaure une archive après confirmation explicite et contrôle d'intégrité."""
    if not confirmed:
        raise PermissionError("La restauration requiert l'option --yes")
    kind = _database_kind(database_url)
    with tempfile.TemporaryDirectory(prefix="digitalfootprint-restore-") as temporary:
        manifest, payload = _read_archive(archive_path.resolve(), Path(temporary))
        if manifest.get("database_kind") != kind:
            raise ValueError("Le moteur de l'archive ne correspond pas à la configuration")
        if kind == "sqlite":
            target_path = _sqlite_path(database_url)
            source = sqlite3.connect(payload)
            target = sqlite3.connect(target_path)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
        else:
            _run_postgres(
                [
                    "pg_restore",
                    "--dbname",
                    make_url(database_url).database or "",
                    "--clean",
                    "--if-exists",
                    "--no-owner",
                    "--exit-on-error",
                    "--single-transaction",
                    str(payload),
                ],
                database_url,
            )


def backup_main() -> None:
    parser = argparse.ArgumentParser(description="Sauvegarder DigitalFootprint")
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    result = create_archive(get_settings().database_url, arguments.destination)
    print(f"Sauvegarde créée: {result}")


def restore_main() -> None:
    parser = argparse.ArgumentParser(description="Restaurer DigitalFootprint")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--yes", action="store_true", help="confirmer l'écrasement de la base")
    arguments = parser.parse_args()
    restore_archive(get_settings().database_url, arguments.archive, confirmed=arguments.yes)
    print("Restauration terminée")
