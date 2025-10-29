#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

COMPOSE="docker compose --env-file docker/.env -f docker/docker-compose.dev.yml"

WS_URL=${STATUS2_SMOKE_WS_URL:-ws://status:9002}
REDIS_URL=${STATUS2_SMOKE_REDIS_URL:-redis://redis:6379/2}
RUN_ID=${STATUS2_SMOKE_RUN_ID:-smoke-test}
CHANNEL=${STATUS2_SMOKE_CHANNEL:-climate}
SAMPLES=${STATUS2_SMOKE_SAMPLES:-5}
PAYLOAD_BYTES=${STATUS2_SMOKE_PAYLOAD_BYTES:-256}
CLIENTS=${STATUS2_SMOKE_CLIENTS:-1}
RECEIVE_TIMEOUT=${STATUS2_SMOKE_RECEIVE_TIMEOUT:-10s}
OVERALL_TIMEOUT=${STATUS2_SMOKE_TIMEOUT:-10s}

status_was_running=0
redis_was_running=0

if ${COMPOSE} ps -q status >/dev/null 2>&1; then
  if [ -n "$(${COMPOSE} ps -q status)" ]; then
    status_was_running=1
  fi
fi

if ${COMPOSE} ps -q redis >/dev/null 2>&1; then
  if [ -n "$(${COMPOSE} ps -q redis)" ]; then
    redis_was_running=1
  fi
fi

cleanup() {
  ${COMPOSE} rm -fs status-build >/dev/null 2>&1 || true
  if [ "${status_was_running}" -eq 0 ]; then
    ${COMPOSE} stop status >/dev/null 2>&1 || true
  fi
  if [ "${redis_was_running}" -eq 0 ]; then
    ${COMPOSE} stop redis >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

${COMPOSE} up -d redis status >/dev/null

${COMPOSE} run --rm status-build sh -lc "
  cd /workspace/tests/tools/status2_smoke && \
  PATH=/usr/local/go/bin:\$PATH go run . \
    --ws '${WS_URL}' \
    --redis '${REDIS_URL}' \
    --run '${RUN_ID}' \
    --channel '${CHANNEL}' \
    --samples ${SAMPLES} \
    --payload-bytes ${PAYLOAD_BYTES} \
    --clients ${CLIENTS} \
    --receive-timeout ${RECEIVE_TIMEOUT} \
    --timeout ${OVERALL_TIMEOUT}
"
