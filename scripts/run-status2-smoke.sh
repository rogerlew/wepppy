#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

: "${STATUS2_SMOKE_ENV_FILE:=docker/.env}"
cleanup_env_file=0
if [ ! -f "${STATUS2_SMOKE_ENV_FILE}" ]; then
  STATUS2_SMOKE_ENV_FILE="/tmp/status2-smoke.env"
  cleanup_env_file=1

  WC1_DIR_VALUE=${WC1_DIR:-${STATUS2_SMOKE_WC1_DIR:-/tmp/status2-smoke-wc1}}
  GEODATA_DIR_VALUE=${GEODATA_DIR:-${STATUS2_SMOKE_GEODATA_DIR:-/tmp/status2-smoke-geodata}}
  DATABASE_URL_VALUE=${DATABASE_URL:-${STATUS2_SMOKE_DATABASE_URL:-postgresql://postgres:postgres@postgres:5432/postgres}}
  WEPP_AUTH_JWT_SECRET_VALUE=${WEPP_AUTH_JWT_SECRET:-${STATUS2_SMOKE_WEPP_AUTH_JWT_SECRET:-dev-secret}}
  AGENT_JWT_SECRET_VALUE=${AGENT_JWT_SECRET_KEY:-${STATUS2_SMOKE_AGENT_JWT_SECRET:-dev-agent-secret}}
  OPENTOPO_API_KEY_VALUE=${OPENTOPOGRAPHY_API_KEY:-${STATUS2_SMOKE_OPENTOPO_API_KEY:-dummy}}
  CADDY_FILE_VALUE=${CADDY_FILE:-${STATUS2_SMOKE_CADDY_FILE:-${ROOT_DIR}/docker/caddy/Caddyfile}}

  mkdir -p "${WC1_DIR_VALUE}" "${GEODATA_DIR_VALUE}"

  cat <<EOF_ENV > "${STATUS2_SMOKE_ENV_FILE}"
UID=$(id -u)
GID=$(id -g)
WC1_DIR=${WC1_DIR_VALUE}
GEODATA_DIR=${GEODATA_DIR_VALUE}
CADDY_FILE=${CADDY_FILE_VALUE}
DATABASE_URL=${DATABASE_URL_VALUE}
WEPP_AUTH_JWT_SECRET=${WEPP_AUTH_JWT_SECRET_VALUE}
AGENT_JWT_SECRET_KEY=${AGENT_JWT_SECRET_VALUE}
OPENTOPOGRAPHY_API_KEY=${OPENTOPO_API_KEY_VALUE}
EOF_ENV
fi

COMPOSE=(docker compose --env-file "${STATUS2_SMOKE_ENV_FILE}" -f docker/docker-compose.dev.yml)

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
  if [ "${cleanup_env_file}" -eq 1 ]; then
    rm -f "${STATUS2_SMOKE_ENV_FILE}"
  fi
}
trap cleanup EXIT

"${COMPOSE[@]}" up -d redis status >/dev/null

"${COMPOSE[@]}" run --rm status-build sh -lc "cd /workspace/tests/tools/status2_smoke && PATH=/usr/local/go/bin:\$PATH go run . --ws '${WS_URL}' --redis '${REDIS_URL}' --run '${RUN_ID}' --channel '${CHANNEL}' --samples ${SAMPLES} --payload-bytes ${PAYLOAD_BYTES} --clients ${CLIENTS} --receive-timeout ${RECEIVE_TIMEOUT} --timeout ${OVERALL_TIMEOUT}"
