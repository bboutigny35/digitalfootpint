from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]


def test_native_installer_enforces_local_non_root_layout() -> None:
    installer = (PROJECT_ROOT / "scripts/install-native.sh").read_text()
    assert 'VERSION_ID:-}" != "13"' in installer
    assert "--shell /usr/sbin/nologin" in installer
    assert "--host 127.0.0.1" not in installer  # Le host appartient à l'unité systemd.
    assert "chmod -R o-rwx" in installer
    assert "FRONTEND_ROOT=/var/www/digitalfootprint" in installer
    assert "chown -R root:www-data" in installer
    assert "DIGITALFOOTPRINT_DATABASE_URL=sqlite:////var/lib/digitalfootprint" in installer
    assert "ufw" not in installer
    assert "iptables" not in installer


def test_native_services_are_hardened_and_local_only() -> None:
    web = (PROJECT_ROOT / "deploy/systemd/digitalfootprint-web.service").read_text()
    retention = (PROJECT_ROOT / "deploy/systemd/digitalfootprint-retention.service").read_text()
    worker = (PROJECT_ROOT / "deploy/systemd/digitalfootprint-worker.service").read_text()
    nginx = (PROJECT_ROOT / "deploy/nginx/digitalfootprint.conf").read_text()
    for unit in (web, retention, worker):
        assert "User=digitalfootprint" in unit
        assert "NoNewPrivileges=true" in unit
        assert "ProtectSystem=strict" in unit
        assert "UMask=0077" in unit
    assert "--host 127.0.0.1" in web
    assert "listen 127.0.0.1:8080;" in nginx
    assert "listen 0.0.0.0" not in nginx
    assert "digitalfootprint-scan-worker" in worker


def test_native_searxng_service_is_local_and_has_no_published_public_port() -> None:
    compose = (PROJECT_ROOT / "deploy/searxng/compose.native.yaml").read_text()
    settings = (PROJECT_ROOT / "deploy/searxng/settings.yml").read_text()
    unit = (PROJECT_ROOT / "deploy/systemd/digitalfootprint-searxng.service").read_text()
    assert '"127.0.0.1:8888:8080"' in compose
    assert "SEARXNG_SECRET" in compose
    assert "no-new-privileges:true" in compose
    assert "cap_drop:" in compose
    assert 'user: "977:977"' in compose
    assert "read_only: true" in compose
    assert "formats:" in settings and "json" in settings
    assert "/etc/digitalfootprint/searxng.env" in unit
    installer = (PROJECT_ROOT / "scripts/install-native.sh").read_text()
    assert "digitalfootprint-searxng.service" in installer


def test_native_update_reuses_idempotent_installer() -> None:
    updater = (PROJECT_ROOT / "scripts/update-native.sh").read_text()
    assert "install-native.sh\" --skip-packages" in updater
    assert "/etc/digitalfootprint/digitalfootprint.env" in updater
    assert "rm " not in updater


def test_backup_and_restore_wrappers_protect_native_data() -> None:
    backup = (PROJECT_ROOT / "scripts/backup.sh").read_text()
    restore = (PROJECT_ROOT / "scripts/restore.sh").read_text()
    assert "umask 077" in backup
    assert '"$BACKUP_COMMAND" "$1"' in backup
    assert '"$2" != "--yes"' in restore
    assert "systemctl stop" in restore
    assert "trap restart_service EXIT" in restore
    assert "DIGITALFOOTPRINT_DATABASE_URL" not in backup + restore


def test_backend_image_includes_postgres_tools_for_managed_archives() -> None:
    dockerfile = (PROJECT_ROOT / "deploy/docker/backend.Dockerfile").read_text()
    assert "apt-get install --yes --no-install-recommends postgresql-client" in dockerfile


def test_uninstaller_preserves_data_unless_purge_is_explicit() -> None:
    uninstaller = (PROJECT_ROOT / "scripts/uninstall.sh").read_text()
    purge_guard = '"${2:-}" != "--yes"'
    assert purge_guard in uninstaller
    assert 'if [[ "$PURGE_DATA" == true ]]' in uninstaller
    assert "rm -rf /var/lib/digitalfootprint" in uninstaller
    assert uninstaller.index('if [[ "$PURGE_DATA" == true ]]') < uninstaller.index(
        "rm -rf /var/lib/digitalfootprint"
    )
    assert "systemctl disable --now digitalfootprint-web.service" in uninstaller
