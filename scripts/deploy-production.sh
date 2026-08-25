#!/bin/bash
# Production Deployment Script for WEPPcloud
# Usage: ./scripts/deploy-production.sh [--targeted-web|--targeted-cap] [--print-plan] [--skip-pull] [--skip-build] [--skip-themes] [--flush-rq-db|--no-flush-rq-db] [--skip-docker-prune] [--docker-prune-volumes]
# The installed wctl preset selects full production, worker-pool, or the
# dedicated wepp3 fork/archive deployment automatically.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ORIGINAL_ARGS=("$@")

# Harden compose passthrough calls against occasional docker compose hangs.
WCTL_COMPOSE_TIMEOUT_SECONDS="${WCTL_COMPOSE_TIMEOUT_SECONDS:-180}"
WCTL_COMPOSE_RETRIES="${WCTL_COMPOSE_RETRIES:-3}"
WCTL_COMPOSE_RETRY_DELAY_SECONDS="${WCTL_COMPOSE_RETRY_DELAY_SECONDS:-5}"

read_env_value() {
    local key="$1"
    local file="$2"
    local value

    value=$(awk -F= -v key="${key}" '
        $0 ~ "^[[:space:]]*"key"=" {
            sub("^[[:space:]]*"key"=", "", $0)
            sub(/[[:space:]]+#.*$/, "", $0)
            print $0
            exit
        }' "${file}")

    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    echo "${value}"
}

run_with_timeout() {
    local timeout_seconds="$1"
    shift

    if command -v timeout >/dev/null 2>&1; then
        timeout --foreground --signal=TERM --kill-after=15 "${timeout_seconds}" "$@"
        return $?
    fi

    echo "Warning: 'timeout' command not found; running without timeout protection." >&2
    "$@"
}

run_wctl_with_retry() {
    local timeout_seconds="$1"
    local retries="$2"
    local retry_delay_seconds="$3"
    shift 3
    local cmd=("$@")
    local attempt=1
    local exit_code=0

    while [ "${attempt}" -le "${retries}" ]; do
        if run_with_timeout "${timeout_seconds}" wctl "${cmd[@]}"; then
            return 0
        fi

        exit_code=$?
        if [ "${attempt}" -ge "${retries}" ]; then
            echo "✗ Command failed after ${attempt} attempts: wctl ${cmd[*]} (exit ${exit_code})" >&2
            return "${exit_code}"
        fi

        if [ "${exit_code}" -eq 124 ]; then
            echo "    Command timed out after ${timeout_seconds}s (attempt ${attempt}/${retries}); retrying in ${retry_delay_seconds}s..." >&2
        else
            echo "    Command failed with exit ${exit_code} (attempt ${attempt}/${retries}); retrying in ${retry_delay_seconds}s..." >&2
        fi
        sleep "${retry_delay_seconds}"
        attempt=$((attempt + 1))
    done

    return "${exit_code}"
}

capture_wctl_with_retry() {
    local timeout_seconds="$1"
    local retries="$2"
    local retry_delay_seconds="$3"
    shift 3
    local cmd=("$@")
    local attempt=1
    local exit_code=0
    local output=""

    while [ "${attempt}" -le "${retries}" ]; do
        if output="$(run_with_timeout "${timeout_seconds}" wctl "${cmd[@]}")"; then
            printf "%s\n" "${output}"
            return 0
        fi

        exit_code=$?
        if [ "${attempt}" -ge "${retries}" ]; then
            echo "✗ Command failed after ${attempt} attempts: wctl ${cmd[*]} (exit ${exit_code})" >&2
            return "${exit_code}"
        fi

        if [ "${exit_code}" -eq 124 ]; then
            echo "    Command timed out after ${timeout_seconds}s (attempt ${attempt}/${retries}); retrying in ${retry_delay_seconds}s..." >&2
        else
            echo "    Command failed with exit ${exit_code} (attempt ${attempt}/${retries}); retrying in ${retry_delay_seconds}s..." >&2
        fi
        sleep "${retry_delay_seconds}"
        attempt=$((attempt + 1))
    done

    return "${exit_code}"
}

print_limited_list() {
    local header="$1"
    local items="$2"
    local limit="${3:-20}"
    local count

    count=$(printf "%s\n" "${items}" | sed '/^$/d' | wc -l | tr -d ' ')
    if [ "${count}" -eq 0 ]; then
        return 0
    fi

    echo "${header}"
    printf "%s\n" "${items}" | sed '/^$/d' | sed -n "1,${limit}p" | sed 's/^/    /'
    if [ "${count}" -gt "${limit}" ]; then
        echo "    ... (${count} total; showing first ${limit})"
    fi
}

validate_git_credential_helpers() {
    local helper
    local missing=0
    local needs_gh_auth=0

    while IFS= read -r helper; do
        [ -z "${helper}" ] && continue
        case "${helper}" in
            gh)
                needs_gh_auth=1
                if ! command -v git-credential-gh >/dev/null 2>&1; then
                    echo "✗ Git credential helper 'gh' is configured but git-credential-gh is not installed/found on PATH." >&2
                    echo "  Remediation: run 'gh auth setup-git' (or fix credential.helper) before deploying." >&2
                    missing=1
                fi
                ;;
        esac
    done < <(git config --get-all credential.helper 2>/dev/null || true)

    if [ "${needs_gh_auth}" -eq 1 ]; then
        if ! command -v gh >/dev/null 2>&1; then
            echo "✗ Git credential helper 'gh' is configured but GitHub CLI 'gh' is not installed/found on PATH." >&2
            echo "  Remediation: install gh and run 'gh auth login' + 'gh auth setup-git' before deploying." >&2
            missing=1
        elif ! gh auth status --hostname github.com >/dev/null 2>&1; then
            echo "✗ GitHub CLI auth check failed for github.com." >&2
            echo "  Remediation: re-authenticate with 'gh auth login' (and optionally rerun 'gh auth setup-git')." >&2
            missing=1
        fi
    fi

    if [ "${missing}" -ne 0 ]; then
        return 1
    fi
    return 0
}

ensure_git_worktree_clean() {
    local tracked_changes=""
    local untracked_files=""

    tracked_changes="$(git status --porcelain=v1 --untracked-files=no || true)"
    if [ -n "${tracked_changes}" ]; then
        echo "✗ Refusing deployment pull: tracked git changes are present in working tree/index." >&2
        print_limited_list "  Tracked changes:" "${tracked_changes}" 30 >&2
        echo "  Commit/stash/discard tracked changes or rerun with --skip-pull." >&2
        return 1
    fi

    untracked_files="$(git ls-files --others --exclude-standard || true)"
    if [ -n "${untracked_files}" ]; then
        echo "✗ Refusing deployment pull: untracked files are present and may block fast-forward update." >&2
        print_limited_list "  Untracked files:" "${untracked_files}" 30 >&2
        echo "  Remediation options:" >&2
        echo "    - stash with untracked: git stash push --include-untracked" >&2
        echo "    - or clean untracked: git clean -fd" >&2
        echo "    - or rerun deploy with --skip-pull if repo is already updated" >&2
        return 1
    fi

    return 0
}

safe_git_fast_forward_pull() {
    local original_head=""
    local current_branch=""
    local upstream_ref=""
    local remote_name=""
    local remote_branch=""
    local fetched_head=""

    current_branch="$(git rev-parse --abbrev-ref HEAD)"
    if [ "${current_branch}" = "HEAD" ]; then
        echo "✗ Refusing deployment pull from detached HEAD." >&2
        return 1
    fi

    original_head="$(git rev-parse HEAD)"
    upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true)"
    if [ -z "${upstream_ref}" ]; then
        upstream_ref="origin/${current_branch}"
    fi

    remote_name="${upstream_ref%%/*}"
    remote_branch="${upstream_ref#*/}"

    validate_git_credential_helpers
    ensure_git_worktree_clean

    echo "    Fetching ${upstream_ref}..."
    git fetch --prune "${remote_name}" "${remote_branch}"
    fetched_head="$(git rev-parse FETCH_HEAD)"

    if [ "${fetched_head}" = "${original_head}" ]; then
        echo "    Already up to date."
        return 0
    fi

    if ! git merge-base --is-ancestor "${original_head}" "${fetched_head}"; then
        echo "✗ Refusing deployment pull: local HEAD is not an ancestor of ${upstream_ref} (non-fast-forward)." >&2
        echo "  Local HEAD : ${original_head}" >&2
        echo "  Upstream   : ${fetched_head}" >&2
        echo "  Resolve branch divergence manually, then rerun deployment." >&2
        return 1
    fi

    echo "    Fast-forwarding ${current_branch} to ${fetched_head}..."
    if ! git merge --ff-only "${fetched_head}"; then
        echo "✗ Fast-forward apply failed; rolling repository back to ${original_head}." >&2
        git reset --hard "${original_head}" >/dev/null 2>&1 || true
        return 1
    fi

    return 0
}

