#!/bin/bash
# Production Deployment Script for WEPPcloud
# Usage: ./scripts/deploy-production.sh [--skip-pull] [--skip-build] [--skip-themes]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Parse arguments
SKIP_PULL=false
SKIP_BUILD=false
SKIP_THEMES=false

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
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-pull] [--skip-build] [--skip-themes]"
            exit 1
            ;;
    esac
done

cd "${PROJECT_ROOT}"

echo "============================================"
echo "WEPPcloud Production Deployment"
echo "============================================"
echo "Project root: ${PROJECT_ROOT}"
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
    ./wctl/wctl.sh build --no-cache weppcloud rq-worker
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
./wctl/wctl.sh down
echo ""

# Build static assets (controllers and themes)
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

# Start services
echo ">>> Step 5: Starting services..."
./wctl/wctl.sh up -d
echo ""

# Wait for health check
echo ">>> Step 6: Waiting for services to be healthy..."
sleep 5

# Check weppcloud health
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -fsS http://localhost:8080/weppcloud/health > /dev/null 2>&1; then
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

echo ""
echo "============================================"
echo "Deployment complete!"
echo "============================================"
echo "Controllers bundle: wepppy/weppcloud/static/js/controllers-gl.js"
echo "Theme CSS: wepppy/weppcloud/static/css/themes/"
echo ""
echo "Remember to hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)"
echo "to bypass cache and load the new assets."
