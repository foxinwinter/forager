#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${FORAGER_VENV:-/nyaa/coding/envs/forager-venv}"

if [[ ! -x "$VENV/bin/python" ]]; then
    echo "error: no venv found at $VENV (set FORAGER_VENV)" >&2
    exit 1
fi

if [[ ! -d "$ROOT/src/forager" ]]; then
    echo "error: forager package not found under $ROOT/src" >&2
    exit 1
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$VENV/bin/python" -m forager "$@"
