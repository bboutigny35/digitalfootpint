#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
E2E_STATE_DIR="$(mktemp -d)"
BACKEND_PID=""
WORKER_PID=""

cleanup() {
  if [[ -n "${BACKEND_PID}" ]]; then
    kill "${BACKEND_PID}" 2>/dev/null || true
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${WORKER_PID}" ]]; then
    kill "${WORKER_PID}" 2>/dev/null || true
    wait "${WORKER_PID}" 2>/dev/null || true
  fi
  rm -rf -- "${E2E_STATE_DIR}"
}
trap cleanup EXIT INT TERM

if [[ -x "${PROJECT_ROOT}/backend/.venv/bin/python" ]]; then
  PYTHON_BIN="${PROJECT_ROOT}/backend/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON:-python3}"
fi

export DIGITALFOOTPRINT_ENVIRONMENT="test"
export DIGITALFOOTPRINT_DATABASE_URL="sqlite:///${E2E_STATE_DIR}/e2e.db"
export DIGITALFOOTPRINT_SECRET_KEY="e2e-only-synthetic-secret-at-least-32-characters"
export DIGITALFOOTPRINT_ALLOWED_HOSTS="localhost,127.0.0.1"
export DIGITALFOOTPRINT_CORS_ORIGINS="http://127.0.0.1:4173"
export DIGITALFOOTPRINT_SCAN_WORKER_POLL_SECONDS="0.2"

cd "${PROJECT_ROOT}/backend"
"${PYTHON_BIN}" -m alembic upgrade head
"${PYTHON_BIN}" -m app.workers.scan_daemon &
WORKER_PID=$!
"${PYTHON_BIN}" -m uvicorn app.main:app --host 127.0.0.1 --port 18000 &
BACKEND_PID=$!
wait "${BACKEND_PID}"
