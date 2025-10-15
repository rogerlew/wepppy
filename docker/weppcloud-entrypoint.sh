#!/bin/sh

# Exit immediately if a command exits with a non-zero status or if an unset
# variable is referenced. Keep the entrypoint fail-fast so container start
# aborts when the bundle build does not succeed.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
BUNDLE_SCRIPT="${PROJECT_ROOT}/wepppy/weppcloud/controllers_js/build_controllers_js.py"

echo ">>> Building controllers.js bundle via ${BUNDLE_SCRIPT}..."
python "${BUNDLE_SCRIPT}"
echo ">>> controllers.js bundle ready."

# Replace the shell with the primary process to preserve signal handling.
exec "$@"
