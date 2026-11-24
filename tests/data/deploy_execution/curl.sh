#!/bin/bash
set -euo pipefail
printf 'curl|%s\n' "$*" >> "${FAKE_COMMAND_LOG}"
if [[ "$*" == *'/utils/shape-converter/health/ready'* ]] && [ "${FAKE_SHAPE_READINESS_FAILURE:-0}" = 1 ]; then exit 22; fi
