#!/bin/bash
set -Eeuo pipefail
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

PURGE_DATA=false

if [[ $EUID -ne 0 ]]; then
  echo "La désinstallation doit être lancée avec sudo ou comme root." >&2
  exit 1
fi

case "${1:-}" in
  --yes)
    if [[ $# -ne 1 ]]; then
      echo "Usage: sudo $0 --yes" >&2
      exit 2
    fi
    ;;
  --purge-data)
    if [[ "${2:-}" != "--yes" || $# -ne 2 ]]; then
      echo "Usage destructif: sudo $0 --purge-data --yes" >&2
      exit 2
    fi
    PURGE_DATA=true
    ;;
  *)
    echo "Usage: sudo $0 --yes" >&2
    echo "       sudo $0 --purge-data --yes" >&2
    echo "Sans --purge-data, la configuration et les données sont conservées." >&2
    exit 2
    ;;
esac

systemctl disable --now digitalfootprint-retention.timer >/dev/null 2>&1 || true
systemctl stop digitalfootprint-retention.service >/dev/null 2>&1 || true
systemctl disable --now digitalfootprint-searxng.service >/dev/null 2>&1 || true
systemctl disable --now digitalfootprint-web.service >/dev/null 2>&1 || true
systemctl disable --now digitalfootprint-worker.service >/dev/null 2>&1 || true

rm -f /etc/systemd/system/digitalfootprint-web.service
rm -f /etc/systemd/system/digitalfootprint-retention.service
rm -f /etc/systemd/system/digitalfootprint-retention.timer
rm -f /etc/systemd/system/digitalfootprint-worker.service
rm -f /etc/systemd/system/digitalfootprint-searxng.service
rm -f /etc/nginx/sites-enabled/digitalfootprint.conf
rm -f /etc/nginx/sites-available/digitalfootprint.conf
rm -rf /opt/digitalfootprint
rm -rf /var/www/digitalfootprint

systemctl daemon-reload
if command -v nginx >/dev/null && nginx -t >/dev/null 2>&1; then
  systemctl reload nginx.service >/dev/null 2>&1 || true
fi

if [[ "$PURGE_DATA" == true ]]; then
  if command -v docker >/dev/null && docker volume inspect digitalfootprint-search_searxng-cache >/dev/null 2>&1; then
    docker volume rm digitalfootprint-search_searxng-cache >/dev/null
  fi
  rm -rf /etc/digitalfootprint
  rm -rf /var/lib/digitalfootprint
  if id digitalfootprint >/dev/null 2>&1; then
    userdel digitalfootprint
  fi
  if getent group digitalfootprint >/dev/null; then
    groupdel digitalfootprint
  fi
  echo "Application, configuration, données et compte système supprimés."
else
  echo "Application supprimée. Configuration et données conservées:"
  echo "  /etc/digitalfootprint"
  echo "  /var/lib/digitalfootprint"
fi
