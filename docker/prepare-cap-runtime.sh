#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRET_PATH="${PROJECT_ROOT}/docker/secrets/cap_secret"
CAP_UID=10001
MODE="${1:---all}"

case "${MODE}" in
    --all|--secret-only|--data-only) ;;
    *)
        echo "usage: $0 [--all|--secret-only|--data-only]" >&2
        exit 2
        ;;
esac

fail() {
    echo "cap-runtime-preflight: $*" >&2
    exit 1
}

[ "$(id -u)" -ne 0 ] || fail "run as the deployment account, not root"
if [ "${MODE}" != "--data-only" ]; then
    [ -d "${PROJECT_ROOT}/docker/secrets" ] || fail "canonical secrets directory is absent"
    [ ! -L "${PROJECT_ROOT}/docker/secrets" ] || fail "canonical secrets directory must not be a symlink"
    [ -f "${SECRET_PATH}" ] && [ ! -L "${SECRET_PATH}" ] \
        || fail "cap_secret must be a non-symlink regular file"
    SECRET_DIR_MODE="$(stat -c %a "${PROJECT_ROOT}/docker/secrets")"
    (( (8#${SECRET_DIR_MODE} & 8#022) == 0 )) \
        || fail "canonical secrets directory must not be group/other writable"
    [ "$(stat -c %u "${SECRET_PATH}")" = "$(id -u)" ] \
        || fail "cap_secret must be owned by the deployment account"
    command -v setfacl >/dev/null 2>&1 || fail "setfacl is required"
    command -v getfacl >/dev/null 2>&1 || fail "getfacl is required"

    HOST_CAP_ACCOUNT="$(getent passwd "${CAP_UID}" || true)"
    if [ -n "${HOST_CAP_ACCOUNT}" ]; then
        HOST_CAP_NAME="${HOST_CAP_ACCOUNT%%:*}"
        HOST_CAP_SHELL="${HOST_CAP_ACCOUNT##*:}"
        case "${HOST_CAP_NAME}:${HOST_CAP_SHELL}" in
            cap:/usr/sbin/nologin|cap:/sbin/nologin|cap:/bin/false) ;;
            *) fail "host UID ${CAP_UID} belongs to an unexpected login account" ;;
        esac
    fi

    COMPOSE_CONFIG="$(wctl docker compose config --format json)"
    INLINE_SECRET="$(python3 -c 'import json,sys; c=json.load(sys.stdin); e=c["services"]["cap"].get("environment") or {}; print("yes" if e.get("CAP_SECRET") else "no")' <<< "${COMPOSE_CONFIG}")"
    [ "${INLINE_SECRET}" = "no" ] || fail "inline CAP_SECRET conflicts with CAP_SECRET_FILE"
    mapfile -t SECRET_CONSUMERS < <(python3 -c 'import json,sys; c=json.load(sys.stdin); print("\n".join(n for n,s in c["services"].items() if any((x if isinstance(x,str) else x.get("source")) == "cap_secret" for x in (s.get("secrets") or []))))' <<< "${COMPOSE_CONFIG}")
    [ "${#SECRET_CONSUMERS[@]}" -gt 0 ] || fail "effective Compose config has no cap_secret consumers"

    OWNER_UID="$(id -u)"
    ALLOWED_UIDS=()
    for service in "${SECRET_CONSUMERS[@]}"; do
        SERVICE_UID="$(wctl docker compose run --rm --no-deps --entrypoint /usr/bin/id "${service}" -u)"
        [[ "${SERVICE_UID}" =~ ^[0-9]+$ ]] || fail "could not resolve numeric UID for ${service}"
        if [ "${SERVICE_UID}" != "${OWNER_UID}" ] \
            && ! printf "%s\n" "${ALLOWED_UIDS[@]:-}" | grep -qx "${SERVICE_UID}"; then
            ALLOWED_UIDS+=("${SERVICE_UID}")
        fi
    done
    printf "%s\n" "${ALLOWED_UIDS[@]}" | grep -qx "${CAP_UID}" \
        || fail "effective cap_secret consumers do not include CAP UID ${CAP_UID}"

    # Validation is deliberately read-only. Repairs are staged and atomically
    # published by install-cap-secret.sh so a partial ACL update cannot break
    # a running service that rereads the mounted secret.
    ACL="$(getfacl --numeric --absolute-names --omit-header "${SECRET_PATH}")"
    grep -qx "user::rw-" <<< "${ACL}" || fail "cap_secret owner ACL is not rw-"
    grep -Eq "^user:${CAP_UID}:r--" <<< "${ACL}" || fail "cap_secret CAP ACL is not r--"
    for consumer_uid in "${ALLOWED_UIDS[@]}"; do
        grep -Eq "^user:${consumer_uid}:r--" <<< "${ACL}" \
            || fail "cap_secret consumer UID ${consumer_uid} ACL is not r--"
    done
    grep -qx "group::---" <<< "${ACL}" || fail "cap_secret group ACL is not ---"
    grep -qx "mask::r--" <<< "${ACL}" || fail "cap_secret ACL mask is not r--"
    grep -qx "other::---" <<< "${ACL}" || fail "cap_secret other ACL is not ---"
    while IFS= read -r acl_uid; do
        printf "%s\n" "${ALLOWED_UIDS[@]}" | grep -qx "${acl_uid}" \
            || fail "cap_secret contains unexpected named UID ${acl_uid}"
    done < <(sed -n 's/^user:\([0-9][0-9]*\):.*/\1/p' <<< "${ACL}")
    if grep -Eq '^group:[^:]+' <<< "${ACL}"; then
        fail "cap_secret contains unexpected named group ACL entries"
    fi
    echo "cap-runtime-preflight: secret-ready uid=${CAP_UID}"
fi

if [ "${MODE}" = "--secret-only" ]; then
    exit 0
fi

CAP_CONTAINER="$(wctl docker compose ps --all -q cap)"
CREATED_CONTAINER=false
if [ -z "${CAP_CONTAINER}" ]; then
    wctl docker compose create --no-build cap >/dev/null
    CAP_CONTAINER="$(wctl docker compose ps -q --all cap)"
    CREATED_CONTAINER=true
fi
[ -n "${CAP_CONTAINER}" ] || fail "unable to resolve CAP container"

CAP_VOLUME="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/cap"}}{{.Name}}{{end}}{{end}}' "${CAP_CONTAINER}")"
CAP_IMAGE="$(wctl docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["cap"]["image"])')"
[ -n "${CAP_VOLUME}" ] || fail "unable to resolve the exact CAP named volume"
[ -n "${CAP_IMAGE}" ] || fail "unable to resolve the candidate CAP image"

