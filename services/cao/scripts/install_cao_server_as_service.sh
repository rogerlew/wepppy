#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
TARGET_ROOT=${TARGET_ROOT:-/workdir/cao}
SYSTEMD_DIR=${SYSTEMD_DIR:-/etc/systemd/system}
SERVICE_NAME=${SERVICE_NAME:-cao-server.service}

echo "[CAO installer] Source project: ${PROJECT_ROOT}"
echo "[CAO installer] Target install: ${TARGET_ROOT}"

if [[ ! -d "$TARGET_ROOT" ]]; then
  echo "[CAO installer] Creating target directory"
  mkdir -p "$TARGET_ROOT"
fi

echo "[CAO installer] Syncing project files"
rsync -a --delete \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  "${PROJECT_ROOT}/" "${TARGET_ROOT}/"

echo "[CAO installer] Resolving project version"
VERSION=$(
  python - <<'PY' "${TARGET_ROOT}/pyproject.toml"
import pathlib, sys
pyproject = pathlib.Path(sys.argv[1])
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore
data = tomllib.loads(pyproject.read_text())
print(data["project"]["version"])
PY
)
echo "${VERSION}" > "${TARGET_ROOT}/VERSION"
echo "[CAO installer] Recorded version ${VERSION} -> ${TARGET_ROOT}/VERSION"

SERVICE_SOURCE="${TARGET_ROOT}/systemd/${SERVICE_NAME}"
SERVICE_DEST="${SYSTEMD_DIR}/${SERVICE_NAME}"
echo "[CAO installer] Installing systemd unit to ${SERVICE_DEST}"
cp "${SERVICE_SOURCE}" "${SERVICE_DEST}"
systemctl daemon-reload

cat <<EOF

[CAO installer] Installation complete.
- Installed version: ${VERSION}
- Service unit: ${SERVICE_DEST}
- Project root: ${TARGET_ROOT}

Next steps:
  sudo systemctl enable --now ${SERVICE_NAME}
  systemctl status ${SERVICE_NAME}

EOF
