#!/bin/bash
set -Eeuo pipefail
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -gt 0 ]]; then
  echo "Usage: sudo $0" >&2
  exit 2
fi

if [[ $EUID -ne 0 ]]; then
  echo "La mise à jour doit être lancée avec sudo ou comme root." >&2
  exit 1
fi

if [[ ! -f /etc/digitalfootprint/digitalfootprint.env ]]; then
  echo "DigitalFootprint ne semble pas installé; lancez install-native.sh." >&2
  exit 1
fi

"$SCRIPT_ROOT/scripts/install-native.sh" --skip-packages

echo "Mise à jour terminée. La configuration existante a été conservée."
