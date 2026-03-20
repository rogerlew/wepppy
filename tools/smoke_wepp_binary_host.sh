#!/usr/bin/env bash
set -euo pipefail

RUNS_DIR="${RUNS_DIR:-/wc1/runs/du/dumbfounded-patentee/wepp/runs}"
CASES="${CASES:-p962,p1}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <binary-path-on-host>" >&2
  exit 2
fi

BINARY_PATH="$(readlink -f "$1")"

if [[ ! -x "${BINARY_PATH}" ]]; then
  echo "error: binary is not executable: ${BINARY_PATH}" >&2
  exit 1
fi

IFS=',' read -r -a case_list <<<"${CASES}"
overall_status=0

required_suffixes=(
  ".run"
  ".man"
  ".slp"
  ".cli"
  ".sol"
)

required_shared_files=(
  "chan.inp"
  "chntyp.txt"
  "gwcoeff.txt"
  "pmetpara.txt"
  "snow.txt"
  "wepp_ui.txt"
)

for case_id in "${case_list[@]}"; do
  for suffix in "${required_suffixes[@]}"; do
    path="${RUNS_DIR}/${case_id}${suffix}"
    if [[ ! -f "${path}" ]]; then
      echo "error: missing fixture file: ${path}" >&2
      overall_status=1
    fi
  done

  for shared in "${required_shared_files[@]}"; do
    path="${RUNS_DIR}/${shared}"
    if [[ ! -f "${path}" ]]; then
      echo "error: missing fixture file: ${path}" >&2
      overall_status=1
    fi
  done
done

if [[ "${overall_status}" -ne 0 ]]; then
  exit "${overall_status}"
fi

for case_id in "${case_list[@]}"; do
  work_dir="$(mktemp -d "/tmp/${case_id}_host_smoke_XXXXXX")"
  mkdir -p "${work_dir}/runs" "${work_dir}/output"

  for f in \
    "${case_id}.run" \
    "${case_id}.man" \
    "${case_id}.slp" \
    "${case_id}.cli" \
    "${case_id}.sol" \
    chan.inp \
    chntyp.txt \
    gwcoeff.txt \
    pmetpara.txt \
    snow.txt \
    wepp_ui.txt
  do
    cp "${RUNS_DIR}/${f}" "${work_dir}/runs/"
  done

  set +e
  (
    cd "${work_dir}/runs"
    timeout "${TIMEOUT_SECONDS}" "${BINARY_PATH}" < "${case_id}.run" > "${work_dir}/stdout.log" 2> "${work_dir}/stderr.log"
  )
  rc=$?
  set -e

  years="$(grep -E 'SIMULATION YEAR[[:space:]]*=' "${work_dir}/stdout.log" | sed -E 's/.*=[[:space:]]*([0-9]+).*/\1/' | tr '\n' ' ' | sed 's/ $//')"
  success_count="$(grep -c 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' "${work_dir}/stdout.log" || true)"
  last_line="$(grep -v '^$' "${work_dir}/stdout.log" | tail -n 1 || true)"

  printf "%s\trc=%s\tsuccess=%s\tyears=[%s]\tlast=%s\twd=%s\n" \
    "${case_id}" "${rc}" "${success_count}" "${years}" "${last_line}" "${work_dir}"

  if [[ "${rc}" -ne 0 ]] || [[ "${success_count}" -lt 1 ]]; then
    overall_status=1
  fi

  if ! grep -q 'SIMULATION YEAR = *17' "${work_dir}/stdout.log"; then
    overall_status=1
  fi
done

exit "${overall_status}"
