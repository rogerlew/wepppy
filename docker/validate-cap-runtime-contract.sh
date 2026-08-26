#!/bin/bash
set -euo pipefail

IMAGE="${1:-}"
if [ -z "${IMAGE}" ]; then
    echo "usage: $0 <candidate-cap-image>" >&2
    exit 2
fi
command -v docker >/dev/null 2>&1 || {
    echo "cap-runtime-contract: docker is required" >&2
    exit 2
}

SUFFIX="$$-$(date +%s)"
FRESH_VOLUME="cap-contract-fresh-${SUFFIX}"
LEGACY_VOLUME="cap-contract-legacy-${SUFFIX}"
BAD_VOLUME="cap-contract-bad-${SUFFIX}"
ZERO_VOLUME="cap-contract-zero-${SUFFIX}"
UNEXPECTED_VOLUME="cap-contract-unexpected-${SUFFIX}"
HOSTILE_VOLUME="cap-contract-hostile-${SUFFIX}"
CONTAINER="cap-contract-${SUFFIX}"
TEMP_DIR="$(mktemp -d)"

cleanup() {
    docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
    docker volume rm "${FRESH_VOLUME}" "${LEGACY_VOLUME}" "${BAD_VOLUME}" "${ZERO_VOLUME}" "${UNEXPECTED_VOLUME}" "${HOSTILE_VOLUME}" >/dev/null 2>&1 || true
    chmod 0700 "${TEMP_DIR}/unwritable" 2>/dev/null || true
    rmdir "${TEMP_DIR}/unwritable" 2>/dev/null || true
    rm -f "${TEMP_DIR}/cap_secret" "${TEMP_DIR}/cap_secret.next"
    rmdir "${TEMP_DIR}" 2>/dev/null || true
}
trap cleanup EXIT

printf '%s\n' 'contract-test-secret-not-production' > "${TEMP_DIR}/cap_secret"
chmod 0600 "${TEMP_DIR}/cap_secret"
command -v setfacl >/dev/null 2>&1 || {
    echo "cap-runtime-contract: setfacl is required" >&2
    exit 2
}
setfacl -m u:10001:r,m::r,g::-,o::- "${TEMP_DIR}/cap_secret"
[ "$(stat -c %a "${TEMP_DIR}/cap_secret")" = "640" ] || {
    echo "cap-runtime-contract: production-style secret mode is not 0640-with-ACL" >&2
    exit 1
}
docker image inspect "${IMAGE}" >/dev/null
docker volume create "${FRESH_VOLUME}" >/dev/null
docker volume create "${LEGACY_VOLUME}" >/dev/null
docker volume create "${BAD_VOLUME}" >/dev/null
docker volume create "${ZERO_VOLUME}" >/dev/null
docker volume create "${UNEXPECTED_VOLUME}" >/dev/null
docker volume create "${HOSTILE_VOLUME}" >/dev/null

write_ledger() {
    local volume="$1"
    local payload="$2"
    docker run --rm --network none --user 0:0 \
        --mount "type=volume,src=${volume},dst=/var/lib/cap" \
        --entrypoint node "${IMAGE}" -e \
        "require('node:fs').writeFileSync('/var/lib/cap/tokensList.json', '${payload}', {mode: 0o600})"
}

run_migration() {
    local volume="$1"
    docker run --rm --network none --user 0:0 \
        --mount "type=volume,src=${volume},dst=/var/lib/cap" \
        --entrypoint node "${IMAGE}" /app/migrate-data.js
}

start_and_canary() {
    local volume="$1"
    docker run -d --network none --name "${CONTAINER}" --user 10001:10001 \
        --mount "type=volume,src=${volume},dst=/var/lib/cap" \
        --mount "type=bind,src=${TEMP_DIR}/cap_secret,dst=/run/secrets/cap_secret,readonly" \
        -e CAP_SITE_KEY=contract-test \
        -e CAP_SECRET_FILE=/run/secrets/cap_secret \
        -e CAP_ASSET_ROOT=/opt/cap \
        -e CAP_CHALLENGE_COUNT=1 \
        -e CAP_CHALLENGE_DIFFICULTY=1 \
        "${IMAGE}" >/dev/null
    local attempt
    for attempt in $(seq 1 30); do
        if [ "$(docker inspect --format '{{.State.Running}}' "${CONTAINER}")" != "true" ]; then
            break
        fi
        if docker exec "${CONTAINER}" node -e \
            "fetch('http://127.0.0.1:3000/cap/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"; then
            docker exec "${CONTAINER}" node /app/canary.js
            docker rm -f "${CONTAINER}" >/dev/null
            return 0
        fi
        sleep 1
    done
    docker logs --tail 30 "${CONTAINER}" >&2
    docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
    return 1
}

expect_migration_failure() {
    local volume="$1"
    local label="$2"
    if run_migration "${volume}"; then
        echo "cap-runtime-contract: ${label} unexpectedly migrated" >&2
        exit 1
    fi
}

reset_hostile_volume() {
    docker run --rm --network none --user 0:0 \
        --mount "type=volume,src=${HOSTILE_VOLUME},dst=/var/lib/cap" \
        --entrypoint /bin/sh "${IMAGE}" -ec \
        'find /var/lib/cap -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +; chmod 0755 /var/lib/cap'
}

run_migration "${FRESH_VOLUME}"
start_and_canary "${FRESH_VOLUME}"