# Parse arguments
SKIP_PULL=false
SKIP_BUILD=false
SKIP_THEMES=false
FLUSH_RQ_DB=false
FLUSH_RQ_DB_EXPLICIT=false
REQUIRE_RQ_REDIS=false
SKIP_DOCKER_PRUNE=false
DOCKER_PRUNE_VOLUMES=false
TARGETED_WEB=false
TARGETED_CAP=false
PRINT_PLAN=false
HEALTHCHECK_URL="${HEALTHCHECK_URL:-}"
RQ_ENGINE_HEALTHCHECK_URL="${RQ_ENGINE_HEALTHCHECK_URL:-}"
CAP_HEALTHCHECK_URL="${CAP_HEALTHCHECK_URL:-}"
CAP_RUNTIME_VALIDATOR="${CAP_RUNTIME_VALIDATOR:-${PROJECT_ROOT}/docker/validate-cap-runtime-contract.sh}"
CAP_RUNTIME_PREPARER="${CAP_RUNTIME_PREPARER:-${PROJECT_ROOT}/docker/prepare-cap-runtime.sh}"
WEPPCLOUDR_RUNTIME_VALIDATOR="${WEPPCLOUDR_RUNTIME_VALIDATOR:-${PROJECT_ROOT}/docker/validate-weppcloudr-runtime-contract.sh}"
CONTROLLERS_JS_BUILDER="${CONTROLLERS_JS_BUILDER:-${PROJECT_ROOT}/wepppy/weppcloud/controllers_js/build_controllers_js.py}"
CONTROLLERS_JS_TARGET="${CONTROLLERS_JS_TARGET:-${PROJECT_ROOT}/wepppy/weppcloud/static/js/controllers-gl.js}"
DEPLOY_STATE_DIR="${DEPLOY_STATE_DIR:-/var/tmp}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --targeted-web)
            TARGETED_WEB=true
            shift
            ;;
        --targeted-cap)
            TARGETED_CAP=true
            shift
            ;;
        --print-plan)
            PRINT_PLAN=true
            shift
            ;;
        --skip-pull)
            SKIP_PULL=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-themes)
            SKIP_THEMES=true
            shift
            ;;
        --flush-rq-db)
            FLUSH_RQ_DB=true
            FLUSH_RQ_DB_EXPLICIT=true
            shift
            ;;
        --no-flush-rq-db)
            FLUSH_RQ_DB=false
            FLUSH_RQ_DB_EXPLICIT=true
            shift
            ;;
        --require-rq-redis)
            REQUIRE_RQ_REDIS=true
            shift
            ;;
        --skip-docker-prune)
            SKIP_DOCKER_PRUNE=true
            shift
            ;;
        --docker-prune-volumes)
            DOCKER_PRUNE_VOLUMES=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--targeted-web|--targeted-cap] [--print-plan] [--skip-pull] [--skip-build] [--skip-themes] [--flush-rq-db|--no-flush-rq-db] [--require-rq-redis] [--skip-docker-prune] [--docker-prune-volumes]"
            exit 1
            ;;
    esac
done

cd "${PROJECT_ROOT}"

configure_deploy_topology() {
    COMPOSE_SERVICES="$(
        capture_wctl_with_retry \
            "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
            "${WCTL_COMPOSE_RETRIES}" \
            "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
            docker compose config --services
    )"
    HAS_WEPPCLOUD=false
    IS_WEPP3_FORK_ARCHIVE=false
    ACTIVE_SERVICE_ARGS=()
    while IFS= read -r service; do
        [ -n "${service}" ] && ACTIVE_SERVICE_ARGS+=(--active-service "${service}")
    done <<< "${COMPOSE_SERVICES}"

    if echo "${COMPOSE_SERVICES}" | grep -q "^weppcloud$"; then
        HAS_WEPPCLOUD=true
    fi
    if [ "$(printf "%s\n" "${COMPOSE_SERVICES}" | sed '/^$/d' | wc -l | tr -d ' ')" -eq 1 ] \
        && echo "${COMPOSE_SERVICES}" | grep -q "^rq-worker-fork-archive$"; then
        IS_WEPP3_FORK_ARCHIVE=true
    fi

    if [ "${HAS_WEPPCLOUD}" = true ] \
        && echo "${COMPOSE_SERVICES}" | grep -q "^rq-worker$"; then
        DEPLOY_MODE="full"
    elif [ "${IS_WEPP3_FORK_ARCHIVE}" = true ]; then
        DEPLOY_MODE="wepp3-fork-archive"
    elif echo "${COMPOSE_SERVICES}" | grep -q "^rq-worker$" \
        && echo "${COMPOSE_SERVICES}" | grep -q "^rq-worker-batch$" \
        && echo "${COMPOSE_SERVICES}" | grep -q "^weppcloudr$"; then
        DEPLOY_MODE="worker"
    else
        echo "✗ Unsupported production Compose topology; refusing to guess deployment services." >&2
        echo "  Effective services:" >&2
        printf "%s\n" "${COMPOSE_SERVICES}" | sed 's/^/    /' >&2
        echo "  Reinstall the intended wctl preset before deploying." >&2
        exit 1
    fi

    BUILD_OUTPUT="$(
        wctl docker compose config --format json \
            | python3 "${SCRIPT_DIR}/compose_deploy_contract.py" \
                build-services "${ACTIVE_SERVICE_ARGS[@]}"
    )"
    mapfile -t BUILD_SERVICES <<< "${BUILD_OUTPUT}"
    EXPECTED_OUTPUT="$(
        wctl docker compose config --format json \
            | python3 "${SCRIPT_DIR}/compose_deploy_contract.py" \
                expected-services "${ACTIVE_SERVICE_ARGS[@]}"
    )"
    mapfile -t EXPECTED_RUNNING_SERVICES <<< "${EXPECTED_OUTPUT}"
    if [ "${DEPLOY_MODE}" = "full" ]; then
        FILTERED_EXPECTED_SERVICES=()
        for service in "${EXPECTED_RUNNING_SERVICES[@]}"; do
            [ "${service}" = "rq-worker-fork-archive" ] || FILTERED_EXPECTED_SERVICES+=("${service}")
        done
        EXPECTED_RUNNING_SERVICES=("${FILTERED_EXPECTED_SERVICES[@]}")
    fi
    RECREATED_SERVICES=("${EXPECTED_RUNNING_SERVICES[@]}")

    if [ "${TARGETED_WEB}" = true ]; then
        if [ "${DEPLOY_MODE}" != "full" ] \
            || ! echo "${COMPOSE_SERVICES}" | grep -q "^rq-engine$"; then
            echo "✗ --targeted-web requires a full stack containing weppcloud and rq-engine." >&2
            exit 1
        fi
        # Both services resolve to the same WEPPCLOUD_IMAGE. Building both in
        # one Compose invocation races two writes to the same tag.
        BUILD_SERVICES=(weppcloud)
        RECREATED_SERVICES=(weppcloud rq-engine)
        EXPECTED_RUNNING_SERVICES=(weppcloud rq-engine)
    fi

    if [ "${TARGETED_CAP}" = true ]; then
        if [ "${DEPLOY_MODE}" != "full" ] \
            || ! echo "${COMPOSE_SERVICES}" | grep -q "^cap$"; then
            echo "✗ --targeted-cap requires a full stack containing CAP." >&2
            exit 1
        fi
        BUILD_SERVICES=(cap)
        RECREATED_SERVICES=(cap)
        EXPECTED_RUNNING_SERVICES=(cap)
    fi
}

