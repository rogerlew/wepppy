#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-weppcloud}"
CONTAINER_REPO_ROOT="${CONTAINER_REPO_ROOT:-/workdir/wepppy}"
RUNS_DIR="${RUNS_DIR:-${CONTAINER_REPO_ROOT}/tests/wepp_runner/fixtures/hillslope_smoke/runs}"
CASES="${CASES:-p1}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <binary-path-inside-container>" >&2
  exit 2
fi

# Share fixture staging, PASS adaptation and completion checks with the host gate.
docker exec -i \
  -e RUNS_DIR="${RUNS_DIR}" \
  -e CASES="${CASES}" \
  -e TIMEOUT_SECONDS="${TIMEOUT_SECONDS}" \
  -w "${CONTAINER_REPO_ROOT}" \
  "${CONTAINER}" \
  bash tools/smoke_wepp_binary_host.sh "$1"
