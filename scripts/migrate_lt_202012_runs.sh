#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/workdir/wepppy}"
DEFAULT_RUN_ROOT="/wc1/runs/lt"
if [[ -d "/geodata/weppcloud_runs" ]]; then
  DEFAULT_RUN_ROOT="/geodata/weppcloud_runs"
fi
RUN_ROOT="${RUN_ROOT:-${DEFAULT_RUN_ROOT}}"
RUN_PATTERN="${RUN_PATTERN:-lt_202012_*}"
LOG_ROOT="${LOG_ROOT:-${RUN_ROOT}/_migration_logs}"
DRY_RUN="${DRY_RUN:-false}"
ARCHIVE_BEFORE="${ARCHIVE_BEFORE:-false}"
SLEEP_SECS="${SLEEP_SECS:-0}"
WCTL_BIN="${WCTL_BIN:-wctl}"

cd "${PROJECT_DIR}"

if ! command -v "${WCTL_BIN}" >/dev/null 2>&1; then
  echo "Error: ${WCTL_BIN} not found on PATH." >&2
  exit 1
fi

mkdir -p "${LOG_ROOT}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="${LOG_ROOT}/migrate_lt_202012_${timestamp}.log"

echo "Starting LT 202012 migrations at ${timestamp}" | tee -a "${log_file}"
echo "Run root: ${RUN_ROOT}" | tee -a "${log_file}"
echo "Pattern: ${RUN_PATTERN}" | tee -a "${log_file}"
echo "Dry run: ${DRY_RUN}" | tee -a "${log_file}"
echo "Archive before: ${ARCHIVE_BEFORE}" | tee -a "${log_file}"
echo "Sleep seconds: ${SLEEP_SECS}" | tee -a "${log_file}"
echo "" | tee -a "${log_file}"

mapfile -t run_dirs < <(find "${RUN_ROOT}" -maxdepth 1 -mindepth 1 -type d -name "${RUN_PATTERN}" | sort)

if [[ ${#run_dirs[@]} -eq 0 ]]; then
  echo "No matching runs found under ${RUN_ROOT}." | tee -a "${log_file}"
  exit 0
fi

failures=0

for run_dir in "${run_dirs[@]}"; do
  runid="$(basename "${run_dir}")"
  echo "---- ${runid} ----" | tee -a "${log_file}"

  cmd=("${WCTL_BIN}" "migrate-run" "${runid}")
  if [[ "${DRY_RUN}" == "true" || "${DRY_RUN}" == "1" || "${DRY_RUN}" == "yes" ]]; then
    cmd+=("--dry-run")
  fi
  if [[ "${ARCHIVE_BEFORE}" == "true" || "${ARCHIVE_BEFORE}" == "1" || "${ARCHIVE_BEFORE}" == "yes" ]]; then
    cmd+=("--archive-before")
  fi

  if ! "${cmd[@]}" 2>&1 | tee -a "${log_file}"; then
    echo "Run failed: ${runid}" | tee -a "${log_file}"
    failures=$((failures + 1))
  fi

  if [[ "${SLEEP_SECS}" != "0" ]]; then
    sleep "${SLEEP_SECS}"
  fi

  echo "" | tee -a "${log_file}"
done

echo "Completed with ${failures} failure(s)." | tee -a "${log_file}"
exit 0