configure_deploy_topology

validate_deploy_topology() {
    if [ "${FLUSH_RQ_DB}" = true ]; then
        echo "✗ Deploy-time Redis flushing is incompatible with the global RQ cutover fence." >&2
        echo "  Perform destructive queue maintenance as a separate, explicitly fenced operation." >&2
        exit 1
    fi
    if [ "${TARGETED_WEB}" = true ] && [ "${TARGETED_CAP}" = true ]; then
        echo "✗ --targeted-web and --targeted-cap are mutually exclusive." >&2
        exit 1
    fi

    if [ "${TARGETED_WEB}" = true ] && [ "${FLUSH_RQ_DB}" = true ]; then
        echo "✗ --targeted-web cannot be combined with --flush-rq-db." >&2
        echo "  Targeted web deployment must leave Redis and workers untouched." >&2
        exit 1
    fi

    if [ "${TARGETED_CAP}" = true ] && [ "${FLUSH_RQ_DB}" = true ]; then
        echo "✗ --targeted-cap cannot be combined with --flush-rq-db." >&2
        exit 1
    fi

    if [ "${IS_WEPP3_FORK_ARCHIVE}" = true ] && [ "${FLUSH_RQ_DB}" = true ]; then
        echo "✗ Refusing --flush-rq-db on the dedicated wepp3 worker deployment." >&2
        echo "  Redis DB 9 is shared production state and is not owned by wepp3." >&2
        exit 1
    fi

    if [ "${IS_WEPP3_FORK_ARCHIVE}" = true ]; then
        if ! wctl docker compose run --rm --no-deps --entrypoint /bin/sh \
            rq-worker-fork-archive -c \
            'test -r /run/secrets/redis_password && test -r /opt/vendor/weppcloud2/weppcloud2/discord_bot/.bot_token'; then
            echo "✗ The wepp3 worker identity (uid 1002) cannot read a required mounted secret." >&2
            echo "  Redis remediation (preserves the secret's 0600 base mode):" >&2
            echo "  sudo setfacl -m u:1002:r docker/secrets/redis_password" >&2
            echo "  If DISCORD_BOT_TOKEN_FILE is set, grant uid 1002 read access there too." >&2
            exit 1
        fi
    fi
}

if [ "${PRINT_PLAN}" = true ]; then
    validate_deploy_topology
    echo "mode=${DEPLOY_MODE}"
    printf "build=%s\n" "${BUILD_SERVICES[*]}"
    printf "recreate=%s\n" "${RECREATED_SERVICES[*]}"
    printf "expected-running=%s\n" "${EXPECTED_RUNNING_SERVICES[*]}"
    exit 0
fi

DEPLOY_LOCK_FILE="${DEPLOY_LOCK_FILE:-${PROJECT_ROOT}/.git/wepppy-production-deploy.lock}"
if [ "${DEPLOY_LOCK_HELD_PID:-}" != "$$" ]; then
    exec 9>"${DEPLOY_LOCK_FILE}"
    if ! flock -n 9; then
        echo "✗ Another deployment holds ${DEPLOY_LOCK_FILE}; refusing concurrent activation." >&2
        exit 1
    fi
    export DEPLOY_LOCK_HELD_PID="$$"
fi

echo "============================================"
echo "WEPPcloud Production Deployment"
echo "============================================"
echo "Project root: ${PROJECT_ROOT}"
echo "Mode: ${DEPLOY_MODE}"
if [ "${TARGETED_WEB}" = true ]; then
    echo "Scope: targeted weppcloud + rq-engine recreation; dependencies remain running"
elif [ "${TARGETED_CAP}" = true ]; then
    echo "Scope: targeted CAP recreation; all other services remain running"
fi
echo "Timestamp: $(date --iso-8601=seconds)"
echo ""

# Capture the running topology before a pull can change Compose semantics.
PRE_PULL_CAP_CONFIG=""
if printf "%s\n" "${RECREATED_SERVICES[@]}" | grep -qx "cap" \
    && [ -n "$(wctl docker compose ps -q cap)" ]; then
    PRE_PULL_CAP_CONFIG="$(mktemp "${DEPLOY_STATE_DIR%/}/wepppy-cap-prepull-config.XXXXXX.yml")"
    wctl docker compose config > "${PRE_PULL_CAP_CONFIG}"
    chmod 0600 "${PRE_PULL_CAP_CONFIG}"
fi

# Git pull
if [ "${SKIP_PULL}" = false ]; then
    echo ">>> Step 1: Pulling latest changes from git..."
    SCRIPT_SHA_BEFORE_PULL="$(sha256sum "${SCRIPT_DIR}/deploy-production.sh" | awk '{print $1}')"
    safe_git_fast_forward_pull
    SCRIPT_SHA_AFTER_PULL="$(sha256sum "${SCRIPT_DIR}/deploy-production.sh" | awk '{print $1}')"
    if [ "${SCRIPT_SHA_BEFORE_PULL}" != "${SCRIPT_SHA_AFTER_PULL}" ]; then
        echo "    Deployment script changed during pull; restarting with the updated script..."
        exec "${SCRIPT_DIR}/deploy-production.sh" "${ORIGINAL_ARGS[@]}" --skip-pull
    fi
    # Compose files may change even when this script does not. Re-resolve the
    # effective topology before constructing any build or stop command.
    configure_deploy_topology
    echo ""
else
    echo ">>> Step 1: Skipping git pull (--skip-pull)"
    echo ""
fi

validate_deploy_topology

if [ "${SKIP_BUILD}" = true ] && [ "${#BUILD_SERVICES[@]}" -gt 0 ]; then
    echo "✗ --skip-build is unsafe when locally built services will be recreated." >&2
    echo "  Build the candidate images or use --print-plan for a read-only inspection." >&2
    exit 1
fi

assert_no_active_rq_jobs() {
    if ! printf "%s\n" "${COMPOSE_SERVICES}" | grep -qx "rq-worker"; then
        return 0
    fi
    echo "    Verifying no default or batch RQ jobs are executing..."
    ACTIVE_RQ_JOBS="$(wctl docker compose exec -T rq-worker /opt/venv/bin/python -c '
import redis
from rq.registry import StartedJobRegistry
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
print(sum(len(StartedJobRegistry(name, connection=connection).get_job_ids()) for name in ("default", "batch")))
')"
    [[ "${ACTIVE_RQ_JOBS}" =~ ^[0-9]+$ ]] || {
        echo "✗ Unable to determine active RQ job count." >&2
        return 1
    }
    [ "${ACTIVE_RQ_JOBS}" -eq 0 ] || {
        echo "✗ Refusing deployment while ${ACTIVE_RQ_JOBS} default/batch RQ jobs are executing." >&2
        return 1
    }
}

