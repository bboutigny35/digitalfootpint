#!/bin/sh
set -eu

if [ "${DIGITALFOOTPRINT_RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi

exec "$@"
