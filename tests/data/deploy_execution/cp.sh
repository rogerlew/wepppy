#!/bin/bash
set -euo pipefail
if [ "${FAKE_CONTROLLER_BACKUP_FAILURE:-0}" = 1 ] \
    && [[ "$*" == *"controllers-gl.js"* ]]; then
    exit 77
fi
exec /bin/cp "$@"
