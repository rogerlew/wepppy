#!/bin/bash
set -euo pipefail
printf 'docker|%s\n' "$*" >> "${FAKE_COMMAND_LOG}"
if [ "${1:-}" = "inspect" ]; then
    format="${3:-}"
    container="${4:-}"
    case "${format}" in
        *State.Running*) printf 'true\n' ;;
        *RestartCount*) printf 'container-%s 0\n' "${container}" ;;
        *Image*)
            gate_count=0
            [ ! -f "${FAKE_GATE_COUNT}" ] || gate_count="$(cat "${FAKE_GATE_COUNT}")"
            if [ "${FAKE_RUNNING_MAP_DRIFT:-0}" = 1 ] \
                && [ "${container}" = "cid-rq-worker" ] \
                && [ "${gate_count}" -ge 3 ]; then
                printf 'sha256:%064d\n' 2
            elif [ "${container}" = "cid-rq-worker-batch" ] && [[ "${FAKE_CONFIG}" == *"wepppy:rollback-test"* ]]; then
                printf 'sha256:%064d\n' 0
            elif [ "${FAKE_CANDIDATE_MISMATCH:-0}" = 1 ] && [ "${container}" = "cid-cap" ]; then
                printf 'sha256:%064d\n' 0
            else
                printf 'sha256:%064d\n' 1
            fi
            ;;
        *Mounts*) printf 'cap-data\n' ;;
        *) printf 'sha256:%064d\n' 1 ;;
    esac
elif [ "${1:-}" = "image" ] && [ "${2:-}" = "inspect" ]; then
    if [ "${3:-}" = "--format" ]; then
        if [ "${5:-}" = 'wepppy:rollback-test' ]; then
            printf 'sha256:%064d\n' 0
        elif [[ "${5:-}" == wepppy-retained-rollback:* ]]; then
            printf 'sha256:%s\n' "${5#wepppy-retained-rollback:}"
        else
            printf 'sha256:%064d\n' 1
        fi
    fi
elif [ "${1:-}" = "ps" ] && [[ "$*" == *"com.docker.compose.service=shape-converter"* ]]; then
    shape_ps_calls=0
    [ ! -f "${FAKE_SHAPE_PS_CALL_COUNT}" ] \
        || shape_ps_calls="$(cat "${FAKE_SHAPE_PS_CALL_COUNT}")"
    shape_ps_calls=$((shape_ps_calls + 1))
    printf '%s\n' "${shape_ps_calls}" > "${FAKE_SHAPE_PS_CALL_COUNT}"
    if [ "${FAKE_SHAPE_DISCOVERY_FAILURE:-0}" = 1 ] && [ "${shape_ps_calls}" -eq 1 ]; then
        exit 82
    fi
    if [ "${FAKE_SHAPE_PS_FAILURE:-0}" = 1 ] && [ "${shape_ps_calls}" -ge 2 ]; then
        exit 82
    fi
    if [ ! -f "${FAKE_SHAPE_STOPPED_MARKER}" ]; then
        printf 'cid-shape-converter\n'
    fi
elif [ "${1:-}" = "stop" ]; then
    if [ "${FAKE_SHAPE_STOP_FAILURE:-0}" = 1 ]; then
        exit 81
    fi
    : > "${FAKE_SHAPE_STOPPED_MARKER}"
elif [ "${1:-}" = "compose" ]; then
    if [[ "$*" == *"# rq-fence-renew"* ]]; then
        printf 'rq-fallback|renew|%s\n' "$*" >> "${FAKE_COMMAND_LOG}"
    fi
    if [[ "$*" == *"wepppy-known-good"* ]] \
        && [ "${FAKE_RECOVERY_FAILURE:-0}" = 1 ]; then
        exit 73
    fi
    if [[ "$*" == *" run "* && "$*" == *"StartedJobRegistry"* ]]; then
        echo 'rq-probe|run' >> "${FAKE_COMMAND_LOG}"
        if [ "${FAKE_RQ_PROBE_RESULT}" = error ]; then
            echo 'Redis connection unavailable' >&2
            exit 1
        fi
        printf '%s\n' "${FAKE_RQ_PROBE_RESULT}"
    elif [[ "$*" == *" run "* && "$*" == *"# rq-fence-acquire"* ]]; then
        token="${!#}"
        printf 'rq-token|acquire|%s\n' "${token}" >> "${FAKE_COMMAND_LOG}"
        if [ "${FAKE_RQ_ACQUIRE_REPLY_LOST:-0}" = 1 ] \
            && mkdir "${FAKE_RQ_ACQUIRE_REPLY_MARKER}" 2>/dev/null; then
            exit 124
        fi
        printf 'no\n'
    elif [[ "$*" == *" run "* && "$*" == *"# rq-fence-renew"* ]]; then
        token="${!#}"
        printf 'rq-token|renew|%s\n' "${token}" >> "${FAKE_COMMAND_LOG}"
        : > "${FAKE_RENEWAL_SEEN}"
        if [ "${FAKE_HEARTBEAT_FAILURE:-0}" = 1 ]; then
            exit 75
        fi
    elif [[ "$*" == *" run "* && "$*" == *"from rq.suspension import is_suspended"* ]]; then
        printf 'rq-token|assert|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
        printf 'yes\n'
    elif [[ "$*" == *" run "* && "$*" == *"# rq-fence-resume"* ]]; then
        token="${!#}"
        printf 'rq-token|resume|%s\n' "${token}" >> "${FAKE_COMMAND_LOG}"
        if [ "${FAKE_RQ_RESUME_REPLY_LOST:-0}" = 1 ] \
            && mkdir "${FAKE_RQ_RESUME_REPLY_MARKER}" 2>/dev/null; then
            exit 124
        fi
        if [ "${FAKE_RQ_RESUME_FAILURE:-0}" = 1 ]; then
            exit 78
        fi
    elif [[ "$*" == *" run "* && "$*" == *"Worker.all"* ]]; then
        printf '1:1\n'
    fi
    if [[ "$*" == *" rm --stop --force "* ]]; then
        if [ "${FAKE_NEW_CLEANUP_FAILURE}" = 1 ]; then exit 83; fi
        rm -f "${FAKE_NEW_MARKER}"
    fi
    if [[ "$*" == *" up -d "* ]]; then
        if [[ "$*" != *"wepppy-known-good"* ]] && [ -n "${FAKE_NEW_SERVICE}" ]; then
            : > "${FAKE_NEW_MARKER}"
        fi
        rm -f "${FAKE_WORKER_STOPPED_MARKER}"
        if [[ "$*" == *"wepppy-known-good"* ]]; then
            : > "${FAKE_RECOVERY_STARTED_MARKER}"
        fi
    fi
    if [[ "$*" == *" up -d --no-deps --force-recreate cap"* ]] \
        && [ "${FAKE_RECOVERY_FAILURE:-0}" = 1 ]; then
        exit 73
    fi
    if [[ "$*" == *" ps -q caddy"* ]]; then
        if [ "${FAKE_CADDY_INSPECTION_FAILURE:-0}" = 1 ]; then
            exit 76
        fi
        printf 'cid-caddy\n'
    fi
elif [ "${1:-}" = "builder" ] || [ "${1:-}" = "system" ] || [ "${1:-}" = "tag" ]; then
    :
else
    echo "unexpected docker call: $*" >&2
    exit 91
fi
