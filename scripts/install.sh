#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="${COSMOS_VENV:-.venv}"

"$PYTHON_BIN" -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip
pip install -e ".[server,media,test]"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

cosmos-media doctor

echo
echo "COSMOS Media installed."
echo "Run: source $VENV/bin/activate && cosmos-media serve"
echo "Open: http://127.0.0.1:8788/app/"
