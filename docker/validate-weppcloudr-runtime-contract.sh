#!/bin/bash
set -euo pipefail

IMAGE="${1:-}"
WORKER_IMAGE="${2:-}"
if [ -z "${IMAGE}" ]; then
    echo "usage: $0 <candidate-weppcloudr-image>" >&2
    exit 2
fi
command -v docker >/dev/null 2>&1 || {
    echo "weppcloudr-runtime-contract: docker is required" >&2
    exit 2
}

docker image inspect "${IMAGE}" >/dev/null
docker run --rm --network none --entrypoint /bin/sh "${IMAGE}" -ec '
    test -r /srv/weppcloudr/render-compose-request.R
    test -r /srv/weppcloudr/render-request-v1.R
    test -x /srv/weppcloudr/publish_fenced.py
    test -s /srv/weppcloudr/compose-protocol-version
    Rscript -e '\''parse(file="/srv/weppcloudr/render-compose-request.R"); parse(file="/srv/weppcloudr/render-request-v1.R")'\'' >/dev/null
    python3 -m py_compile /srv/weppcloudr/publish_fenced.py
'
PROBE_RECEIPT="$(printf '%s' '{"run_path":"/wc1/runs/contract","runid":"contract","config":"disturbed9002","skip_cache":true,"fencing_generation":1}' \
    | docker run --rm -i --network none -e WEPPCLOUDR_CONTRACT_PROBE=1 \
        --entrypoint Rscript "${IMAGE}" /srv/weppcloudr/render-compose-request.R)"
[ "${PROBE_RECEIPT}" = '{"protocol":1,"accepted":true}' ] || {
    echo "weppcloudr-runtime-contract: request/receipt protocol probe failed" >&2
    exit 1
}
if [ -n "${WORKER_IMAGE}" ]; then
    docker image inspect "${WORKER_IMAGE}" >/dev/null
    RENDERER_PROTOCOL="$(docker run --rm --network none --entrypoint cat "${IMAGE}" /srv/weppcloudr/compose-protocol-version)"
    WORKER_PROTOCOL="$(docker run --rm --network none --entrypoint cat "${WORKER_IMAGE}" /workdir/wepppy/weppcloudR/compose-protocol-version)"
    [ "${RENDERER_PROTOCOL}" = "${WORKER_PROTOCOL}" ] || {
        echo "weppcloudr-runtime-contract: worker/renderer protocol mismatch (${WORKER_PROTOCOL} != ${RENDERER_PROTOCOL})" >&2
        exit 1
    }
    docker run --rm --network none --entrypoint /bin/sh "${WORKER_IMAGE}" -ec '
        grep -Fq /srv/weppcloudr/render-compose-request.R /workdir/wepppy/wepppy/rq/weppcloudr_backends.py
    '
    # Exercise the actual filesystem boundary with legacy owner-only run data.
    # Script parsing and group membership alone did not catch the errno-13 regression.
    WORKER_IDENTITY="$(docker run --rm --network none --entrypoint python "${WORKER_IMAGE}" \
        -c 'import os; print(f"{os.geteuid()}:{os.getegid()}")')"
    PROBE_DIR="$(mktemp -d /tmp/weppcloudr-identity.XXXXXXXX)"
    cleanup_identity_probe() {
        docker run --rm --network none --user "${WORKER_IDENTITY}" \
            -v "${PROBE_DIR}:/probe" --entrypoint python "${WORKER_IMAGE}" \
            -c 'import shutil; shutil.rmtree("/probe/owned", ignore_errors=True)'
        rmdir "${PROBE_DIR}"
    }
    trap cleanup_identity_probe EXIT
    chmod 1777 "${PROBE_DIR}"
    docker run --rm --network none -v "${PROBE_DIR}:/probe" \
        --entrypoint python "${WORKER_IMAGE}" -c '
import os
import pyarrow as pa
import pyarrow.parquet as pq
os.umask(0o077)
os.mkdir("/probe/owned")
pq.write_table(pa.table({"runoff": [1.0, 2.0]}), "/probe/owned/input.parquet")
assert os.stat("/probe/owned/input.parquet").st_mode & 0o777 == 0o600
'
    docker run --rm --network none --user "${WORKER_IDENTITY}" \
        -v "${PROBE_DIR}:/probe" --entrypoint Rscript "${IMAGE}" -e '
input <- arrow::read_parquet("/probe/owned/input.parquet")
stopifnot(sum(input$runoff) == 3)
writeLines("worker-renderer access passed", "/probe/owned/output.txt")
'
    docker run --rm --network none -v "${PROBE_DIR}:/probe" \
        --entrypoint python "${WORKER_IMAGE}" -c '
from pathlib import Path
assert Path("/probe/owned/output.txt").read_text().strip() == "worker-renderer access passed"
assert Path("/probe/owned/input.parquet").stat().st_mode & 0o777 == 0o600
'
    cleanup_identity_probe
    trap - EXIT
    echo "weppcloudr-runtime-contract: owner-only data sharing passed as ${WORKER_IDENTITY}"
fi
echo "weppcloudr-runtime-contract: compatible image=${IMAGE}"
