#!/bin/bash
set -euo pipefail
printf 'wctl|%s\n' "$*" >> "${FAKE_COMMAND_LOG}"
args="$*"
if [[ "${args}" == *"exec -T rq-worker"* ]] \
    && [ "${FAKE_STOPPED_WORKER_AFTER_STOP:-0}" = 1 ] \
    && [ -f "${FAKE_WORKER_STOPPED_MARKER}" ]; then
    echo 'service "rq-worker" is not running' >&2
    exit 1
fi
if [[ "${args}" == *"config --services"* ]]; then
    printf '%s\n' "${FAKE_SERVICES}"
elif [[ "${args}" == *"show-compose-files"* ]]; then
    if [ "${FAKE_PRESET_QUERY_FAILURE:-0}" = 1 ]; then
        exit 84
    fi
    printf '%s\n' "${FAKE_COMPOSE_FILES}"
elif [[ "${args}" == *"config --format json"* ]]; then
    if [ "${FAKE_COMPOSE_RENDER_FAILURE:-0}" = 1 ]; then
        exit 85
    fi
    printf '%s\n' "${FAKE_CONFIG}"
elif [[ "${args}" == *"docker compose config"* ]]; then
    printf '%s\n' "${FAKE_CONFIG}"
elif [[ "${args}" == *"ps --status running --services"* ]]; then
    printf '%s\n' "${FAKE_SERVICES}"
elif [[ "${args}" == *"ps --all --format json"* ]]; then
    count=0
    [ ! -f "${FAKE_RECOVERY_HEALTH_COUNT}" ] \
        || count="$(cat "${FAKE_RECOVERY_HEALTH_COUNT}")"
    if [ -f "${FAKE_RECOVERY_STARTED_MARKER}" ] \
        && [ "${count}" -lt "${FAKE_RECOVERY_HEALTH_DELAY_CHECKS}" ]; then
        count=$((count + 1))
        printf '%s\n' "${count}" > "${FAKE_RECOVERY_HEALTH_COUNT}"
        printf '%s\n' "${FAKE_PS_STARTING}"
    else
        printf '%s\n' "${FAKE_PS}"
    fi
elif [[ "${args}" == *" ps "* && "${args}" == *" -q "* ]] \
    || [[ "${args}" == *" ps -q "* ]]; then
    service="${!#}"
    if [ -n "${FAKE_NEW_SERVICE}" ] && [ "${service}" = "${FAKE_NEW_SERVICE}" ]; then
        if [ "${FAKE_NEW_INVENTORY_FAILURE}" = 1 ]; then exit 82; fi
        if [ -f "${FAKE_NEW_MARKER}" ]; then printf 'cid-%s\n' "${service}"; fi
        if [[ "$*" == *" --all "* ]] && [ "${FAKE_STOPPED_NEW_SERVICE}" = 1 ]; then
            printf 'cid-stopped-%s\n' "${service}"
        fi
        exit 0
    fi
    if [ "${service}" = "shape-converter" ] && [ "${FAKE_SHAPE_PS_FAILURE:-0}" = 1 ]; then
        exit 82
    fi
    if [ "${service}" != "shape-converter" ] || [ ! -f "${FAKE_SHAPE_STOPPED_MARKER}" ]; then
        printf 'cid-%s\n' "${service}"
    fi
elif [[ "${args}" == *"StartedJobRegistry"* ]]; then
    if [[ "${args}" == *"exec -T rq-worker"* ]]; then
        echo 'rq-probe|exec' >> "${FAKE_COMMAND_LOG}"
        if [ "${FAKE_RQ_PROBE_WORKER_STOPPED}" = 1 ]; then
            echo 'service "rq-worker" is not running' >&2
            exit 1
        fi
    else
        echo 'rq-probe|run' >> "${FAKE_COMMAND_LOG}"
    fi
    if [ "${FAKE_RQ_PROBE_RESULT}" = error ]; then
        echo 'Redis connection unavailable' >&2
        exit 1
    fi
    printf '%s\n' "${FAKE_RQ_PROBE_RESULT}"
elif [[ "${args}" == *"# rq-fence-acquire"* ]]; then
    printf 'rq-token|acquire|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
    if [ "${FAKE_RQ_ACQUIRE_REPLY_LOST:-0}" = 1 ] \
        && mkdir "${FAKE_RQ_ACQUIRE_REPLY_MARKER}" 2>/dev/null; then
        exit 124
    fi
    if [ "${FAKE_RQ_COMPETING_DEPLOY:-0}" = 1 ]; then
        echo 'another deployment owns the RQ fence' >&2
        exit 79
    fi
    if [ "${FAKE_RQ_PRE_SUSPENDED:-0}" = 1 ]; then
        echo 'RQ is already suspended by an external operator' >&2
        exit 80
    fi
    printf 'no\n'
elif [[ "${args}" == *"# rq-fence-renew"* ]]; then
    printf 'rq-token|renew|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
    : > "${FAKE_RENEWAL_SEEN}"
    renew_call_count=0
    [ ! -f "${FAKE_RQ_RENEW_CALL_COUNT}" ] \
        || renew_call_count="$(cat "${FAKE_RQ_RENEW_CALL_COUNT}")"
    renew_call_count=$((renew_call_count + 1))
    printf '%s\n' "${renew_call_count}" > "${FAKE_RQ_RENEW_CALL_COUNT}"
    if [ "${FAKE_RQ_RENEW_HANGS_ONCE:-0}" = 1 ] \
        && [ "${renew_call_count}" -le 2 ]; then
        /bin/sleep 5
    fi
    if [ "${FAKE_RQ_RENEW_BLOCK_AT_RESUME:-0}" = 1 ]; then
        /bin/sleep 0.2
        printf 'rq-token|renew-complete|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
    fi
    if [ "${FAKE_RQ_RENEW_TRANSIENT_FAILURE:-0}" = 1 ] \
        && [ "${renew_call_count}" -le 2 ]; then
        exit 75
    fi
    if [ "${FAKE_HEARTBEAT_FAILURE:-0}" = 1 ]; then
        exit 75
    fi
