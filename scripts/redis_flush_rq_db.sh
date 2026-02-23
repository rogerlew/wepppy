#!/usr/bin/env bash
#
# Flush Redis DB 9 (WEPPpy RQ only).
#
# This script is intentionally non-destructive beyond DB 9:
# - Never calls FLUSHALL.
# - Validates the DB index and fails closed if it isn't 9.
#
set -euo pipefail

log() {
  local level="$1"
  shift
  printf '[redis_flush_rq_db] %s: %s\n' "${level}" "$*" >&2
}

usage() {
  cat >&2 <<'EOF'
Usage: scripts/redis_flush_rq_db.sh [--dry-run] [--require-redis]

Flushes ONLY Redis DB 9 (RQ). Never FLUSHALL.

Flags:
  --dry-run        Print what would happen; do not flush.
  --require-redis  Fail if Redis is unreachable (default is best-effort skip).

Env overrides:
  REDIS_HOST            Redis host (default: parsed from RQ_REDIS_URL/REDIS_URL or 127.0.0.1)
  REDIS_PORT            Redis port (default: parsed from RQ_REDIS_URL/REDIS_URL or 6379)
  REDIS_PASSWORD_FILE   Secret file path (default: /run/secrets/redis_password)
  REDIS_PASSWORD        Password (discouraged; prefer REDIS_PASSWORD_FILE)
  REDIS_DB              Must be 9 if provided (default: 9)
  REDIS_TIMEOUT_SECONDS Per-command timeout seconds (default: 2)
  RQ_REDIS_URL          Optional URL used to infer host/port (db is ignored; flush is always DB 9)
  REDIS_URL             Optional URL used to infer host/port (db is ignored; flush is always DB 9)
EOF
}

DRY_RUN=false
REQUIRE_REDIS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --require-redis)
      REQUIRE_REDIS=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log "ERROR" "Unknown option: $1"
      usage
      exit 2
      ;;
  esac
done

REDIS_DB="${REDIS_DB:-9}"
if [[ "${REDIS_DB}" != "9" ]]; then
  log "ERROR" "Refusing to flush: REDIS_DB must be 9 (got '${REDIS_DB}')."
  exit 2
fi

if ! command -v redis-cli >/dev/null 2>&1; then
  if [[ "${REQUIRE_REDIS}" = true ]]; then
    log "ERROR" "redis-cli not found; refusing to proceed (--require-redis)."
    exit 1
  fi
  log "WARN" "redis-cli not found; skipping Redis DB 9 flush."
  exit 0
fi

REDIS_PASSWORD_FILE="${REDIS_PASSWORD_FILE:-/run/secrets/redis_password}"
REDIS_TIMEOUT_SECONDS="${REDIS_TIMEOUT_SECONDS:-2}"

infer_host_port_from_url() {
  local url="$1"
  # Expected: redis://host:port/db or redis://host/db or rediss://...
  # We intentionally ignore credentials and db in the URL.
  local without_scheme="${url#*://}"
  local authority="${without_scheme%%/*}"
  local host="${authority}"
  local port=""
  if [[ "${authority}" == *"@"* ]]; then
    authority="${authority##*@}"
  fi
  host="${authority}"
  if [[ "${authority}" == *":"* ]]; then
    host="${authority%%:*}"
    port="${authority##*:}"
  fi
  if [[ -n "${host}" ]]; then
    REDIS_HOST="${REDIS_HOST:-${host}}"
  fi
  if [[ -n "${port}" ]]; then
    REDIS_PORT="${REDIS_PORT:-${port}}"
  fi
}

if [[ -z "${REDIS_HOST:-}" || -z "${REDIS_PORT:-}" ]]; then
  if [[ -n "${RQ_REDIS_URL:-}" ]]; then
    infer_host_port_from_url "${RQ_REDIS_URL}"
  elif [[ -n "${REDIS_URL:-}" ]]; then
    infer_host_port_from_url "${REDIS_URL}"
  fi
fi

REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"

