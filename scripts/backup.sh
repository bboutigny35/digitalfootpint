#!/bin/bash
set -Eeuo pipefail
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

BACKUP_COMMAND=/opt/digitalfootprint/backend/.venv/bin/digitalfootprint-backup

if [[ $EUID -ne 0 ]]; then
  echo "La sauvegarde doit être lancée avec sudo ou comme root." >&2
  exit 1
fi
if [[ $# -ne 1 ]]; then
  echo "Usage: sudo $0 /chemin/sauvegarde.tar.gz" >&2
  exit 2
fi
if [[ ! -x "$BACKUP_COMMAND" ]]; then
  echo "DigitalFootprint n'est pas installé ou doit être mis à jour." >&2
  exit 1
fi

umask 077
"$BACKUP_COMMAND" "$1"
echo "Cette archive n'est pas chiffrée : chiffrez-la avant transfert et stockez-la sur un support distinct. Testez sa restauration."
