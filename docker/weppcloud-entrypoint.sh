#!/bin/sh

# Exit immediately if a command exits with a non-zero status or if an unset
# variable is referenced. Keep the entrypoint fail-fast so container start
# aborts when the bundle build does not succeed.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
BUNDLE_SCRIPT="${PROJECT_ROOT}/wepppy/weppcloud/controllers_js/build_controllers_js.py"

DEFAULT_OUTPUT="${CONTROLLERS_JS_OUTPUT:-${PROJECT_ROOT}/wepppy/weppcloud/static/js/controllers.js}"
EXTRA_OUTPUTS="${CONTROLLERS_JS_EXTRA_OUTPUTS:-}"
STATIC_SYNC_DIR="${STATIC_ASSET_SYNC_DIR:-}"
VENDOR_SOURCE="${PROJECT_ROOT}/wepppy/weppcloud/static/vendor"

echo ">>> Building controllers.js bundle via ${BUNDLE_SCRIPT}..."
python "${BUNDLE_SCRIPT}" --output "${DEFAULT_OUTPUT}"
echo ">>> controllers.js bundle written to ${DEFAULT_OUTPUT}."

if [ -n "${EXTRA_OUTPUTS}" ]; then
  echo ">>> Replicating controllers.js bundle to extra targets..."
  for target in ${EXTRA_OUTPUTS}; do
    target_dir=$(dirname "${target}")
    mkdir -p "${target_dir}"
    cp "${DEFAULT_OUTPUT}" "${target}"
    echo "    -> ${target}"
  done
fi

if [ -n "${STATIC_SYNC_DIR}" ]; then
  if [ -d "${VENDOR_SOURCE}" ]; then
    echo ">>> Syncing static vendor assets to ${STATIC_SYNC_DIR}..."
    mkdir -p "${STATIC_SYNC_DIR}"
    rm -rf "${STATIC_SYNC_DIR}/vendor"
    cp -a "${VENDOR_SOURCE}" "${STATIC_SYNC_DIR}/"
  else
    echo ">>> Warning: vendor source directory ${VENDOR_SOURCE} not found; skipping sync."
  fi
fi

echo ">>> controllers.js bundle ready."

# Replace the shell with the primary process to preserve signal handling.
exec "$@"
