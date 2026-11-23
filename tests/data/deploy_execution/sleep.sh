#!/bin/bash
set -euo pipefail
if [ "${1:-}" != "30" ]; then
    exit 0
fi
exec >/dev/null 2>&1
if [ "${FAKE_RQ_RESUME_FAILURE:-0}" = 1 ]; then
    exit 1
fi
if [ "${FAKE_RENEW_ONCE:-0}" = 1 ] || [ "${FAKE_HEARTBEAT_FAILURE:-0}" = 1 ]; then
    if mkdir "${FAKE_RENEW_ONCE_MARKER}" 2>/dev/null; then
        exit 0
    fi
fi
if [ "${FAKE_RQ_RENEW_AFTER_STOP:-0}" = 1 ]; then
    for _attempt in $(seq 1 500); do
        [ -f "${FAKE_WORKER_STOPPED_MARKER}" ] && exit 0
        /bin/sleep 0.01
    done
fi
deployment_parent="$(awk '{print $4}' "/proc/${PPID}/stat")"
while kill -0 "${deployment_parent}" 2>/dev/null; do
    /bin/sleep 0.02
done
