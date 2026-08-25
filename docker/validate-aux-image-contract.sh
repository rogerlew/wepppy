#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 <status|preflight|cap|weppcloudr|fcgiwrap> <image> <expected-revision>" >&2
  exit 2
fi

service=$1
image=$2
expected_revision=$3
contract_id="wepppy-aux-contract-${service}-$$"
network="${contract_id}-network"
container="${contract_id}-service"
redis_container="${contract_id}-redis"
secret_dir=$(mktemp -d)

cleanup() {
  docker rm -f "${container}" "${redis_container}" >/dev/null 2>&1 || true
  docker network rm "${network}" >/dev/null 2>&1 || true
  rm -rf "${secret_dir}"
}
trap cleanup EXIT

architecture=$(docker image inspect "${image}" --format '{{.Architecture}}')
runtime_user=$(docker image inspect "${image}" --format '{{.Config.User}}')
revision=$(docker image inspect "${image}" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')

[[ "${architecture}" == "amd64" ]]
[[ -n "${runtime_user}" && "${runtime_user}" != "0" && "${runtime_user}" != "root" ]]
[[ "${revision}" == "${expected_revision}" ]]

wait_for_url() {
  local url=$1
  for _ in $(seq 1 60); do
    if curl -fsS "${url}" >/dev/null; then
      return 0
    fi
    sleep 1
  done
  docker logs "${container}" >&2 || true
  return 1
}

case "${service}" in
  status|preflight)
    docker network create "${network}" >/dev/null
    docker run -d --name "${redis_container}" --network "${network}" \
      redis:8.2.1-alpine@sha256:f887e6dacdcfa8e14af2f625fdf4474ff8c37dc36ce13b9e89e6e9a901f155ad \
      redis-server --requirepass contract-only >/dev/null
    printf '%s' 'contract-only' > "${secret_dir}/redis_password"
    chmod 0444 "${secret_dir}/redis_password"
    if [[ "${service}" == "status" ]]; then
      port=9002
      prefix=STATUS
      db=2
    else
      port=9001
      prefix=PREFLIGHT
      db=0
    fi
    docker run -d --name "${container}" --network "${network}" --read-only \
      -p "127.0.0.1::${port}" \
      -v "${secret_dir}/redis_password:/run/secrets/redis_password:ro" \
      -e "${prefix}_REDIS_URL=redis://${redis_container}:6379/${db}" \
      -e "${prefix}_REDIS_PASSWORD_FILE=/run/secrets/redis_password" \
      -e "${prefix}_LISTEN_ADDR=0.0.0.0:${port}" \
      "${image}" >/dev/null
    host_port=$(docker port "${container}" "${port}/tcp" | awk -F: 'END {print $NF}')
    wait_for_url "http://127.0.0.1:${host_port}/health"
    ;;
  cap)
    "$(dirname "$0")/validate-cap-runtime-contract.sh" "${image}"
    ;;
  weppcloudr)
    fontawesome_digest=$(
      docker run --rm --network none --entrypoint sha256sum "${image}" \
        /srv/weppcloudr/vendor/fontawesome/5.3.1/all.js \
        | awk '{print $1}'
    )
    [[ "${fontawesome_digest}" == "8cb270b4d9485a93b31df98113fda8723ffc067fa7bfa90cedd47b76f7b10be1" ]]
    docker run -d --name "${container}" --read-only \
      --tmpfs /tmp:rw,nosuid,nodev \
      --tmpfs /opt/weppcloudr/renv/cache:rw,nosuid,nodev \
      -p 127.0.0.1::8050 \
      -e PORT=8050 \
      "${image}" >/dev/null
    host_port=$(docker port "${container}" 8050/tcp | awk -F: 'END {print $NF}')
    wait_for_url "http://127.0.0.1:${host_port}/healthz"
    ;;
  fcgiwrap)
    docker run --rm --network none --entrypoint /bin/sh "${image}" -lc '
      set -eu
      test "$(id -u)" = 1000
      test "$(id -g)" = 993
      test -x /usr/sbin/fcgiwrap
      test -x /usr/bin/spawn-fcgi
      test -x /usr/lib/git-core/git-http-backend
      test "$(git config --system --get safe.directory)" = "*"
    '
    ;;
  *)
    echo "unsupported service: ${service}" >&2
    exit 2
    ;;
esac

echo "${service} image contract: PASS"
