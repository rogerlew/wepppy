#!/bin/bash
# Run before activating the exact candidate image; never touch a live project.
set -euo pipefail
candidate_image="${1:?usage: validate-parquet-csv-runtime-contract.sh IMAGE [UID:GID]}"
runtime_user="${2:-}"
identity_args=()
if [ -n "${runtime_user}" ]; then
    identity_args=(--user "${runtime_user}")
fi
probe_root="$(mktemp -d)"
trap 'rm -rf -- "${probe_root}"' EXIT
chmod 0755 "${probe_root}"
mkdir -p "${probe_root}/cs/csv-readiness" "${probe_root}/cs/csv-private"
docker run --rm --network none "${identity_args[@]}" --entrypoint /bin/cat \
    "${candidate_image}" /opt/parquet-csv/readiness.parquet > "${probe_root}/cs/csv-readiness/table.parquet"
cp "${probe_root}/cs/csv-readiness/table.parquet" "${probe_root}/cs/csv-private/table.parquet"
touch "${probe_root}/cs/csv-readiness/PUBLIC"
# Fixtures are public synthetic inputs, readable under a different runtime UID
# even when the operator invokes this preflight with umask 077.
chmod 0755 "${probe_root}/cs" "${probe_root}/cs/csv-readiness" "${probe_root}/cs/csv-private"
chmod 0644 "${probe_root}/cs/csv-readiness/table.parquet" "${probe_root}/cs/csv-readiness/PUBLIC" "${probe_root}/cs/csv-private/table.parquet"
docker run --rm --network none "${identity_args[@]}" \
    --entrypoint /opt/venv/bin/python "${candidate_image}" \
    -B -m wepppy.microservices.parquet_csv.preflight
docker run --rm --network none "${identity_args[@]}" --ulimit nofile=1000000:1000000 \
    --mount "type=bind,src=${probe_root},dst=/wc1/runs,readonly" \
    --entrypoint /opt/venv/bin/python "${candidate_image}" \
    -B /workdir/wepppy/tools/parquet_csv_cli/http_preflight.py
