#!/bin/bash
set -euo pipefail
if [ "${1:-}" = "status" ] && [[ "$*" == *"wepppy/microservices/shape_converter"* ]]; then
    if [ "${FAKE_SHAPE_GIT_STATUS_FAILURE:-0}" = 1 ]; then
        exit 83
    fi
    if [ "${FAKE_SHAPE_BUILD_INPUTS_CLEAN:-1}" = 1 ]; then
        exit 0
    fi
    printf ' M %s\n' "${FAKE_SHAPE_DIRTY_BUILD_INPUT}"
    exit 0
fi
exec /usr/bin/git "$@"
