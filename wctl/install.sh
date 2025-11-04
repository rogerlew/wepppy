#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WCTL_SCRIPT="${SCRIPT_DIR}/wctl.sh"
SYMLINK_PATH="${WCTL_SYMLINK_PATH:-/usr/local/bin/wctl}"

usage() {
  cat <<'USAGE' >&2
Usage:
  ./wctl/install.sh [dev|prod]

Configure the wctl Typer CLI to target the selected docker compose file.
USAGE
}

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to run this installer." >&2
  exit 1
fi

resolve_realpath() {
  python3 - "$1" <<'PY'
import os
import sys
print(os.path.realpath(sys.argv[1]))
PY
}

ENVIRONMENT="${1:-dev}"
case "${ENVIRONMENT}" in
  dev)
    COMPOSE_RELATIVE_PATH="docker/docker-compose.dev.yml"
    ;;
  prod)
    COMPOSE_RELATIVE_PATH="docker/docker-compose.prod.yml"
    ;;
  *)
    usage
    exit 1
    ;;
esac

cat > "${WCTL_SCRIPT}" <<'EOF_SCRIPT'
#!/bin/bash

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to run wctl." >&2
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
COMPOSE_FILE_RELATIVE="__COMPOSE_FILE_RELATIVE__"

cd "${PROJECT_DIR}"

if [[ -n "${PYTHONPATH:-}" ]]; then
  export PYTHONPATH="${PROJECT_DIR}:${PROJECT_DIR}/tools:${PYTHONPATH}"
else
  export PYTHONPATH="${PROJECT_DIR}:${PROJECT_DIR}/tools"
fi

export WCTL_COMPOSE_FILE="${COMPOSE_FILE_RELATIVE}"

python3 -m wctl2 "$@"
EOF_SCRIPT

python3 - "${WCTL_SCRIPT}" "${COMPOSE_RELATIVE_PATH}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
compose_relative = sys.argv[2]
text = path.read_text()
text = text.replace("__COMPOSE_FILE_RELATIVE__", compose_relative)
path.write_text(text)
PY

chmod +x "${WCTL_SCRIPT}"

echo "wctl configured for ${ENVIRONMENT} environment (${COMPOSE_RELATIVE_PATH})."

if [[ -n "${SYMLINK_PATH}" ]]; then
  TARGET_REALPATH="$(resolve_realpath "${WCTL_SCRIPT}")"
  if [[ -L "${SYMLINK_PATH}" ]]; then
    EXISTING_REALPATH="$(resolve_realpath "${SYMLINK_PATH}")"
    if [[ "${EXISTING_REALPATH}" == "${TARGET_REALPATH}" ]]; then
      echo "Symlink already up to date at ${SYMLINK_PATH}."
      exit 0
    fi
  fi

  if [[ -e "${SYMLINK_PATH}" && ! -L "${SYMLINK_PATH}" ]]; then
    echo "Cannot create symlink at ${SYMLINK_PATH}: path exists and is not a symlink." >&2
  else
    if ln -sfn "${WCTL_SCRIPT}" "${SYMLINK_PATH}"; then
      echo "Symlink created at ${SYMLINK_PATH} -> ${WCTL_SCRIPT}."
    else
      echo "Failed to create symlink at ${SYMLINK_PATH}. Try running with elevated permissions or set WCTL_SYMLINK_PATH." >&2
    fi
  fi
fi
