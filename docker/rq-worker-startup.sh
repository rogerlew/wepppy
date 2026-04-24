#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <worker_count> <queue_name> [rq_args...]" >&2
  exit 64
fi

worker_count="$1"
queue_name="$2"
shift 2

wait_timeout="${RQ_REDIS_WAIT_TIMEOUT_SECONDS:-300}"
wait_interval="${RQ_REDIS_WAIT_INTERVAL_SECONDS:-1}"
startup_delay="${RQ_WORKER_STARTUP_DELAY_SECONDS:-5}"
probe_connect_timeout="${RQ_REDIS_PROBE_CONNECT_TIMEOUT_SECONDS:-5}"
probe_socket_timeout="${RQ_REDIS_PROBE_SOCKET_TIMEOUT_SECONDS:-5}"

redis_url="$(
  python - <<'PY'
import os
import sys
from urllib.parse import urlparse

from wepppy.config.redis_settings import RedisDB, redis_url

raw_url = os.getenv("REDIS_URL") or os.getenv("RQ_REDIS_URL") or ""
parsed = urlparse(raw_url)
if not parsed.scheme or not parsed.hostname:
    print(
        "Invalid worker Redis URL; set RQ_REDIS_URL to redis://<host>:<port>/<db>.",
        file=sys.stderr,
    )
    raise SystemExit(64)

print(redis_url(RedisDB.RQ))
PY
)"

python - "$redis_url" "$wait_timeout" "$wait_interval" "$probe_connect_timeout" "$probe_socket_timeout" <<'PY'
import sys
import time

import redis

redis_url_value = sys.argv[1]
timeout_seconds = float(sys.argv[2])
poll_interval_seconds = max(0.1, float(sys.argv[3]))
connect_timeout_seconds = max(0.1, float(sys.argv[4]))
socket_timeout_seconds = max(0.1, float(sys.argv[5]))
deadline = time.monotonic() + timeout_seconds
attempt = 0
last_error: Exception | None = None

while time.monotonic() < deadline:
    attempt += 1
    try:
        redis.Redis.from_url(
            redis_url_value,
            socket_connect_timeout=connect_timeout_seconds,
            socket_timeout=socket_timeout_seconds,
        ).ping()
        print(f"Redis ready for RQ after {attempt} attempt(s).")
        break
    except (redis.exceptions.RedisError, OSError, ValueError) as exc:
        last_error = exc
        print(
            f"Waiting for Redis readiness (attempt {attempt}): {exc}",
            file=sys.stderr,
        )
        time.sleep(poll_interval_seconds)
else:
    print(
        "Timed out waiting for Redis readiness "
        f"after {timeout_seconds:.1f}s: {last_error}",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY

python - "$startup_delay" <<'PY'
import sys
import time

delay_seconds = float(sys.argv[1])
if delay_seconds > 0:
    print(f"Applying additional worker startup delay: {delay_seconds:.1f}s")
    time.sleep(delay_seconds)
PY

exec /opt/venv/bin/rq worker-pool \
  -n "$worker_count" \
  -u "$redis_url" \
  --logging-level INFO \
  --worker-class wepppy.rq.WepppyRqWorker \
  "$queue_name" \
  "$@"
