#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

: "${STATUS2_SMOKE_ENV_FILE:=docker/.env}"
# Authenticated smoke needs the same configured secret files as the service.
# Never create fallback signing keys or an alternate anonymous service.
test -f "${STATUS2_SMOKE_ENV_FILE}" || { echo "Configured smoke env file required" >&2; exit 1; }

COMPOSE=(docker compose --env-file "${STATUS2_SMOKE_ENV_FILE}" -f docker/docker-compose.dev.yml)

WS_URL=${STATUS2_SMOKE_WS_URL:-ws://status:9002}
REDIS_URL=${STATUS2_SMOKE_REDIS_URL:-redis://redis:6379/2}
RUN_ID=${STATUS2_SMOKE_RUN_ID:-smoke-test}
CHANNEL=${STATUS2_SMOKE_CHANNEL:-climate}
SAMPLES=${STATUS2_SMOKE_SAMPLES:-5}
PAYLOAD_BYTES=${STATUS2_SMOKE_PAYLOAD_BYTES:-256}
CLIENTS=${STATUS2_SMOKE_CLIENTS:-1}
RECEIVE_TIMEOUT=${STATUS2_SMOKE_RECEIVE_TIMEOUT:-20s}
OVERALL_TIMEOUT=${STATUS2_SMOKE_TIMEOUT:-20s}
STATUS2_SMOKE_LOG=${STATUS2_SMOKE_LOG:-telemetry/status2-smoke.log}
mkdir -p "$(dirname "${STATUS2_SMOKE_LOG}")"
: > "${STATUS2_SMOKE_LOG}"

status_was_running=0
redis_was_running=0

if "${COMPOSE[@]}" ps -q status >/dev/null 2>&1; then
  if [ -n "$("${COMPOSE[@]}" ps -q status)" ]; then
    status_was_running=1
  fi
fi

if "${COMPOSE[@]}" ps -q redis >/dev/null 2>&1; then
  if [ -n "$("${COMPOSE[@]}" ps -q redis)" ]; then
    redis_was_running=1
  fi
fi

cleanup() {
  "${COMPOSE[@]}" rm -fs status-build >/dev/null 2>&1 || true
  if [ "${status_was_running}" -eq 0 ]; then
    "${COMPOSE[@]}" stop status >/dev/null 2>&1 || true
  fi
  if [ "${redis_was_running}" -eq 0 ]; then
    "${COMPOSE[@]}" stop redis >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

"${COMPOSE[@]}" up -d redis status >/dev/null

# Render only non-secret paths and Origin; mount secrets only into this trusted invocation.
mapfile -t fixture_config < <("${COMPOSE[@]}" config --format json | python3 -c '
import json,sys
c=json.load(sys.stdin)
print(c["secrets"]["wepp_auth_jwt_secrets"]["file"])
print(c["secrets"]["redis_password"]["file"])
print(c["services"]["status"]["environment"]["STATUS_ALLOWED_ORIGINS"].split(",")[0])
')
[ "${#fixture_config[@]}" -eq 3 ] || { echo "Smoke authorization configuration unavailable" >&2; exit 1; }
"${COMPOSE[@]}" run --rm \
  -v "${fixture_config[0]}:/run/secrets/smoke_signing:ro" \
  -v "${fixture_config[1]}:/run/secrets/smoke_redis:ro" \
  -e STATUS2_SIGNING_KEY_FILE=/run/secrets/smoke_signing \
  -e STATUS2_REDIS_PASSWORD_FILE=/run/secrets/smoke_redis \
  -e "STATUS2_ORIGIN=${fixture_config[2]}" \
  status-build sh -lc 'cd /workspace/tests/tools/status2_smoke && PATH=/usr/local/go/bin:$PATH exec go run . "$@"' smoke \
  --ws "${WS_URL}" --redis "${REDIS_URL}" --run "${RUN_ID}" --channel "${CHANNEL}" \
  --samples "${SAMPLES}" --payload-bytes "${PAYLOAD_BYTES}" --clients "${CLIENTS}" \
  --receive-timeout "${RECEIVE_TIMEOUT}" --timeout "${OVERALL_TIMEOUT}" | tee "${STATUS2_SMOKE_LOG}"