if [ "${CREATED_CONTAINER}" = true ]; then
    wctl docker compose rm -f cap >/dev/null
fi

docker run --rm --network none --read-only --security-opt no-new-privileges \
    --cap-drop ALL --cap-add CHOWN --cap-add FOWNER --cap-add DAC_OVERRIDE \
    --pids-limit 64 --memory 128m --user 0:0 \
    --mount "type=volume,src=${CAP_VOLUME},dst=/var/lib/cap" \
    --entrypoint node "${CAP_IMAGE}" /app/migrate-data.js

docker run --rm --network none --read-only --security-opt no-new-privileges \
    --cap-drop ALL --pids-limit 64 --memory 128m --user "${CAP_UID}:${CAP_UID}" \
    --mount "type=volume,src=${CAP_VOLUME},dst=/var/lib/cap" \
    --entrypoint node "${CAP_IMAGE}" -e \
    'const fs=require("node:fs"); const p="/var/lib/cap/.deploy-probe"; const f=fs.openSync(p,"wx",0o600); fs.fsyncSync(f); fs.closeSync(f); fs.unlinkSync(p); const l="/var/lib/cap/tokensList.json"; if(fs.existsSync(l)) fs.accessSync(l,fs.constants.R_OK|fs.constants.W_OK);'

echo "cap-runtime-preflight: data-ready volume=${CAP_VOLUME} uid=${CAP_UID}"
