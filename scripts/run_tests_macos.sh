#!/usr/bin/env bash
set -euo pipefail

export PYTHONUTF8=1
VENV_PY=".venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
  echo "Project virtual environment not found: $VENV_PY"
  echo "Please run scripts/setup_dev_macos.sh first."
  exit 1
fi

"$VENV_PY" -X utf8 -m pytest -q
"$VENV_PY" -X utf8 -m compileall -q astock_source_router tests examples
"$VENV_PY" -X utf8 scripts/smoke_test_offline.py
"$VENV_PY" -X utf8 scripts/doctor_env.py

if "$VENV_PY" -X utf8 -m ruff --version >/dev/null 2>&1; then
  "$VENV_PY" -X utf8 -m ruff check .
else
  echo "ruff: SKIP，原因：未安装"
fi
