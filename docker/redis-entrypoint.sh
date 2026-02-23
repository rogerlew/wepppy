#!/bin/sh

set -eu

SECRET_FILE="${REDIS_PASSWORD_FILE:-/run/secrets/redis_password}"

if [ ! -f "$SECRET_FILE" ]; then
  echo "[redis-entrypoint] Missing redis password file at $SECRET_FILE" >&2
  exit 1
fi

# Command substitution strips trailing newlines; do not echo the password.
REDIS_PASSWORD="$(cat "$SECRET_FILE")"
if [ -z "${REDIS_PASSWORD}" ]; then
  echo "[redis-entrypoint] Redis password file is empty at $SECRET_FILE" >&2
  exit 1
fi

REDIS_APPENDONLY="${REDIS_APPENDONLY:-yes}"
REDIS_APPENDFSYNC="${REDIS_APPENDFSYNC:-everysec}"
REDIS_SAVE_SCHEDULE="${REDIS_SAVE_SCHEDULE:-900 1 300 10 60 10000}"
REDIS_AOF_USE_RDB_PREAMBLE="${REDIS_AOF_USE_RDB_PREAMBLE:-yes}"

set -- \
  redis-server \
  --notify-keyspace-events "Kh" \
  --appendonly "${REDIS_APPENDONLY}" \
  --appendfsync "${REDIS_APPENDFSYNC}" \
  --aof-use-rdb-preamble "${REDIS_AOF_USE_RDB_PREAMBLE}" \
  --requirepass "${REDIS_PASSWORD}"

# Allow an explicit empty value to disable RDB snapshots.
if [ -n "${REDIS_SAVE_SCHEDULE}" ]; then
  set -- "$@" --save "${REDIS_SAVE_SCHEDULE}"
else
  set -- "$@" --save ""
fi

exec "$@"
