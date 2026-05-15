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

infer_pass_family() {
  local binary_path="$1"
  local sidecar_path="${binary_path}.json"
  if [[ ! -f "${sidecar_path}" ]]; then
    echo "legacy_ascii"
    return 0
  fi

  python3 - "$sidecar_path" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    payload = json.load(fh)

features = payload.get("features")
if not isinstance(features, dict):
    raise SystemExit(f"invalid sidecar: missing features object: {path}")
hbp_supported = features.get("hbp_supported")
if not isinstance(hbp_supported, bool):
    raise SystemExit(f"invalid sidecar: features.hbp_supported must be boolean: {path}")
mode2_prompt_required = features.get("mode2_master_pass_prompt_required")
if not isinstance(mode2_prompt_required, bool):
    raise SystemExit(
        f"invalid sidecar: features.mode2_master_pass_prompt_required must be boolean: {path}"
    )

if hbp_supported:
    print("hbp")
else:
    print("legacy_ascii")
PY
}

adapt_run_file_for_pass_family() {
  local run_file="$1"
  local pass_family="$2"
  if [[ "${pass_family}" != "hbp" ]]; then
    return 0
  fi
  # HBP-capable releases require process pass names to be H*.hbp.
  sed -i 's/\.pass\.dat/.hbp/g' "${run_file}"
}

PASS_FAMILY="$(infer_pass_family "${BINARY_PATH}")"
echo "pass_family=${PASS_FAMILY} (inferred from ${BINARY_PATH}.json when present)"

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

  adapt_run_file_for_pass_family "${work_dir}/runs/${case_id}.run" "${PASS_FAMILY}"

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
