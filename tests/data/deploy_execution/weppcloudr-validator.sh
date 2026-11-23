#!/bin/bash
set -euo pipefail
printf 'weppcloudr-validator|%s\n' "$*" >> "${FAKE_COMMAND_LOG}"
if [ "${FAKE_STALE_RENDERER:-0}" = 1 ]; then exit 74; fi