# Replacement inode must retain the exact runtime reader ACL.
printf '%s\n' 'contract-test-secret-rotated' > "${TEMP_DIR}/cap_secret.next"
chmod 0600 "${TEMP_DIR}/cap_secret.next"
setfacl -m u:10001:r,m::r,g::-,o::- "${TEMP_DIR}/cap_secret.next"
mv -T "${TEMP_DIR}/cap_secret.next" "${TEMP_DIR}/cap_secret"
start_and_canary "${FRESH_VOLUME}"

# Without the named runtime ACL the non-root image must fail closed.
setfacl -b "${TEMP_DIR}/cap_secret"
chmod 0600 "${TEMP_DIR}/cap_secret"
if start_and_canary "${FRESH_VOLUME}"; then
    echo "cap-runtime-contract: unreadable secret unexpectedly started" >&2
    exit 1
fi
setfacl -m u:10001:r,m::r,g::-,o::- "${TEMP_DIR}/cap_secret"

write_ledger "${LEGACY_VOLUME}" '{"sentinel":4102444800000}'
BEFORE="$(docker run --rm --network none --user 0:0 --mount "type=volume,src=${LEGACY_VOLUME},dst=/var/lib/cap,readonly" --entrypoint sha256sum "${IMAGE}" /var/lib/cap/tokensList.json | awk '{print $1}')"
if docker run --rm --network none --user 10001:10001 \
    --mount "type=volume,src=${LEGACY_VOLUME},dst=/var/lib/cap" \
    --mount "type=bind,src=${TEMP_DIR}/cap_secret,dst=/run/secrets/cap_secret,readonly" \
    -e CAP_SITE_KEY=contract-test -e CAP_SECRET_FILE=/run/secrets/cap_secret \
    -e CAP_ASSET_ROOT=/opt/cap \
    "${IMAGE}"; then
    echo "cap-runtime-contract: root-owned legacy ledger unexpectedly started" >&2
    exit 1
fi
run_migration "${LEGACY_VOLUME}"
run_migration "${LEGACY_VOLUME}"
AFTER="$(docker run --rm --network none --user 0:0 --mount "type=volume,src=${LEGACY_VOLUME},dst=/var/lib/cap,readonly" --entrypoint sha256sum "${IMAGE}" /var/lib/cap/tokensList.json | awk '{print $1}')"
[ "${BEFORE}" = "${AFTER}" ] || {
    echo "cap-runtime-contract: populated ledger changed during migration" >&2
    exit 1
}
start_and_canary "${LEGACY_VOLUME}"

write_ledger "${BAD_VOLUME}" '[]'
expect_migration_failure "${BAD_VOLUME}" "non-object ledger"
write_ledger "${ZERO_VOLUME}" ''
expect_migration_failure "${ZERO_VOLUME}" "zero-byte ledger"
docker run --rm --network none --user 0:0 --mount "type=volume,src=${UNEXPECTED_VOLUME},dst=/var/lib/cap" --entrypoint node "${IMAGE}" -e \
    "require('node:fs').writeFileSync('/var/lib/cap/unexpected', 'x')"
expect_migration_failure "${UNEXPECTED_VOLUME}" "unexpected entry"

write_ledger "${HOSTILE_VOLUME}" '{invalid-json'
expect_migration_failure "${HOSTILE_VOLUME}" "invalid JSON"
reset_hostile_volume
docker run --rm --network none --user 0:0 --mount "type=volume,src=${HOSTILE_VOLUME},dst=/var/lib/cap" --entrypoint node "${IMAGE}" -e \
    "require('node:fs').symlinkSync('/dev/null', '/var/lib/cap/tokensList.json')"
expect_migration_failure "${HOSTILE_VOLUME}" "symlink ledger"
reset_hostile_volume
docker run --rm --network none --user 0:0 --mount "type=volume,src=${HOSTILE_VOLUME},dst=/var/lib/cap" --entrypoint node "${IMAGE}" -e \
    "require('node:fs').mkdirSync('/var/lib/cap/tokensList.json')"
expect_migration_failure "${HOSTILE_VOLUME}" "directory ledger"
reset_hostile_volume
docker run --rm --network none --user 0:0 --mount "type=volume,src=${HOSTILE_VOLUME},dst=/var/lib/cap" --entrypoint /bin/sh "${IMAGE}" -ec \
    'mkfifo /var/lib/cap/tokensList.json'
expect_migration_failure "${HOSTILE_VOLUME}" "FIFO ledger"
mkdir "${TEMP_DIR}/unwritable"
chmod 0500 "${TEMP_DIR}/unwritable"
set +e
timeout 5 docker run --rm --network none --user 10001:10001 \
    --mount "type=bind,src=${TEMP_DIR}/unwritable,dst=/var/lib/cap" \
    --mount "type=bind,src=${TEMP_DIR}/cap_secret,dst=/run/secrets/cap_secret,readonly" \
    -e CAP_SITE_KEY=contract-test -e CAP_SECRET_FILE=/run/secrets/cap_secret \
    -e CAP_ASSET_ROOT=/opt/cap "${IMAGE}" >/dev/null 2>&1
UNWRITABLE_RESULT=$?
set -e
if [ "${UNWRITABLE_RESULT}" -eq 0 ] || [ "${UNWRITABLE_RESULT}" -eq 124 ]; then
    echo "cap-runtime-contract: unwritable data directory unexpectedly remained available" >&2
    exit 1
fi

echo "cap-runtime-contract: ACL, rotation, fresh, idempotent legacy, and full hostile-state matrix passed image=${IMAGE}"
