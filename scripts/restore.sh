#!/bin/bash
set -Eeuo pipefail
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RESTORE_COMMAND=/opt/digitalfootprint/backend/.venv/bin/digitalfootprint-restore
SERVICE=digitalfootprint-web.service
SERVICE_WAS_ACTIVE=false

if [[ $EUID -ne 0 ]]; then
  echo "La restauration doit être lancée avec sudo ou comme root." >&2
  exit 1
fi
if [[ $# -ne 2 || "$2" != "--yes" ]]; then
  echo "Usage: sudo $0 /chemin/sauvegarde.tar.gz --yes" >&2
  echo "Attention: la base configurée sera remplacée." >&2
  exit 2
fi
if [[ ! -r "$1" || ! -x "$RESTORE_COMMAND" ]]; then
  echo "Archive illisible ou installation DigitalFootprint absente." >&2
  exit 1
fi

restart_service() {
  if [[ "$SERVICE_WAS_ACTIVE" == true ]]; then
    systemctl start "$SERVICE"
  fi
}
trap restart_service EXIT

if systemctl is-active --quiet "$SERVICE"; then
  SERVICE_WAS_ACTIVE=true
  systemctl stop "$SERVICE"
fi

"$RESTORE_COMMAND" "$1" --yes
if [[ -d /var/lib/digitalfootprint ]]; then
  chown -R digitalfootprint:digitalfootprint /var/lib/digitalfootprint
fi

echo "Restauration contrôlée terminée."
