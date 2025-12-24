#!/usr/bin/env bash
# Stop and disable legacy weppcloud systemd services.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Error: run as root (sudo)." >&2
  exit 1
fi

UNITS=(
  caddy.service
  gunicorn-elevationquery.service
  gunicorn-metquery.service
  gunicorn-preflight.service
  gunicorn-status.service
  gunicorn-weppcloud.service
  gunicorn-wmesque.service
  gunicorn-wmesque2.service
  postgresql.service
  postgresql@16-main.service
  redis-server.service
  rq-wepppy-worker-pool.service
)

unit_exists() {
  systemctl show -p LoadState --value "$1" 2>/dev/null | grep -qv '^not-found$'
}

disable_unit() {
  local unit="$1"
  if unit_exists "$unit"; then
    echo "Stopping $unit..."
    systemctl stop "$unit" >/dev/null 2>&1 || true
    echo "Disabling $unit..."
    systemctl disable "$unit" >/dev/null 2>&1 || true
    systemctl reset-failed "$unit" >/dev/null 2>&1 || true
  else
    echo "Skipping $unit (not found)."
  fi
}

for unit in "${UNITS[@]}"; do
  disable_unit "$unit"
done

echo "Done."