elif [[ "${args}" == *"from rq.suspension import is_suspended"* ]]; then
    printf 'rq-token|assert|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
    count=0
    [ ! -f "${FAKE_FENCE_ASSERT_COUNT}" ] || count="$(cat "${FAKE_FENCE_ASSERT_COUNT}")"
    count=$((count + 1))
    printf '%s\n' "${count}" > "${FAKE_FENCE_ASSERT_COUNT}"
    if [ "${FAKE_RENEW_ONCE:-0}" = 1 ] || [ "${FAKE_HEARTBEAT_FAILURE:-0}" = 1 ]; then
        for _attempt in $(seq 1 100); do
            [ -f "${FAKE_RENEWAL_SEEN}" ] && break
            /bin/sleep 0.01
        done
        /bin/sleep 0.02
    fi
    if [ "${FAKE_RQ_RENEW_TRANSIENT_FAILURE:-0}" = 1 ]; then
        for _attempt in $(seq 1 200); do
            renew_call_count=0
            [ ! -f "${FAKE_RQ_RENEW_CALL_COUNT}" ] \
                || renew_call_count="$(cat "${FAKE_RQ_RENEW_CALL_COUNT}")"
            [ "${renew_call_count}" -ge 3 ] && break
            /bin/sleep 0.01
        done
    fi
    if [ "${FAKE_FENCE_LOSS:-0}" = 1 ] && [ "${count}" -ge 2 ]; then
        printf 'no\n'
    else
        printf 'yes\n'
    fi
elif [[ "${args}" == *"# rq-fence-resume"* ]]; then
    printf 'rq-token|resume|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
    if [ "${FAKE_RQ_RESUME_REPLY_LOST:-0}" = 1 ] \
        && mkdir "${FAKE_RQ_RESUME_REPLY_MARKER}" 2>/dev/null; then
        exit 124
    fi
    if [ "${FAKE_RQ_RESUME_FAILURE:-0}" = 1 ]; then
        exit 78
    fi
elif [[ "${args}" == *"Worker.all"* ]]; then
    count=0
    [ ! -f "${FAKE_RECOVERY_REGISTRATION_COUNT}" ] \
        || count="$(cat "${FAKE_RECOVERY_REGISTRATION_COUNT}")"
    if [ -f "${FAKE_RECOVERY_STARTED_MARKER}" ] \
        && [ "${count}" -lt "${FAKE_RECOVERY_REGISTRATION_DELAY_CHECKS}" ]; then
        count=$((count + 1))
        printf '%s\n' "${count}" > "${FAKE_RECOVERY_REGISTRATION_COUNT}"
        printf '0:0\n'
    elif [[ "${FAKE_CATALOG_REGISTRATION_FAILURE:-0}" = 1 && "${args}" == *"exec -T rq-worker-query-catalog "* ]]; then
        printf '1:0\n'
    elif [ "${FAKE_LOCAL_WORKER_REGISTRATION_FAILURE:-0}" = 1 ]; then
        printf '0:1\n'
    else
        printf '1:1\n'
    fi
elif [[ "${args}" == *"exec -T rq-worker hostname"* ]]; then
    printf 'default-worker-host\n'
elif [[ "${args}" == *"exec -T rq-worker-batch hostname"* ]]; then
    printf 'batch-worker-host\n'
elif [[ "${args}" == *"exec -T rq-worker-"*" id -u"* ]]; then
    printf '1002\n'
elif [[ "${args}" == *"exec -T rq-worker-"*" id -g"* ]]; then
    printf '130\n'
elif [[ "${args}" == *"exec -T rq-worker-fork-archive"* && "${args}" == *"fork-archive"* ]]; then
    printf '1:1\n'
elif [[ "${args}" == *"docker compose run"* ]]; then
    # The wepp3 preflight only needs the command to prove secret readability.
    :
elif [[ "${args}" == *"docker compose exec -T cap"* ]]; then
    :
elif [[ "${args}" == *"docker compose stop"* ]]; then
    if [[ "${args}" == *"rq-worker"* ]]; then
        : > "${FAKE_WORKER_STOPPED_MARKER}"
    fi
    if [[ "${args}" == *"shape-converter"* ]]; then
        if [ "${FAKE_SHAPE_STOP_FAILURE:-0}" = 1 ]; then
            exit 81
        fi
        : > "${FAKE_SHAPE_STOPPED_MARKER}"
    fi
    if [ "${FAKE_RQ_RENEW_HANGS_ONCE:-0}" = 1 ]; then
        /bin/sleep 2
    fi
elif [[ "${args}" == *"build --no-cache"* ]] \
    || [[ "${args}" == "up -d --force-recreate" || "${args}" == *" up -d"* ]] \
    || [[ "${args}" == "down" || "${args}" == *" down"* ]] \
    || [[ "${args}" == rq-info* || "${args}" == *" rq-info "* ]]; then
    :
else
    echo "unexpected wctl call: ${args}" >&2
    exit 90
fi
