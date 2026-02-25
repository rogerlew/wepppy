#!/bin/bash
# Production Deployment Script for WEPPcloud
# Usage: ./scripts/deploy-production.sh [--skip-pull] [--skip-build] [--skip-themes] [--flush-rq-db|--no-flush-rq-db]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

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

# Parse arguments
SKIP_PULL=false
SKIP_BUILD=false
SKIP_THEMES=false
FLUSH_RQ_DB=false
FLUSH_RQ_DB_EXPLICIT=false
REQUIRE_RQ_REDIS=false
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
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-pull] [--skip-build] [--skip-themes] [--flush-rq-db|--no-flush-rq-db] [--require-rq-redis]"
            exit 1
            ;;
    esac
done

cd "${PROJECT_ROOT}"

COMPOSE_SERVICES="$(wctl docker compose config --services)"
HAS_WEPPCLOUD=false
if echo "${COMPOSE_SERVICES}" | grep -q "^weppcloud$"; then
    HAS_WEPPCLOUD=true
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
else
    DEPLOY_MODE="worker"
    BUILD_SERVICES=(rq-worker rq-worker-batch weppcloudr)
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
    git pull
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

# Stop services
echo ">>> Step 3: Stopping services..."
wctl  down
echo ""

# Flush RQ Redis DB 9 (optional, default off)
if [ "${FLUSH_RQ_DB}" = true ]; then
    echo ">>> Step 3b: Flushing Redis DB 9 (RQ)..."

    REQUIRE_FLUSH_REDIS="${REQUIRE_RQ_REDIS}"

    # Ensure redis is reachable locally when running a full stack with a redis service.
    # On worker-only hosts, redis may be absent and/or remote; the flush script will best-effort skip when unreachable.
    if echo "${COMPOSE_SERVICES}" | grep -q "^redis$"; then
        echo "    Bringing up redis service for RQ flush..."
        wctl up -d redis
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
wctl up -d
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
        if curl -fsS "${HEALTHCHECK_URL}" > /dev/null 2>&1; then
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
fi

echo ""
echo "============================================"
echo "Deployment complete!"
echo "============================================"
echo "Controllers bundle: wepppy/weppcloud/static/js/controllers-gl.js"
echo "Theme CSS: wepppy/weppcloud/static/css/themes/"
echo ""
echo "Remember to hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)"
echo "to bypass cache and load the new assets."
