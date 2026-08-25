#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRET_DIR="${PROJECT_ROOT}/docker/secrets"
SECRET_PATH="${SECRET_DIR}/cap_secret"
CAP_UID=10001
STAGED=""
BACKUP=""
PUBLISHED=false
HAD_PREVIOUS=false

cleanup() {
    if [ -n "${STAGED}" ] && [ -f "${STAGED}" ]; then
        rm -f "${STAGED}"
    fi
    if [ -n "${BACKUP}" ] && [ -e "${BACKUP}" ]; then
        mv -T "${BACKUP}" "${SECRET_PATH}"
        echo "cap-secret-install: restored previous secret after failed validation" >&2
    elif [ "${PUBLISHED}" = true ] && [ "${HAD_PREVIOUS}" = false ]; then
        rm -f "${SECRET_PATH}"
        echo "cap-secret-install: removed failed first-install secret" >&2
    fi
}
trap cleanup EXIT

[ "$(id -u)" -ne 0 ] || {
    echo "cap-secret-install: run as the deployment account, not root" >&2
    exit 1
}
[ -d "${SECRET_DIR}" ] && [ ! -L "${SECRET_DIR}" ] || {
    echo "cap-secret-install: canonical secrets directory is invalid" >&2
    exit 1
}
[ "$(stat -c %u "${SECRET_DIR}")" = "$(id -u)" ] || {
    echo "cap-secret-install: canonical secrets directory has the wrong owner" >&2
    exit 1
}
SECRET_DIR_MODE="$(stat -c %a "${SECRET_DIR}")"
(( (8#${SECRET_DIR_MODE} & 8#022) == 0 )) || {
    echo "cap-secret-install: canonical secrets directory is group/other writable" >&2
    exit 1
}
command -v setfacl >/dev/null 2>&1 || {
    echo "cap-secret-install: setfacl is required" >&2
    exit 1
}
command -v getfacl >/dev/null 2>&1 || {
    echo "cap-secret-install: getfacl is required" >&2
    exit 1
}

HOST_CAP_ACCOUNT="$(getent passwd "${CAP_UID}" || true)"
if [ -n "${HOST_CAP_ACCOUNT}" ]; then
    HOST_CAP_NAME="${HOST_CAP_ACCOUNT%%:*}"
    HOST_CAP_SHELL="${HOST_CAP_ACCOUNT##*:}"
    case "${HOST_CAP_NAME}:${HOST_CAP_SHELL}" in
        cap:/usr/sbin/nologin|cap:/sbin/nologin|cap:/bin/false) ;;
        *) echo "cap-secret-install: host UID ${CAP_UID} belongs to an unexpected login account" >&2; exit 1 ;;
    esac
fi

COMPOSE_CONFIG="$(wctl docker compose config --format json)"
mapfile -t SECRET_CONSUMERS < <(python3 -c 'import json,sys; c=json.load(sys.stdin); print("\n".join(n for n,s in c["services"].items() if any((x if isinstance(x,str) else x.get("source")) == "cap_secret" for x in (s.get("secrets") or []))))' <<< "${COMPOSE_CONFIG}")
[ "${#SECRET_CONSUMERS[@]}" -gt 0 ] || {
    echo "cap-secret-install: effective Compose config has no cap_secret consumers" >&2
    exit 1
}
OWNER_UID="$(id -u)"
ALLOWED_UIDS=()
for service in "${SECRET_CONSUMERS[@]}"; do
    SERVICE_UID="$(wctl docker compose run --rm --no-deps --entrypoint /usr/bin/id "${service}" -u)"
    [[ "${SERVICE_UID}" =~ ^[0-9]+$ ]] || {
        echo "cap-secret-install: could not resolve numeric UID for ${service}" >&2
        exit 1
    }
    if [ "${SERVICE_UID}" != "${OWNER_UID}" ] \
        && ! printf "%s\n" "${ALLOWED_UIDS[@]:-}" | grep -qx "${SERVICE_UID}"; then
        ALLOWED_UIDS+=("${SERVICE_UID}")
    fi
done
printf "%s\n" "${ALLOWED_UIDS[@]}" | grep -qx "${CAP_UID}" || {
    echo "cap-secret-install: effective consumers do not include CAP UID ${CAP_UID}" >&2
    exit 1
}

STAGED="$(mktemp "${SECRET_DIR}/.cap_secret.XXXXXX")"
setfacl -b "${STAGED}"
chmod 0600 "${STAGED}"
dd of="${STAGED}" status=none
[ -s "${STAGED}" ] || {
    echo "cap-secret-install: refusing an empty secret" >&2
    exit 1
}
sync -f "${STAGED}"
for consumer_uid in "${ALLOWED_UIDS[@]}"; do
    setfacl -m "u:${consumer_uid}:r" "${STAGED}"
done
setfacl -m "m::r,g::-,o::-" "${STAGED}"
STAGED_ACL="$(getfacl --numeric --absolute-names --omit-header "${STAGED}")"
grep -qx "user::rw-" <<< "${STAGED_ACL}"
grep -qx "group::---" <<< "${STAGED_ACL}"
grep -qx "mask::r--" <<< "${STAGED_ACL}"
grep -qx "other::---" <<< "${STAGED_ACL}"
for consumer_uid in "${ALLOWED_UIDS[@]}"; do
    grep -Eq "^user:${consumer_uid}:r--" <<< "${STAGED_ACL}" || {
        echo "cap-secret-install: staged consumer UID ${consumer_uid} ACL is missing" >&2
        exit 1
    }
done
while IFS= read -r acl_uid; do
    printf "%s\n" "${ALLOWED_UIDS[@]}" | grep -qx "${acl_uid}" || {
        echo "cap-secret-install: staged secret contains unexpected named UID ${acl_uid}" >&2
        exit 1
    }
done < <(sed -n 's/^user:\([0-9][0-9]*\):.*/\1/p' <<< "${STAGED_ACL}")
if grep -Eq '^group:[^:]+' <<< "${STAGED_ACL}"; then
    echo "cap-secret-install: staged secret contains unexpected named group ACL" >&2
    exit 1
fi
if [ -e "${SECRET_PATH}" ] && ! cmp -s "${STAGED}" "${SECRET_PATH}"; then
    for service in "${SECRET_CONSUMERS[@]}"; do
        if [ -n "$(wctl docker compose ps -q "${service}")" ]; then
            echo "cap-secret-install: refusing value rotation while ${service} is running" >&2
            exit 1
        fi
    done
fi
if [ -e "${SECRET_PATH}" ]; then
    HAD_PREVIOUS=true
    BACKUP="${SECRET_DIR}/.cap_secret.previous.$$"
    [ ! -e "${BACKUP}" ] || {
        echo "cap-secret-install: backup path already exists" >&2
        exit 1
    }
    mv -T "${SECRET_PATH}" "${BACKUP}"
fi
mv -T "${STAGED}" "${SECRET_PATH}"
STAGED=""
PUBLISHED=true
"${PROJECT_ROOT}/docker/prepare-cap-runtime.sh" --secret-only
if [ -n "${BACKUP}" ]; then
    rm -f "${BACKUP}"
    BACKUP=""
fi
PUBLISHED=false
echo "cap-secret-install: installed canonical secret with effective consumer ACLs"
