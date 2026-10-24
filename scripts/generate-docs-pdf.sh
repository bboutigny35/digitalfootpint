#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PROJECT_ROOT}/backend/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Environnement backend absent : ${PYTHON_BIN}" >&2
  exit 1
fi

exec "${PYTHON_BIN}" -m app.reporting.docs_pdf \
  --docs-root "${PROJECT_ROOT}/docs" \
  --output-dir "${PROJECT_ROOT}/reports/documentation"
