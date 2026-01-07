#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR_ROOT="$(cd "${ROOT_DIR}/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON="${VENV_DIR}/bin/python"
ENV_FILE="${ROOT_DIR}/.vscode/.env"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found; install uv to build the host .venv." >&2
  exit 1
fi

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
else
  mkdir -p "$(dirname "${ENV_FILE}")"
  cat > "${ENV_FILE}" <<'EOF'
GDAL_CONFIG=/usr/bin/gdal-config
LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu
EOF
fi

if [[ ! -x "${PYTHON}" ]]; then
  uv venv -p 3.12 "${VENV_DIR}"
fi

GDAL_CONFIG="${GDAL_CONFIG:-/usr/bin/gdal-config}"
LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-/usr/lib/x86_64-linux-gnu}"
PATH="/usr/bin:${PATH}"

uv pip install -p "${PYTHON}" \
  -r "${ROOT_DIR}/docker/requirements-uv.txt" \
  -r "${ROOT_DIR}/docker/requirements-stubs-uv.txt" \
  --overrides "${ROOT_DIR}/docker/requirements-uv-host-overrides.txt"

SITE_PACKAGES="$("${PYTHON}" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"

PTH_ENTRIES=(
  "wepppy.pth:${WORKDIR_ROOT}/wepppy/"
  "cao.pth:${WORKDIR_ROOT}/wepppy/services/cao/src/"
  "wepp_runner.pth:${WORKDIR_ROOT}/wepppy2/"
  "weppcloud2.pth:${WORKDIR_ROOT}/weppcloud2/"
  "wbt.pth:${WORKDIR_ROOT}/weppcloud-wbt/WBT/"
  "f_esri.pth:${WORKDIR_ROOT}/f-esri/"
  "wepppyo3.pth:${WORKDIR_ROOT}/wepppyo3/release/linux/py312/"
)

for entry in "${PTH_ENTRIES[@]}"; do
  name="${entry%%:*}"
  path="${entry#*:}"
  printf '%s\n' "${path}" > "${SITE_PACKAGES}/${name}"
done

echo "Host .venv ready at ${VENV_DIR}"