RQ_SUSPENDED_BY_DEPLOY=false
RQ_FENCE_ACTIVE=false
RQ_FENCE_HEARTBEAT_PID=""
RQ_FENCE_FAILURE_FILE=""
RQ_FENCE_TOKEN=""
run_rq_control_program() {
    local program="$1"
    shift
    if ! wctl docker compose exec -T rq-worker /opt/venv/bin/python -c "${program}" "$@"; then
        wctl docker compose run --rm --no-deps --entrypoint /opt/venv/bin/python \
            rq-worker -c "${program}" "$@"
    fi
}

renew_rq_fence_once() {
    run_rq_control_program '
import redis
import sys
from rq.suspension import suspend
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
key = "wepppy:deploy:rq-fence"
token = sys.argv[1]
renewed = connection.eval(
    "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('expire', KEYS[1], ARGV[2]) else return 0 end",
    1, key, token, 3600,
)
if renewed != 1:
    raise SystemExit("deployment fence ownership lost")
suspend(connection, ttl=3600)
' "${RQ_FENCE_TOKEN}"
}

assert_rq_fence() {
    [ "${RQ_FENCE_ACTIVE}" = true ] || return 0
    if [ -n "${RQ_FENCE_FAILURE_FILE}" ] && [ -s "${RQ_FENCE_FAILURE_FILE}" ]; then
        echo "✗ Global RQ suspension heartbeat failed." >&2
        return 1
    fi
    RQ_FENCE_STATE="$(run_rq_control_program '
import redis
import sys
from rq.suspension import is_suspended
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
owned = connection.get("wepppy:deploy:rq-fence") == sys.argv[1].encode()
print("yes" if owned and is_suspended(connection) else "no")
' "${RQ_FENCE_TOKEN}")"
    [ "${RQ_FENCE_STATE}" = "yes" ] || {
        echo "✗ Global RQ suspension fence was lost." >&2
        return 1
    }
}

suspend_rq_dequeue() {
    if ! printf "%s\n" "${COMPOSE_SERVICES}" | grep -qx "rq-worker"; then
        return 0
    fi
    RQ_FENCE_TOKEN="$(hostname)-$$-$(date +%s)"
    RQ_WAS_SUSPENDED="$(wctl docker compose exec -T rq-worker /opt/venv/bin/python -c '
import redis
import sys
from rq.suspension import is_suspended, suspend
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
key = "wepppy:deploy:rq-fence"
token = sys.argv[1]
if not connection.set(key, token, nx=True, ex=3600):
    raise SystemExit("another deployment owns the RQ fence")
if is_suspended(connection):
    connection.delete(key)
    raise SystemExit("RQ is already suspended by an external operator")
suspend(connection, ttl=3600)
print("no")
' "${RQ_FENCE_TOKEN}")"
    if [ "${RQ_WAS_SUSPENDED}" = "no" ]; then
        RQ_SUSPENDED_BY_DEPLOY=true
        echo "    Suspended global RQ dequeue for deployment cutover."
    else
        echo "✗ Unable to establish the global RQ suspension fence." >&2
        return 1
    fi
    RQ_FENCE_ACTIVE=true
    RQ_FENCE_FAILURE_FILE="$(mktemp "${DEPLOY_STATE_DIR%/}/wepppy-rq-fence.XXXXXX")"
    local deployment_pid="$$"
    (
        while kill -0 "${deployment_pid}" 2>/dev/null; do
            sleep 30
            kill -0 "${deployment_pid}" 2>/dev/null || exit 0
            if ! renew_rq_fence_once >/dev/null 2>&1; then
                printf 'renewal failed\n' > "${RQ_FENCE_FAILURE_FILE}"
                exit 1
            fi
        done
    ) &
    RQ_FENCE_HEARTBEAT_PID="$!"
    assert_rq_fence
}

resume_rq_if_owned() {
    if [ "${RQ_SUSPENDED_BY_DEPLOY}" = true ]; then
        RQ_RESUME_PROGRAM='
import redis
import sys
from rq.suspension import resume
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
key = "wepppy:deploy:rq-fence"
if connection.get(key) != sys.argv[1].encode():
    raise SystemExit("deployment fence ownership lost before resume")
resume(connection)
connection.delete(key)
'
        if ! run_rq_control_program "${RQ_RESUME_PROGRAM}" "${RQ_FENCE_TOKEN}"; then
            echo "✗ Failed to resume the deployment-owned global RQ suspension." >&2
            return 1
        fi
    fi
    if [ -n "${RQ_FENCE_HEARTBEAT_PID}" ]; then
        kill "${RQ_FENCE_HEARTBEAT_PID}" 2>/dev/null || true
        wait "${RQ_FENCE_HEARTBEAT_PID}" 2>/dev/null || true
        RQ_FENCE_HEARTBEAT_PID=""
    fi
    if [ -n "${RQ_FENCE_FAILURE_FILE}" ]; then
        rm -f -- "${RQ_FENCE_FAILURE_FILE}"
        RQ_FENCE_FAILURE_FILE=""
    fi
    RQ_FENCE_ACTIVE=false
    if [ "${RQ_SUSPENDED_BY_DEPLOY}" != true ]; then
        return 0
    fi
    RQ_SUSPENDED_BY_DEPLOY=false
    echo "    Resumed global RQ dequeue."
}

if [ "${TARGETED_WEB}" = false ] && [ "${TARGETED_CAP}" = false ]; then
    assert_no_active_rq_jobs
fi

CAP_RESCUE_IMAGE=""
CAP_RESCUE_CONFIG=""
CAP_RESCUE_OVERRIDE=""
CAP_ACTIVATION_STARTED=false
STAGED_CONTROLLERS_JS=""
BACKUP_CONTROLLERS_JS=""
if printf "%s\n" "${RECREATED_SERVICES[@]}" | grep -qx "cap"; then
    CURRENT_CAP_CONTAINER="$(wctl docker compose ps -q cap)"
    if [ "${TARGETED_CAP}" = true ] && [ -z "${CURRENT_CAP_CONTAINER}" ]; then
        echo "✗ Targeted CAP requires a currently running known-good CAP container." >&2
        exit 1
    fi
    if [ -n "${CURRENT_CAP_CONTAINER}" ]; then
        CURRENT_CAP_IMAGE_ID="$(docker inspect --format '{{.Image}}' "${CURRENT_CAP_CONTAINER}")"
        CAP_RESCUE_IMAGE="wepppy-cap-rescue:$(date -u +%Y%m%dT%H%M%SZ)"
        docker tag "${CURRENT_CAP_IMAGE_ID}" "${CAP_RESCUE_IMAGE}"
        CAP_RESCUE_CONFIG="${PRE_PULL_CAP_CONFIG}"
        [ -n "${CAP_RESCUE_CONFIG}" ] || CAP_RESCUE_CONFIG="$(mktemp "${DEPLOY_STATE_DIR%/}/wepppy-cap-rescue-config.XXXXXX.yml")"
        CAP_RESCUE_OVERRIDE="$(mktemp "${DEPLOY_STATE_DIR%/}/wepppy-cap-rescue-override.XXXXXX.yml")"
        [ -s "${CAP_RESCUE_CONFIG}" ] || wctl docker compose config > "${CAP_RESCUE_CONFIG}"
        printf 'services:\n  cap:\n    image: %s\n' "${CAP_RESCUE_IMAGE}" > "${CAP_RESCUE_OVERRIDE}"
        chmod 0600 "${CAP_RESCUE_CONFIG}" "${CAP_RESCUE_OVERRIDE}"
        run_with_timeout 30 wctl docker compose exec -T cap node - < "${PROJECT_ROOT}/services/cap/canary.js"
        echo "    Preserved known-good CAP rescue image: ${CAP_RESCUE_IMAGE}"
        echo "    Preserved known-good rendered config: ${CAP_RESCUE_CONFIG}"
    fi