if [[ -n "${REDIS_PASSWORD:-}" ]]; then
  export REDISCLI_AUTH="${REDIS_PASSWORD}"
elif [[ -f "${REDIS_PASSWORD_FILE}" ]]; then
  REDISCLI_AUTH="$(cat "${REDIS_PASSWORD_FILE}")"
  if [[ -z "${REDISCLI_AUTH}" ]]; then
    log "ERROR" "Redis password file is empty: ${REDIS_PASSWORD_FILE}"
    exit 1
  fi
  export REDISCLI_AUTH
else
  log "WARN" "Redis password file not found: ${REDIS_PASSWORD_FILE} (continuing without auth)"
fi

redis_cmd_base=(
  redis-cli
  -e
  -h "${REDIS_HOST}"
  -p "${REDIS_PORT}"
  -n 9
)

run_redis_cli() {
  if command -v timeout >/dev/null 2>&1; then
    timeout "${REDIS_TIMEOUT_SECONDS}" "${redis_cmd_base[@]}" "$@"
  else
    "${redis_cmd_base[@]}" "$@"
  fi
}

is_unreachable_error() {
  grep -qiE 'Could not connect|Connection refused|No route to host|Name or service not known|Temporary failure in name resolution|Connection timed out'
}

REDIS_PING_ATTEMPTS="${REDIS_PING_ATTEMPTS:-}"
if [[ -z "${REDIS_PING_ATTEMPTS}" ]]; then
  if [[ "${REQUIRE_REDIS}" = true ]]; then
    REDIS_PING_ATTEMPTS=10
  else
    REDIS_PING_ATTEMPTS=1
  fi
fi
REDIS_PING_DELAY_SECONDS="${REDIS_PING_DELAY_SECONDS:-1}"

attempt=1
while true; do
  ping_out="$(run_redis_cli PING 2>&1)" || ping_rc=$?
  ping_rc="${ping_rc:-0}"

  if [[ "${ping_rc}" = "0" && "${ping_out}" = "PONG" ]]; then
    break
  fi

  if echo "${ping_out}" | is_unreachable_error; then
    if [[ "${REQUIRE_REDIS}" = true && "${attempt}" -lt "${REDIS_PING_ATTEMPTS}" ]]; then
      log "INFO" "Redis not reachable at ${REDIS_HOST}:${REDIS_PORT} yet; retrying (${attempt}/${REDIS_PING_ATTEMPTS})..."
      attempt=$((attempt + 1))
      sleep "${REDIS_PING_DELAY_SECONDS}"
      unset ping_rc
      continue
    fi

    if [[ "${REQUIRE_REDIS}" = true ]]; then
      log "ERROR" "Redis unreachable at ${REDIS_HOST}:${REDIS_PORT}; refusing to proceed (--require-redis)."
      exit 1
    fi

    log "WARN" "Redis unreachable at ${REDIS_HOST}:${REDIS_PORT}; skipping Redis DB 9 flush."
    exit 0
  fi

  log "ERROR" "Redis PING failed for ${REDIS_HOST}:${REDIS_PORT} (db 9): ${ping_out}"
  exit 1
done

dbsize_before="$(run_redis_cli DBSIZE 2>&1)" || true
log "INFO" "Connected to Redis at ${REDIS_HOST}:${REDIS_PORT}; DB 9 size before flush: ${dbsize_before}"

if [[ "${DRY_RUN}" = true ]]; then
  log "INFO" "Dry-run: would run 'FLUSHDB' on DB 9 only."
  exit 0
fi

flush_out="$(run_redis_cli FLUSHDB 2>&1)" || flush_rc=$?
flush_rc="${flush_rc:-0}"
if [[ "${flush_rc}" != "0" || "${flush_out}" != "OK" ]]; then
  log "ERROR" "FLUSHDB failed on DB 9: ${flush_out}"
  exit 1
fi

dbsize_after="$(run_redis_cli DBSIZE 2>&1)" || true
log "INFO" "Flushed Redis DB 9 successfully; DB 9 size after flush: ${dbsize_after}"
