#!/bin/bash
set -Eeuo pipefail
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

APP_USER=digitalfootprint
APP_GROUP=digitalfootprint
APP_ROOT=/opt/digitalfootprint
CONFIG_ROOT=/etc/digitalfootprint
STATE_ROOT=/var/lib/digitalfootprint
FRONTEND_ROOT=/var/www/digitalfootprint
SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SKIP_PACKAGES=false

if [[ "${1:-}" == "--skip-packages" ]]; then
  SKIP_PACKAGES=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: sudo $0 [--skip-packages]" >&2
  exit 2
fi

if [[ $EUID -ne 0 ]]; then
  echo "Cette installation doit être lancée avec sudo ou comme root." >&2
  exit 1
fi

source /etc/os-release
if [[ "${ID:-}" != "debian" || "${VERSION_ID:-}" != "13" ]]; then
  echo "Debian 13 est requis (détecté: ${PRETTY_NAME:-inconnu})." >&2
  exit 1
fi

if [[ "$SKIP_PACKAGES" == false ]]; then
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates curl nginx nodejs npm postgresql-client python3 python3-pip python3-venv
fi

for command_name in curl python3 node npm nginx runuser systemctl; do
  command -v "$command_name" >/dev/null || {
    echo "Prérequis absent: $command_name" >&2
    exit 1
  }
done

if ! getent group www-data >/dev/null; then
  echo "Prérequis absent: le groupe système www-data (fourni par nginx)" >&2
  exit 1
fi

python3 -c 'import sys; assert (3, 11) <= sys.version_info < (3, 14)'
node -e 'const [major] = process.versions.node.split(".").map(Number); if (major < 20) process.exit(1)'

if ! getent group "$APP_GROUP" >/dev/null; then
  groupadd --system "$APP_GROUP"
fi
if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --gid "$APP_GROUP" --home-dir "$STATE_ROOT" \
    --shell /usr/sbin/nologin "$APP_USER"
fi

install -d -o root -g "$APP_GROUP" -m 0750 "$APP_ROOT" "$CONFIG_ROOT"
install -d -o "$APP_USER" -g "$APP_GROUP" -m 0700 "$STATE_ROOT"
install -d -o root -g "$APP_GROUP" -m 0750 \
  "$APP_ROOT/backend" "$APP_ROOT/frontend-src" "$APP_ROOT/docs" \
  "$APP_ROOT/deploy/searxng"
install -d -o root -g www-data -m 0755 "$FRONTEND_ROOT"

cp -a "$SCRIPT_ROOT/backend/app" "$APP_ROOT/backend/"
cp -a "$SCRIPT_ROOT/backend/alembic" "$APP_ROOT/backend/"
cp -a "$SCRIPT_ROOT/docs/." "$APP_ROOT/docs/"
cp -a "$SCRIPT_ROOT/deploy/searxng/." "$APP_ROOT/deploy/searxng/"
install -o root -g "$APP_GROUP" -m 0640 "$SCRIPT_ROOT/backend/alembic.ini" "$APP_ROOT/backend/alembic.ini"
install -o root -g "$APP_GROUP" -m 0640 "$SCRIPT_ROOT/backend/pyproject.toml" "$APP_ROOT/backend/pyproject.toml"

if [[ ! -x "$APP_ROOT/backend/.venv/bin/python" ]]; then
  python3 -m venv "$APP_ROOT/backend/.venv"
fi
"$APP_ROOT/backend/.venv/bin/pip" install --disable-pip-version-check "$APP_ROOT/backend"

cp -a "$SCRIPT_ROOT/frontend/src" "$APP_ROOT/frontend-src/"
for frontend_file in \
  .prettierrc.json eslint.config.js index.html package.json package-lock.json \
  tsconfig.app.json tsconfig.json tsconfig.node.json vite.config.ts; do
  install -o root -g "$APP_GROUP" -m 0640 \
    "$SCRIPT_ROOT/frontend/$frontend_file" "$APP_ROOT/frontend-src/$frontend_file"
done
pushd "$APP_ROOT/frontend-src" >/dev/null
npm ci --legacy-peer-deps --no-audit --no-fund
npm run build
popd >/dev/null
cp -a "$APP_ROOT/frontend-src/dist/." "$FRONTEND_ROOT/"

if [[ ! -f "$CONFIG_ROOT/digitalfootprint.env" ]]; then
  GENERATED_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  GENERATED_CONNECTOR_KEY="$(python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
  install -o root -g "$APP_GROUP" -m 0640 /dev/null "$CONFIG_ROOT/digitalfootprint.env"
  {
    printf 'DIGITALFOOTPRINT_ENVIRONMENT=production\n'
    printf 'DIGITALFOOTPRINT_DATABASE_URL=sqlite:////var/lib/digitalfootprint/digitalfootprint.db\n'
    printf 'DIGITALFOOTPRINT_SECRET_KEY=%s\n' "$GENERATED_SECRET"
    printf 'DIGITALFOOTPRINT_CONNECTOR_SECRET_KEYS=v1:%s\n' "$GENERATED_CONNECTOR_KEY"
    printf 'DIGITALFOOTPRINT_CONNECTOR_SECRET_ACTIVE_KEY=v1\n'
    printf 'DIGITALFOOTPRINT_ALLOWED_HOSTS=localhost,127.0.0.1\n'
    printf 'DIGITALFOOTPRINT_CORS_ORIGINS=http://127.0.0.1:8080\n'
    printf 'DIGITALFOOTPRINT_COOKIE_SECURE=false\n'
    printf 'DIGITALFOOTPRINT_SESSION_TTL_HOURS=12\n'
    printf 'DIGITALFOOTPRINT_SENSITIVE_RETENTION_INTERVAL_SECONDS=86400\n'
    printf 'DIGITALFOOTPRINT_SCAN_WORKER_POLL_SECONDS=2\n'
    printf 'DIGITALFOOTPRINT_BRAVE_CONTRACT_APPROVED=false\n'
    printf 'DIGITALFOOTPRINT_SEARXNG_URL=\n'
  } >"$CONFIG_ROOT/digitalfootprint.env"
  unset GENERATED_SECRET
  unset GENERATED_CONNECTOR_KEY