fi

recover_targeted_cap() {
    local original_exit="$?"
    local recovery_exit="${original_exit}"
    trap - ERR
    if [ -n "${STAGED_CONTROLLERS_JS}" ]; then
        rm -f -- "${STAGED_CONTROLLERS_JS}"
        STAGED_CONTROLLERS_JS=""
    fi
    if [ -n "${BACKUP_CONTROLLERS_JS}" ] && [ -f "${BACKUP_CONTROLLERS_JS}" ]; then
        mv -f -- "${BACKUP_CONTROLLERS_JS}" "${CONTROLLERS_JS_TARGET}"
        BACKUP_CONTROLLERS_JS=""
        echo "✓ Restored the pre-deploy controllers bundle" >&2
    fi
    if [ "${CAP_ACTIVATION_STARTED}" != true ] || [ -z "${CAP_RESCUE_IMAGE}" ]; then
        if ! resume_rq_if_owned; then
            echo "✗ RQ_RESUME_FAILED: the 3600-second suspension TTL remains as break-glass protection" >&2
            recovery_exit=87
        fi
        return "${recovery_exit}"
    fi
    echo "✗ Candidate CAP activation failed; restoring ${CAP_RESCUE_IMAGE}" >&2
    local recovered=false
    if docker compose -f "${CAP_RESCUE_CONFIG}" -f "${CAP_RESCUE_OVERRIDE}" \
        up -d --no-deps --force-recreate cap; then
      for _recovery_attempt in $(seq 1 60); do
        if run_with_timeout 30 docker compose -f "${CAP_RESCUE_CONFIG}" -f "${CAP_RESCUE_OVERRIDE}" \
            exec -T cap node - < "${PROJECT_ROOT}/services/cap/canary.js"; then
          recovered=true
          break
        fi
        sleep 2
      done
    fi
    if [ "${recovered}" = true ]; then
        # Reconcile the public route as well: a full-stack activation may have
        # replaced or interrupted Caddy before the candidate failed.
        local rescue_caddy
        if ! rescue_caddy="$(docker compose -f "${CAP_RESCUE_CONFIG}" -f "${CAP_RESCUE_OVERRIDE}" ps -q caddy)"; then
            echo "✗ CAP_RESCUE_FAILED: unable to inspect Caddy" >&2
            if ! resume_rq_if_owned; then return 87; fi
            return 86
        fi
        if [ -z "${rescue_caddy}" ] \
            || [ "$(docker inspect --format '{{.State.Running}}' "${rescue_caddy}" 2>/dev/null || true)" != "true" ]; then
            if ! docker compose -f "${CAP_RESCUE_CONFIG}" -f "${CAP_RESCUE_OVERRIDE}" \
                up -d --no-deps caddy >/dev/null; then
                echo "✗ CAP_RESCUE_FAILED: unable to restore Caddy" >&2
                if ! resume_rq_if_owned; then return 87; fi
                return 86
            fi
        fi
        local recovery_cap_url="${CAP_HEALTHCHECK_URL}"
        local recovery_host=""
        if [ -z "${recovery_cap_url}" ] && [ -f "${PROJECT_ROOT}/docker/.env" ]; then
            recovery_host="$(read_env_value EXTERNAL_HOST "${PROJECT_ROOT}/docker/.env")"
            if [ -n "${recovery_host}" ]; then
                case "${recovery_host}" in
                    http://*|https://*) recovery_cap_url="${recovery_host%/}/cap/health" ;;
                    *) recovery_cap_url="https://${recovery_host}/cap/health" ;;
                esac
            fi
        fi
        if [ -n "${recovery_cap_url}" ]; then
            for _external_attempt in $(seq 1 30); do
                if curl --connect-timeout 5 --max-time 10 -fsS "${recovery_cap_url}" >/dev/null; then
                    if ! resume_rq_if_owned; then
                        echo "✗ RQ_RESUME_FAILED after CAP recovery" >&2
                        return 87
                    fi
                    echo "✓ Known-good CAP rescue image restored; internal functional and public health passed" >&2
                    return "${recovery_exit}"
                fi
                sleep 2
            done
            echo "✗ CAP_RESCUE_FAILED: public CAP route did not recover" >&2
            if ! resume_rq_if_owned; then return 87; fi
            return 86
        fi
        echo "✗ CAP_RESCUE_FAILED: no public CAP health URL could be resolved" >&2
        if ! resume_rq_if_owned; then return 87; fi
        return 86
    else
        echo "✗ CAP_RESCUE_FAILED: rescue image retained as ${CAP_RESCUE_IMAGE}" >&2
        if ! resume_rq_if_owned; then return 87; fi
        return 86
    fi
    return "${recovery_exit}"
}
trap recover_targeted_cap ERR
trap 'echo "✗ Deployment interrupted" >&2; false' INT TERM

# Build Docker images
if [ "${SKIP_BUILD}" = false ]; then
    echo ">>> Step 2: Building Docker images..."
    BASE_BUILD_SERVICES=()
    DEPENDENT_BUILD_SERVICES=()
    for service in "${BUILD_SERVICES[@]}"; do
        if [ "${service}" = "fcgiwrap" ]; then
            DEPENDENT_BUILD_SERVICES+=("${service}")
        else
            BASE_BUILD_SERVICES+=("${service}")
        fi
    done
    if [ "${#BASE_BUILD_SERVICES[@]}" -gt 0 ]; then
        wctl build --no-cache "${BASE_BUILD_SERVICES[@]}"
    fi
    if [ "${#DEPENDENT_BUILD_SERVICES[@]}" -gt 0 ]; then
        echo "    Building dependent images after the canonical wepppy base..."
        wctl build --no-cache "${DEPENDENT_BUILD_SERVICES[@]}"
    fi
    echo ""
    
    echo ">>> Step 2b: Pruning Docker build cache..."
    docker builder prune -af
    echo ""
else
    echo ">>> Step 2: Skipping Docker build (--skip-build)"
    echo ""
fi

if printf "%s\n" "${BUILD_SERVICES[@]}" | grep -qx "weppcloudr"; then
    WEPPCLOUDR_IMAGE="$(wctl docker compose config --format json | python3 -c 'import json,sys; c=json.load(sys.stdin); print(c["services"]["weppcloudr"]["image"])')"
    WORKER_IMAGE="$(wctl docker compose config --format json | python3 -c 'import json,sys; c=json.load(sys.stdin); print(c["services"]["rq-worker"]["image"])')"
    "${WEPPCLOUDR_RUNTIME_VALIDATOR}" "${WEPPCLOUDR_IMAGE}" "${WORKER_IMAGE}"
fi

if printf "%s\n" "${RECREATED_SERVICES[@]}" | grep -qx "cap"; then
    CAP_IMAGE="$(wctl docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["cap"]["image"])')"
    "${CAP_RUNTIME_VALIDATOR}" "${CAP_IMAGE}"
    "${CAP_RUNTIME_PREPARER}" --secret-only
fi

# Stop services. For wepp3, SIGTERM initiates an RQ warm shutdown before
# Compose removes the container: the worker stops dequeuing first and any job
# already running is allowed to finish, closing the check-then-stop race.
echo ">>> Step 3: Stopping services..."
if [ "${DEPLOY_MODE}" = "full" ] && [ "${FLUSH_RQ_DB}" = true ]; then
    suspend_rq_dequeue
    assert_no_active_rq_jobs
    run_wctl_with_retry 216030 1 0 docker compose stop --timeout 216000 rq-worker rq-worker-batch
