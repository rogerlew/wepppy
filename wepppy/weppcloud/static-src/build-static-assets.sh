#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: build-static-assets.sh [--prod] [--force-install]

Options:
  --prod            Build minified production assets (runs `npm run build`).
                    Default runs `npm run build:dev`.
  --force-install   Always run `npm install --legacy-peer-deps` before building.
  -h, --help        Show this help message.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATIC_DIR="${PROJECT_ROOT}/static"
VENDOR_DIR="${STATIC_DIR}/vendor"
BUILD_MODE="dev"
FORCE_INSTALL=0

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

echo ">> Done."
