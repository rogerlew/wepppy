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
fi
echo "weppcloudr-runtime-contract: compatible image=${IMAGE}"
