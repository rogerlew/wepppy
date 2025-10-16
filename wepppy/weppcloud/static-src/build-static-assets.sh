#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: build-static-assets.sh [--prod] [--force-install] [--skip-controllers]

Options:
  --prod            Build minified production assets (runs `npm run build`).
                    Default runs `npm run build:dev`.
  --force-install   Always run `npm install --legacy-peer-deps` before building.
  --skip-controllers  Do not rebuild controllers.js (defaults to rebuilding).
  -h, --help        Show this help message.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATIC_DIR="${PROJECT_ROOT}/static"
VENDOR_DIR="${STATIC_DIR}/vendor"
BUILD_MODE="dev"
FORCE_INSTALL=0
BUILD_CONTROLLERS=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod)
      BUILD_MODE="prod"
      shift
      ;;
    --force-install)
      FORCE_INSTALL=1
      shift
      ;;
    --skip-controllers)
      BUILD_CONTROLLERS=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

cd "${SCRIPT_DIR}"

if [[ ! -d node_modules || ${FORCE_INSTALL} -eq 1 ]]; then
  echo ">> Installing npm dependencies..."
  npm install --legacy-peer-deps
fi

if [[ "${BUILD_MODE}" == "prod" ]]; then
  echo ">> Building production assets..."
  npm run build
else
  echo ">> Building development assets..."
  npm run build:dev
fi

echo ">> Syncing built assets into ${VENDOR_DIR}"
mkdir -p "${VENDOR_DIR}"
rsync -a --delete "${SCRIPT_DIR}/dist/vendor/" "${VENDOR_DIR}/"

if [[ ${BUILD_CONTROLLERS} -eq 1 ]]; then
  echo ">> Rebuilding controllers.js bundle..."
  CONTROLLERS_SCRIPT="${PROJECT_ROOT}/controllers_js/build_controllers_js.py"
  if [[ ! -f "${CONTROLLERS_SCRIPT}" ]]; then
    echo "!! Unable to locate ${CONTROLLERS_SCRIPT}" >&2
    exit 1
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 "${CONTROLLERS_SCRIPT}"
  else
    python "${CONTROLLERS_SCRIPT}"
  fi
fi

echo ">> Done."
