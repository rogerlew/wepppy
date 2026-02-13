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

exec redis-server \
  --notify-keyspace-events "Kh" \
  --save "" \
  --appendonly "no" \
  --requirepass "$REDIS_PASSWORD"
