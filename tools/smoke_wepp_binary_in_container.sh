#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${CONTAINER:-weppcloud}"
RUNS_DIR="${RUNS_DIR:-/wc1/runs/du/dumbfounded-patentee/wepp/runs}"
CASES="${CASES:-p962,p1}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <binary-path-inside-container>" >&2
  exit 2
fi

BINARY_PATH="$1"

docker exec -i \
  -e BIN="${BINARY_PATH}" \
  -e RUNSRC="${RUNS_DIR}" \
  -e CASES="${CASES}" \
  -e TIMEOUT_SECONDS="${TIMEOUT_SECONDS}" \
  "${CONTAINER}" \
  bash -s <<'EOF'
set -euo pipefail

if [[ ! -x "${BIN}" ]]; then
  echo "error: binary is not executable in container: ${BIN}" >&2
  exit 1
fi

IFS=',' read -r -a case_list <<<"${CASES}"
overall_status=0

for case_id in "${case_list[@]}"; do
  work_dir="$(mktemp -d "/tmp/${case_id}_smoke_XXXXXX")"
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
    cp "${RUNSRC}/${f}" "${work_dir}/runs/"
  done

  set +e
  (
    cd "${work_dir}/runs"
    timeout "${TIMEOUT_SECONDS}" "${BIN}" < "${case_id}.run" > "${work_dir}/stdout.log" 2> "${work_dir}/stderr.log"
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
EOF