fi
if [ "${DEPLOY_MODE}" = "worker" ]; then
    suspend_rq_dequeue
    assert_no_active_rq_jobs
    run_wctl_with_retry 216030 1 0 docker compose stop --timeout 216000 rq-worker rq-worker-batch
fi
if [ "${TARGETED_WEB}" = true ] || [ "${TARGETED_CAP}" = true ]; then
    echo "    Skipping stack shutdown; workers and dependencies remain running."
elif [ "${DEPLOY_MODE}" = "full" ]; then
    echo "    Skipping full-stack down; services will be force-recreated in place."
elif [ "${IS_WEPP3_FORK_ARCHIVE}" = true ] \
    && wctl docker compose ps --status running --services 2>/dev/null \
        | grep -q '^rq-worker-fork-archive$'; then
    FORK_ARCHIVE_STOP_TIMEOUT_SECONDS="${FORK_ARCHIVE_STOP_TIMEOUT_SECONDS:-216000}"
    echo "    Requesting warm shutdown of rq-worker-fork-archive..."
    run_wctl_with_retry \
        "$((FORK_ARCHIVE_STOP_TIMEOUT_SECONDS + 30))" \
        1 \
        0 \
        docker compose stop --timeout "${FORK_ARCHIVE_STOP_TIMEOUT_SECONDS}" \
        rq-worker-fork-archive
fi
if [ "${TARGETED_WEB}" = false ] && [ "${TARGETED_CAP}" = false ] \
    && [ "${DEPLOY_MODE}" != "full" ]; then
    run_wctl_with_retry \
        "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
        "${WCTL_COMPOSE_RETRIES}" \
        "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
        down
fi
echo ""

# Flush RQ Redis DB 9 (optional, default off)
if [ "${FLUSH_RQ_DB}" = true ]; then
    echo ">>> Step 3b: Flushing Redis DB 9 (RQ)..."

    REQUIRE_FLUSH_REDIS="${REQUIRE_RQ_REDIS}"

    # Ensure redis is reachable locally when running a full stack with a redis service.
    # On worker-only hosts, redis may be absent and/or remote; the flush script will best-effort skip when unreachable.
    if echo "${COMPOSE_SERVICES}" | grep -q "^redis$"; then
        echo "    Bringing up redis service for RQ flush..."
        run_wctl_with_retry \
            "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
            "${WCTL_COMPOSE_RETRIES}" \
            "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
            up -d redis
        echo ""

        if [ -z "${REDIS_PORT:-}" ] && [ -f "${PROJECT_ROOT}/docker/.env" ]; then
            REDIS_PORT_FROM_ENV="$(read_env_value "REDIS_PORT" "${PROJECT_ROOT}/docker/.env")"
            if [ -n "${REDIS_PORT_FROM_ENV}" ]; then
                export REDIS_PORT="${REDIS_PORT_FROM_ENV}"
            fi
        fi

        export REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
        export REDIS_PORT="${REDIS_PORT:-6379}"
        REQUIRE_FLUSH_REDIS=true
    fi

    if [ -z "${RQ_REDIS_URL:-}" ] && [ -f "${PROJECT_ROOT}/docker/.env" ]; then
        RQ_REDIS_URL="$(read_env_value "RQ_REDIS_URL" "${PROJECT_ROOT}/docker/.env")"
        if [ -n "${RQ_REDIS_URL}" ]; then
            export RQ_REDIS_URL
        fi
    fi

    if [ -z "${REDIS_PASSWORD_FILE:-}" ]; then
        if [ -f "/run/secrets/redis_password" ]; then
            export REDIS_PASSWORD_FILE="/run/secrets/redis_password"
        elif [ -f "${PROJECT_ROOT}/docker/secrets/redis_password" ]; then
            echo "    Using compose secrets file for Redis auth: ${PROJECT_ROOT}/docker/secrets/redis_password"
            export REDIS_PASSWORD_FILE="${PROJECT_ROOT}/docker/secrets/redis_password"
        fi
    fi

    FLUSH_ARGS=()
    if [ "${REQUIRE_FLUSH_REDIS}" = true ]; then
        FLUSH_ARGS+=(--require-redis)
        export REDIS_PING_ATTEMPTS="${REDIS_PING_ATTEMPTS:-120}"
        export REDIS_PING_DELAY_SECONDS="${REDIS_PING_DELAY_SECONDS:-1}"
    fi

    "${SCRIPT_DIR}/redis_flush_rq_db.sh" "${FLUSH_ARGS[@]}"
    echo ""
else
    echo ">>> Step 3b: Skipping Redis DB 9 flush (default policy; pass --flush-rq-db to enable)"
    echo ""
fi

# Build static assets (controllers and themes)
if [ "${HAS_WEPPCLOUD}" = true ] && [ "${TARGETED_CAP}" = false ]; then
    echo ">>> Step 4: Building static assets..."

    # Build controllers-gl.js
    echo "    Building controllers-gl.js..."
    STAGED_CONTROLLERS_JS="$(mktemp "${CONTROLLERS_JS_TARGET}.deploy.XXXXXX")"
    python3 "${CONTROLLERS_JS_BUILDER}" \
        --output "${STAGED_CONTROLLERS_JS}"

    # Build themes
    if [ "${SKIP_THEMES}" = false ]; then
        echo "    Building theme CSS files..."
        if [ -f "wepppy/weppcloud/static-src/themes/build-themes.js" ]; then
            npm --prefix wepppy/weppcloud/static-src run build:themes
        else
            echo "    Warning: Theme build script not found, skipping"
        fi
    else
        echo "    Skipping theme build (--skip-themes)"
    fi

    echo ""
else
    echo ">>> Step 4: Skipping static assets (worker stack detected)..."
    echo ""
fi

# Start services
echo ">>> Step 5: Starting services..."
if [ "${DEPLOY_MODE}" = "full" ] \
    && [ "${TARGETED_WEB}" = false ] && [ "${TARGETED_CAP}" = false ] \
    && [ "${FLUSH_RQ_DB}" = false ]; then
    suspend_rq_dequeue
    assert_no_active_rq_jobs
    run_wctl_with_retry 216030 1 0 docker compose stop --timeout 216000 rq-worker rq-worker-batch
fi
assert_rq_fence
if printf "%s\n" "${RECREATED_SERVICES[@]}" | grep -qx "cap"; then
    # Keep login available through every build/static step.  The closed-ledger
    # interval starts only immediately before migration and activation.
    CAP_ACTIVATION_STARTED=true
    run_wctl_with_retry \
        "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
        "${WCTL_COMPOSE_RETRIES}" \
        "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
        docker compose stop cap
    "${CAP_RUNTIME_PREPARER}" --data-only
fi
if [ -n "${STAGED_CONTROLLERS_JS}" ]; then
    CONTROLLERS_BACKUP_CANDIDATE="$(mktemp "${CONTROLLERS_JS_TARGET}.rollback.XXXXXX")"
    if ! cp --preserve=mode,timestamps -- "${CONTROLLERS_JS_TARGET}" "${CONTROLLERS_BACKUP_CANDIDATE}"; then
        rm -f -- "${CONTROLLERS_BACKUP_CANDIDATE}"
        false
    fi
    BACKUP_CONTROLLERS_JS="${CONTROLLERS_BACKUP_CANDIDATE}"
    mv -f -- "${STAGED_CONTROLLERS_JS}" "${CONTROLLERS_JS_TARGET}"
    STAGED_CONTROLLERS_JS=""
    echo "    Published controllers-gl.js atomically immediately before service cutover."
