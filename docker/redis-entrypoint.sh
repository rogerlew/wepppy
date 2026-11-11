#!/bin/sh

set -eu

. /usr/local/bin/redis-password.sh

# Restrict only credential artifacts; keep the original data-file umask.
redis_original_umask=$(umask)
umask 077
redis_acl_dir=$(mktemp -d /tmp/wepp-redis-acl.XXXXXX)
redis_acl_tmp="$redis_acl_dir/users.acl.tmp"
redis_password_hash=$(printf '%s' "$REDIS_PASSWORD_VALUE" | sha256sum)
redis_password_hash=${redis_password_hash%% *}
printf 'user default on #%s ~* &* +@all\n' "$redis_password_hash" > "$redis_acl_tmp"
chmod 600 "$redis_acl_tmp"
mv "$redis_acl_tmp" "$redis_acl_dir/users.acl"
unset REDIS_PASSWORD_VALUE redis_password_hash
umask "$redis_original_umask"

REDIS_APPENDONLY="${REDIS_APPENDONLY:-yes}"
REDIS_APPENDFSYNC="${REDIS_APPENDFSYNC:-everysec}"
REDIS_SAVE_SCHEDULE="${REDIS_SAVE_SCHEDULE-900 1 300 10 60 10000}"
REDIS_AOF_USE_RDB_PREAMBLE="${REDIS_AOF_USE_RDB_PREAMBLE:-yes}"
REDIS_DIR="${REDIS_DIR:-/data}"

mkdir -p "${REDIS_DIR}"

set -- \
  redis-server \
  --notify-keyspace-events "Kh" \
  --dir "${REDIS_DIR}" \
  --appendonly "${REDIS_APPENDONLY}" \
  --appendfsync "${REDIS_APPENDFSYNC}" \
  --aof-use-rdb-preamble "${REDIS_AOF_USE_RDB_PREAMBLE}" \
  --aclfile "$redis_acl_dir/users.acl"

# Allow an explicit empty value to disable RDB snapshots.
if [ -n "${REDIS_SAVE_SCHEDULE}" ]; then
  set -- "$@" --save "${REDIS_SAVE_SCHEDULE}"
else
  set -- "$@" --save ""
fi

exec "$@"
