#!/bin/sh
set +x
set -eu
redis_script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$redis_script_dir/redis-password.sh"
# This assignment belongs only to the ephemeral CLI child, never its parent.
REDISCLI_AUTH="$REDIS_PASSWORD_VALUE" exec redis-cli "$@"