fi
if [ "${TARGETED_WEB}" = true ]; then
    run_wctl_with_retry \
        "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
        "${WCTL_COMPOSE_RETRIES}" \
        "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
        docker compose up -d --no-deps --force-recreate weppcloud rq-engine
elif [ "${TARGETED_CAP}" = true ]; then
    CAP_ACTIVATION_STARTED=true
    run_wctl_with_retry \
        "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
        "${WCTL_COMPOSE_RETRIES}" \
        "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
        docker compose up -d --no-deps --force-recreate cap
else
    if [ -n "${CAP_RESCUE_IMAGE}" ]; then
        CAP_ACTIVATION_STARTED=true
    fi
    run_wctl_with_retry \
        "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
        "${WCTL_COMPOSE_RETRIES}" \
        "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
        up -d --force-recreate
fi
echo ""

# Wait for health check
if [ "${HAS_WEPPCLOUD}" = true ]; then
    echo ">>> Step 6: Waiting for services to be healthy..."
    sleep 5

    # Resolve health check URL (prefer explicit override, then EXTERNAL_HOST from docker/.env)
    if [ -z "${HEALTHCHECK_URL}" ] && [ -f "${PROJECT_ROOT}/docker/.env" ]; then
        HEALTHCHECK_URL="$(read_env_value "HEALTHCHECK_URL" "${PROJECT_ROOT}/docker/.env")"
    fi
    if [ -z "${EXTERNAL_HOST:-}" ] && [ -f "${PROJECT_ROOT}/docker/.env" ]; then
        EXTERNAL_HOST="$(read_env_value "EXTERNAL_HOST" "${PROJECT_ROOT}/docker/.env")"
    fi

    if [ -z "${HEALTHCHECK_URL}" ]; then
        if [ -n "${EXTERNAL_HOST:-}" ]; then
            case "${EXTERNAL_HOST}" in
                http://*|https://*)
                    HEALTHCHECK_URL="${EXTERNAL_HOST%/}/weppcloud/health"
                    ;;
                *)
                    HEALTHCHECK_URL="https://${EXTERNAL_HOST}/weppcloud/health"
                    ;;
            esac
        else
            HEALTHCHECK_URL="http://localhost:8080/weppcloud/health"
        fi
    fi

    echo "    Health check URL: ${HEALTHCHECK_URL}"

    # Check weppcloud health
    MAX_ATTEMPTS=30
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if curl --connect-timeout 5 --max-time 10 -fsS "${HEALTHCHECK_URL}" > /dev/null 2>&1; then
            echo "✓ WEPPcloud is healthy"
            break
        fi
        ATTEMPT=$((ATTEMPT + 1))
        if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
            echo "✗ WEPPcloud health check failed after ${MAX_ATTEMPTS} attempts"
            false
        fi
        echo "  Waiting for WEPPcloud to be ready (attempt ${ATTEMPT}/${MAX_ATTEMPTS})..."
        sleep 2
    done

    if printf "%s\n" "${RECREATED_SERVICES[@]}" | grep -qx "rq-engine"; then
        if [ -z "${RQ_ENGINE_HEALTHCHECK_URL}" ]; then
            case "${HEALTHCHECK_URL}" in
                */weppcloud/health)
                    RQ_ENGINE_HEALTHCHECK_URL="${HEALTHCHECK_URL%/weppcloud/health}/rq-engine/health"
                    ;;
                *)
                    echo "✗ Set RQ_ENGINE_HEALTHCHECK_URL when HEALTHCHECK_URL does not end in /weppcloud/health." >&2
                    false
                    ;;
            esac
        fi
        echo "    RQ-engine health check URL: ${RQ_ENGINE_HEALTHCHECK_URL}"
        RQ_ENGINE_ATTEMPT=0
        while [ "${RQ_ENGINE_ATTEMPT}" -lt "${MAX_ATTEMPTS}" ]; do
            if curl --connect-timeout 5 --max-time 10 -fsS "${RQ_ENGINE_HEALTHCHECK_URL}" > /dev/null 2>&1; then
                echo "✓ rq-engine is healthy"
                break
            fi
            RQ_ENGINE_ATTEMPT=$((RQ_ENGINE_ATTEMPT + 1))
            if [ "${RQ_ENGINE_ATTEMPT}" -eq "${MAX_ATTEMPTS}" ]; then
                echo "✗ rq-engine health check failed after ${MAX_ATTEMPTS} attempts" >&2
                false
            fi
            echo "  Waiting for rq-engine to be ready (attempt ${RQ_ENGINE_ATTEMPT}/${MAX_ATTEMPTS})..."
            sleep 2
        done
    fi
else
    echo ">>> Step 6: Skipping WEPPcloud health check (worker stack detected)..."
    if [ "${IS_WEPP3_FORK_ARCHIVE}" = true ]; then
        echo "    Verifying dedicated fork/archive worker identity and registration..."
        WORKER_UID="$(wctl docker compose exec -T rq-worker-fork-archive id -u)"
        WORKER_GID="$(wctl docker compose exec -T rq-worker-fork-archive id -g)"
        if [ "${WORKER_UID}:${WORKER_GID}" != "1002:130" ]; then
            echo "✗ wepp3 worker identity is ${WORKER_UID}:${WORKER_GID}; expected 1002:130 for production NFS writes." >&2
            false
        fi
        REGISTERED_FORK_ARCHIVE_WORKERS=""
        for _attempt in $(seq 1 60); do
            REGISTERED_FORK_ARCHIVE_WORKERS="$(
                wctl docker compose exec -T rq-worker-fork-archive \
                    /opt/venv/bin/python -c \
                    'import os; import redis; import socket; from rq import Worker; connection = redis.Redis.from_url(os.environ["RQ_REDIS_URL"], password=open(os.environ["REDIS_PASSWORD_FILE"], encoding="utf-8").read().strip()); workers = [worker for worker in Worker.all(connection=connection) if "fork-archive" in worker.queue_names()]; current = [worker for worker in workers if worker.hostname == socket.gethostname() and connection.ttl(worker.key) > 0]; print(f"{len(workers)}:{len(current)}")' \
                    2>/dev/null || true
            )"
            if [ "${REGISTERED_FORK_ARCHIVE_WORKERS}" = "1:1" ]; then
                break
            fi
            sleep 2
        done
        if [ "${REGISTERED_FORK_ARCHIVE_WORKERS}" != "1:1" ]; then
            echo "✗ Expected one global/current-container fork-archive worker; found '${REGISTERED_FORK_ARCHIVE_WORKERS:-query failed}'." >&2
            false
        fi
        run_wctl_with_retry \
            "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
            "${WCTL_COMPOSE_RETRIES}" \
            "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
            rq-info --service rq-worker-fork-archive --detail
        echo "✓ wepp3 fork/archive worker is running as 1002:130 and registered with RQ"
    fi
fi