fi

chown -R root:"$APP_GROUP" "$APP_ROOT"
chmod -R o-rwx "$APP_ROOT"
# Configuration non secrète lue par l'UID 977 du conteneur SearXNG.
chmod 0644 "$APP_ROOT/deploy/searxng/settings.yml"
chown -R "$APP_USER":"$APP_GROUP" "$STATE_ROOT"
chown -R root:www-data "$FRONTEND_ROOT"
find "$FRONTEND_ROOT" -type d -exec chmod 0755 {} +
find "$FRONTEND_ROOT" -type f -exec chmod 0644 {} +

runuser -u "$APP_USER" -- /bin/sh -c \
  'cd /opt/digitalfootprint/backend && exec .venv/bin/alembic upgrade head'
chown -R "$APP_USER":"$APP_GROUP" "$STATE_ROOT"
chmod -R go-rwx "$STATE_ROOT"

install -o root -g root -m 0644 "$SCRIPT_ROOT/deploy/systemd/digitalfootprint-web.service" \
  /etc/systemd/system/digitalfootprint-web.service
install -o root -g root -m 0644 "$SCRIPT_ROOT/deploy/systemd/digitalfootprint-retention.service" \
  /etc/systemd/system/digitalfootprint-retention.service
install -o root -g root -m 0644 "$SCRIPT_ROOT/deploy/systemd/digitalfootprint-retention.timer" \
  /etc/systemd/system/digitalfootprint-retention.timer
install -o root -g root -m 0644 "$SCRIPT_ROOT/deploy/systemd/digitalfootprint-worker.service" \
  /etc/systemd/system/digitalfootprint-worker.service
install -o root -g root -m 0644 "$SCRIPT_ROOT/deploy/nginx/digitalfootprint.conf" \
  /etc/nginx/sites-available/digitalfootprint.conf
ln -sfn /etc/nginx/sites-available/digitalfootprint.conf /etc/nginx/sites-enabled/digitalfootprint.conf

nginx -t
systemctl daemon-reload
systemctl enable --now digitalfootprint-web.service digitalfootprint-worker.service \
  digitalfootprint-retention.timer nginx.service
systemctl restart digitalfootprint-web.service digitalfootprint-worker.service nginx.service

if command -v docker >/dev/null && docker compose version >/dev/null 2>&1; then
  if [[ ! -f "$CONFIG_ROOT/searxng.env" ]]; then
    SEARXNG_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    umask 077
    printf 'SEARXNG_SECRET=%s\n' "$SEARXNG_SECRET" >"$CONFIG_ROOT/searxng.env"
    chmod 0600 "$CONFIG_ROOT/searxng.env"
    unset SEARXNG_SECRET
  fi
  if ! grep -q '^DIGITALFOOTPRINT_SEARXNG_URL=' "$CONFIG_ROOT/digitalfootprint.env"; then
    printf '\nDIGITALFOOTPRINT_SEARXNG_URL=http://127.0.0.1:8888/search\n' \
      >>"$CONFIG_ROOT/digitalfootprint.env"
  elif grep -q '^DIGITALFOOTPRINT_SEARXNG_URL=$' "$CONFIG_ROOT/digitalfootprint.env"; then
    sed -i 's|^DIGITALFOOTPRINT_SEARXNG_URL=$|DIGITALFOOTPRINT_SEARXNG_URL=http://127.0.0.1:8888/search|' \
      "$CONFIG_ROOT/digitalfootprint.env"
  fi
  install -o root -g root -m 0644 \
    "$SCRIPT_ROOT/deploy/systemd/digitalfootprint-searxng.service" \
    /etc/systemd/system/digitalfootprint-searxng.service
  systemctl daemon-reload
  systemctl enable --now digitalfootprint-searxng.service
  systemctl restart digitalfootprint-web.service digitalfootprint-worker.service
else
  echo "Docker Compose absent : SearXNG reste désactivé (connecteur non prêt)."
fi

systemctl is-active --quiet digitalfootprint-web.service
systemctl is-active --quiet digitalfootprint-retention.timer
systemctl is-active --quiet digitalfootprint-worker.service
if systemctl is-enabled --quiet digitalfootprint-searxng.service 2>/dev/null; then
  systemctl is-active --quiet digitalfootprint-searxng.service
fi
curl --fail --silent --show-error --retry 10 --retry-delay 1 http://127.0.0.1:8080/health >/dev/null

echo "Installation terminée: http://127.0.0.1:8080"
