#!/bin/bash
# Production Deployment Script for WEPPcloud
# Usage: ./scripts/deploy-production.sh [--skip-pull] [--skip-build] [--skip-themes] [--flush-rq-db|--no-flush-rq-db] [--skip-docker-prune] [--docker-prune-volumes]
# The installed wctl preset selects full production, worker-pool, or the
# dedicated wepp3 fork/archive deployment automatically.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

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
HEALTHCHECK_URL="${HEALTHCHECK_URL:-}"

while [[ $# -gt 0 ]]; do
    case $1 in
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
            echo "Usage: $0 [--skip-pull] [--skip-build] [--skip-themes] [--flush-rq-db|--no-flush-rq-db] [--require-rq-redis] [--skip-docker-prune] [--docker-prune-volumes]"
            exit 1
            ;;
    esac
done

cd "${PROJECT_ROOT}"

COMPOSE_SERVICES="$(
    capture_wctl_with_retry \
        "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
        "${WCTL_COMPOSE_RETRIES}" \
        "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
        docker compose config --services
)"
HAS_WEPPCLOUD=false
if echo "${COMPOSE_SERVICES}" | grep -q "^weppcloud$"; then
    HAS_WEPPCLOUD=true
fi
IS_WEPP3_FORK_ARCHIVE=false
if [ "$(printf "%s\n" "${COMPOSE_SERVICES}" | sed '/^$/d' | wc -l | tr -d ' ')" -eq 1 ] \
    && echo "${COMPOSE_SERVICES}" | grep -q "^rq-worker-fork-archive$"; then
    IS_WEPP3_FORK_ARCHIVE=true
fi

if [ "${HAS_WEPPCLOUD}" = true ]; then
    DEPLOY_MODE="full"
    BUILD_SERVICES=(weppcloud rq-worker)
    # These services have their own images/build contexts; include them when present so
    # a full deploy doesn't accidentally keep stale binaries when compose/env changes.
    for svc in cap status preflight; do
        if echo "${COMPOSE_SERVICES}" | grep -q "^${svc}$"; then
            BUILD_SERVICES+=("${svc}")
        fi
    done
elif [ "${IS_WEPP3_FORK_ARCHIVE}" = true ]; then
    DEPLOY_MODE="wepp3-fork-archive"
    BUILD_SERVICES=(rq-worker-fork-archive)
else
    DEPLOY_MODE="worker"
    BUILD_SERVICES=(rq-worker rq-worker-batch weppcloudr)
fi

if [ "${IS_WEPP3_FORK_ARCHIVE}" = true ] && [ "${FLUSH_RQ_DB}" = true ]; then
    echo "✗ Refusing --flush-rq-db on the dedicated wepp3 worker deployment." >&2
    echo "  Redis DB 9 is shared production state and is not owned by wepp3." >&2
    exit 1
fi

if [ "${IS_WEPP3_FORK_ARCHIVE}" = true ]; then
    if ! wctl docker compose run --rm --no-deps --entrypoint /bin/sh \
        rq-worker-fork-archive -c 'test -r /run/secrets/redis_password'; then
        echo "✗ The wepp3 worker identity (uid 1002) cannot read docker/secrets/redis_password." >&2
        echo "  Grant a read ACL without broadening the secret's 0600 base mode:" >&2
        echo "  sudo setfacl -m u:1002:r docker/secrets/redis_password" >&2
        exit 1
    fi
fi

echo "============================================"
echo "WEPPcloud Production Deployment"
echo "============================================"
echo "Project root: ${PROJECT_ROOT}"
echo "Mode: ${DEPLOY_MODE}"
echo "Timestamp: $(date --iso-8601=seconds)"
echo ""

# Git pull
if [ "${SKIP_PULL}" = false ]; then
    echo ">>> Step 1: Pulling latest changes from git..."
    safe_git_fast_forward_pull
    echo ""
else
    echo ">>> Step 1: Skipping git pull (--skip-pull)"
    echo ""
fi

# Build Docker images
if [ "${SKIP_BUILD}" = false ]; then
    echo ">>> Step 2: Building Docker images..."
    wctl build --no-cache "${BUILD_SERVICES[@]}"
    echo ""
    
    echo ">>> Step 2b: Pruning Docker build cache..."
    docker builder prune -af
    echo ""
else
    echo ">>> Step 2: Skipping Docker build (--skip-build)"
    echo ""
fi

# Stop services. For wepp3, SIGTERM initiates an RQ warm shutdown before
# Compose removes the container: the worker stops dequeuing first and any job
# already running is allowed to finish, closing the check-then-stop race.
echo ">>> Step 3: Stopping services..."
if [ "${IS_WEPP3_FORK_ARCHIVE}" = true ] \
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
run_wctl_with_retry \
    "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
    "${WCTL_COMPOSE_RETRIES}" \
    "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
    down
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
if [ "${HAS_WEPPCLOUD}" = true ]; then
    echo ">>> Step 4: Building static assets..."

    # Build controllers-gl.js
    echo "    Building controllers-gl.js..."
    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py \
        --output wepppy/weppcloud/static/js/controllers-gl.js

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
run_wctl_with_retry \
    "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
    "${WCTL_COMPOSE_RETRIES}" \
    "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
    up -d
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
            exit 1
        fi
        echo "  Waiting for WEPPcloud to be ready (attempt ${ATTEMPT}/${MAX_ATTEMPTS})..."
        sleep 2
    done
else
    echo ">>> Step 6: Skipping WEPPcloud health check (worker stack detected)..."
    if [ "${IS_WEPP3_FORK_ARCHIVE}" = true ]; then
        echo "    Verifying dedicated fork/archive worker identity and registration..."
        WORKER_UID="$(wctl docker compose exec -T rq-worker-fork-archive id -u)"
        WORKER_GID="$(wctl docker compose exec -T rq-worker-fork-archive id -g)"
        if [ "${WORKER_UID}:${WORKER_GID}" != "1002:130" ]; then
            echo "✗ wepp3 worker identity is ${WORKER_UID}:${WORKER_GID}; expected 1002:130 for production NFS writes." >&2
            exit 1
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
            exit 1
        fi
        run_wctl_with_retry \
            "${WCTL_COMPOSE_TIMEOUT_SECONDS}" \
            "${WCTL_COMPOSE_RETRIES}" \
            "${WCTL_COMPOSE_RETRY_DELAY_SECONDS}" \
            rq-info --service rq-worker-fork-archive --detail
        echo "✓ wepp3 fork/archive worker is running as 1002:130 and registered with RQ"
    fi
fi

if [ "${SKIP_DOCKER_PRUNE}" = false ]; then
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