if printf "%s\n" "${RECREATED_SERVICES[@]}" | grep -qx "cap"; then
    if [ -z "${CAP_HEALTHCHECK_URL}" ]; then
        case "${HEALTHCHECK_URL}" in
            */weppcloud/health)
                CAP_HEALTHCHECK_URL="${HEALTHCHECK_URL%/weppcloud/health}/cap/health"
                ;;
            *)
                echo "✗ Set CAP_HEALTHCHECK_URL when HEALTHCHECK_URL does not end in /weppcloud/health." >&2
                false
                ;;
        esac
    fi
    echo "    CAP health check URL: ${CAP_HEALTHCHECK_URL}"
    CAP_ATTEMPT=0
    while [ "${CAP_ATTEMPT}" -lt "${MAX_ATTEMPTS:-30}" ]; do
        if curl --connect-timeout 5 --max-time 10 -fsS "${CAP_HEALTHCHECK_URL}" >/dev/null 2>&1 \
            && wctl docker compose exec -T cap node - < "${PROJECT_ROOT}/services/cap/canary.js"; then
            echo "✓ CAP readiness and functional canary passed"
            break
        fi
        CAP_ATTEMPT=$((CAP_ATTEMPT + 1))
        if [ "${CAP_ATTEMPT}" -eq "${MAX_ATTEMPTS:-30}" ]; then
            echo "✗ CAP readiness or challenge/redeem/siteverify canary failed" >&2
            false
        fi
        sleep 2
    done
fi

EXPECTED_SERVICE_ARGS=()
for service in "${EXPECTED_RUNNING_SERVICES[@]}"; do
    EXPECTED_SERVICE_ARGS+=(--expected-service "${service}")
done
echo "    Waiting for every recreated service to reach its accepted state..."
SERVICE_STATE_ATTEMPT=0
while [ "${SERVICE_STATE_ATTEMPT}" -lt 60 ]; do
    PS_OUTPUT="$(wctl docker compose ps --all --format json)"
    if printf "%s\n" "${PS_OUTPUT}" \
        | python3 "${SCRIPT_DIR}/compose_deploy_contract.py" \
            validate-ps "${EXPECTED_SERVICE_ARGS[@]}" 2>/dev/null; then
        break
    fi
    SERVICE_STATE_ATTEMPT=$((SERVICE_STATE_ATTEMPT + 1))
    if [ "${SERVICE_STATE_ATTEMPT}" -eq 60 ]; then
        printf "%s\n" "${PS_OUTPUT}" \
            | python3 "${SCRIPT_DIR}/compose_deploy_contract.py" \
                validate-ps "${EXPECTED_SERVICE_ARGS[@]}"
    fi
    sleep 5
done
echo "✓ All recreated services are running and healthy where healthchecks exist"

echo "    Verifying candidate image identity for locally built services..."
CANDIDATE_IMAGE_ROWS="$(
    wctl docker compose config --format json \
        | python3 "${SCRIPT_DIR}/compose_deploy_contract.py" \
            candidate-images "${EXPECTED_SERVICE_ARGS[@]}"
)"
while IFS=$'\t' read -r service image; do
    [ -n "${service}" ] || continue
    CANDIDATE_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "${image}")"
    while IFS= read -r container; do
        [ -n "${container}" ] || continue
        RUNNING_IMAGE_ID="$(docker inspect --format '{{.Image}}' "${container}")"
        if [ "${RUNNING_IMAGE_ID}" != "${CANDIDATE_IMAGE_ID}" ]; then
            echo "✗ ${service} is not running candidate image ${image}" >&2
            false
        fi
    done < <(wctl docker compose ps -q "${service}")
done <<< "${CANDIDATE_IMAGE_ROWS}"
echo "✓ Every locally built recreated service runs its candidate image"

echo "    Observing container identity and restart counts for 15 seconds..."
STABILITY_BEFORE="$(
    for service in "${EXPECTED_RUNNING_SERVICES[@]}"; do
        while IFS= read -r container; do
            [ -z "${container}" ] || docker inspect --format '{{.Id}} {{.RestartCount}}' "${container}"
        done < <(wctl docker compose ps -q "${service}")
    done | sort
)"
sleep 15
STABILITY_AFTER="$(
    for service in "${EXPECTED_RUNNING_SERVICES[@]}"; do
        while IFS= read -r container; do
            [ -z "${container}" ] || docker inspect --format '{{.Id}} {{.RestartCount}}' "${container}"
        done < <(wctl docker compose ps -q "${service}")
    done | sort
)"
[ "${STABILITY_BEFORE}" = "${STABILITY_AFTER}" ] || {
    echo "✗ Container identity or restart count changed during stability observation." >&2
    false
}
echo "✓ Recreated services remained stable"

if printf "%s\n" "${COMPOSE_SERVICES}" | grep -qx "rq-worker"; then
    DEFAULT_WORKER_HOSTNAME="$(wctl docker compose exec -T rq-worker hostname)"
    BATCH_WORKER_HOSTNAME="$(wctl docker compose exec -T rq-worker-batch hostname)"
    RQ_REGISTRATION="$(wctl docker compose exec -T rq-worker /opt/venv/bin/python -c '
import redis
import sys
from rq import Worker
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
workers = [worker for worker in Worker.all(connection=connection) if connection.ttl(worker.key) > 0]
print("{}:{}".format(
    sum(worker.hostname == sys.argv[1] and "default" in worker.queue_names() for worker in workers),
    sum(worker.hostname == sys.argv[2] and "batch" in worker.queue_names() for worker in workers),
))
' "${DEFAULT_WORKER_HOSTNAME}" "${BATCH_WORKER_HOSTNAME}")"
    DEFAULT_WORKERS="${RQ_REGISTRATION%%:*}"
    BATCH_WORKERS="${RQ_REGISTRATION##*:}"
    [[ "${DEFAULT_WORKERS}" =~ ^[0-9]+$ && "${BATCH_WORKERS}" =~ ^[0-9]+$ ]] \
        && [ "${DEFAULT_WORKERS}" -gt 0 ] && [ "${BATCH_WORKERS}" -gt 0 ] || {
        echo "✗ RQ default/batch worker registration is incomplete: ${RQ_REGISTRATION}" >&2
        false
    }
    echo "✓ RQ default/batch workers are registered"
    assert_rq_fence
fi

resume_rq_if_owned

if [ -n "${BACKUP_CONTROLLERS_JS}" ]; then
    rm -f -- "${BACKUP_CONTROLLERS_JS}"
    BACKUP_CONTROLLERS_JS=""
fi

if [ "${TARGETED_WEB}" = true ] || [ "${TARGETED_CAP}" = true ] \
    || [ -n "${CAP_RESCUE_IMAGE}" ]; then
    echo ""
    echo ">>> Step 7: Skipping broad Docker runtime prune after targeted deployment"
elif [ "${IS_WEPP3_FORK_ARCHIVE}" = true ]; then
    echo ""
    echo ">>> Step 7: Skipping broad Docker runtime prune on the dedicated wepp3 host"
    echo "    Build cache was pruned after the image build; unrelated host images are left intact."
elif [ "${SKIP_DOCKER_PRUNE}" = false ]; then
    echo ""
    echo ">>> Step 7: Pruning unused Docker runtime artifacts..."
    PRUNE_ARGS=(-a -f)
    if [ "${DOCKER_PRUNE_VOLUMES}" = true ]; then
        echo "    WARNING: --docker-prune-volumes enabled; unused Docker volumes will be deleted."
        PRUNE_ARGS+=(--volumes)
    fi
    docker system prune "${PRUNE_ARGS[@]}"
else
    echo ""
    echo ">>> Step 7: Skipping Docker runtime prune (--skip-docker-prune)"
fi

echo ""
echo "============================================"
echo "Deployment complete!"
echo "============================================"
if [ "${HAS_WEPPCLOUD}" = true ]; then
    echo "Controllers bundle: wepppy/weppcloud/static/js/controllers-gl.js"
    echo "Theme CSS: wepppy/weppcloud/static/css/themes/"
    echo ""
    echo "Remember to hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)"
    echo "to bypass cache and load the new assets."
elif [ "${IS_WEPP3_FORK_ARCHIVE}" = true ]; then
    echo "Dedicated service: rq-worker-fork-archive"
    echo "Runtime identity: 1002:130"
fi
