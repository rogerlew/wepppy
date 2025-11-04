#!/bin/bash

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to run wctl2." >&2
  exit 1
fi

resolve_realpath() {
  python3 - "$1" <<'PY'
import os
import sys
print(os.path.realpath(sys.argv[1]))
PY
}

SCRIPT_PATH="$(resolve_realpath "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

export WCTL_COMPOSE_FILE="docker/docker-compose.dev.yml"
export PYTHONPATH="${PROJECT_DIR}/tools"

python3 -m wctl2 "$@"
