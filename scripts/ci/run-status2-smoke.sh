#!/bin/sh
set -eu
umask 077
scratch=$(mktemp -d /tmp/status2-ci.XXXXXX)
service_pid=""
cleanup() {
    if [ -n "$service_pid" ]; then
        kill "$service_pid" 2>/dev/null || true
        wait "$service_pid" 2>/dev/null || true
    fi
    rm -rf "$scratch"
}
trap cleanup EXIT INT TERM
head -c 48 /dev/urandom | base64 > "$scratch/signing"
printf '%s' local-ci-only > "$scratch/redis"
export WEPP_AUTH_JWT_SECRETS_FILE="$scratch/signing"
export STATUS2_SIGNING_KEY_FILE="$scratch/signing"
export STATUS_REDIS_PASSWORD_FILE="$scratch/redis"
export STATUS2_REDIS_PASSWORD_FILE="$scratch/redis"
export STATUS_REDIS_URL=redis://redis:6379/2
export STATUS_ALLOWED_ORIGINS=http://127.0.0.1
export STATUS2_ORIGIN=http://127.0.0.1
export STATUS_LISTEN_ADDR=127.0.0.1:9002
status2 > "$scratch/service.log" 2>&1 &
service_pid=$!
ready=false
for attempt in $(seq 1 30); do
    if wget -q -O /dev/null http://127.0.0.1:9002/health; then
        ready=true
        break
    fi
    if ! kill -0 "$service_pid" 2>/dev/null; then break; fi
    sleep 1
done
if [ "$ready" != true ]; then
    cat "$scratch/service.log"
    exit 1
fi
status2-smoke --ws ws://127.0.0.1:9002 --redis redis://redis:6379/2 \
    --run ci-smoke --channel climate --samples 5 --payload-bytes 256 --clients 1 \
    --receive-timeout 20s --timeout 20s
