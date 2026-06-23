#!/usr/bin/env bash
set -euo pipefail

export PYTHONUTF8=1
VENV_PY=".venv/bin/python"

create_venv_with() {
  local candidate="$1"
  if ! command -v "$candidate" >/dev/null 2>&1; then
    return 1
  fi
  if ! "$candidate" -X utf8 - <<'PY'
import sys

raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
  then
    return 1
  fi
  "$candidate" -X utf8 -m venv .venv
}

if [ ! -x "$VENV_PY" ]; then
  echo "Creating project virtual environment: .venv"
  if create_venv_with python3.10; then
    :
  elif create_venv_with python3; then
    :
  else
    echo "Failed to create .venv. Please install Python 3.10+ and rerun scripts/setup_dev_macos.sh."
    exit 1
  fi
fi

if ! "$VENV_PY" -X utf8 - <<'PY'
import sys

raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  echo "The project virtual environment must use Python 3.10+."
  echo "Please remove .venv, install Python 3.10+, and rerun scripts/setup_dev_macos.sh."
  exit 1
fi

"$VENV_PY" -X utf8 -m pip install --upgrade pip setuptools wheel
"$VENV_PY" -X utf8 -m pip install -e ".[dev]"

echo "Development environment is ready: $VENV_PY"
