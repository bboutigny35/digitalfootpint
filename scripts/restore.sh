#!/bin/bash
set -Eeuo pipefail
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RESTORE_COMMAND=/opt/digitalfootprint/backend/.venv/bin/digitalfootprint-restore
WRITE_SERVICES=(
  digitalfootprint-retention.timer
  digitalfootprint-retention.service
  digitalfootprint-worker.service
  digitalfootprint-web.service
)
declare -A SERVICE_WAS_ACTIVE=()

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

restart_services() {
  local service
  for service in \
    digitalfootprint-web.service \
    digitalfootprint-worker.service \
    digitalfootprint-retention.service \
    digitalfootprint-retention.timer; do
    if [[ "${SERVICE_WAS_ACTIVE[$service]:-false}" == true ]]; then
      systemctl start "$service"
    fi
  done
}
trap restart_services EXIT

for service in "${WRITE_SERVICES[@]}"; do
  if systemctl is-active --quiet "$service"; then
    SERVICE_WAS_ACTIVE["$service"]=true
    systemctl stop "$service"
  fi
done

"$RESTORE_COMMAND" "$1" --yes
if [[ -d /var/lib/digitalfootprint ]]; then
  chown -R digitalfootprint:digitalfootprint /var/lib/digitalfootprint
  chmod -R go-rwx /var/lib/digitalfootprint
fi

echo "Restauration contrôlée terminée."
