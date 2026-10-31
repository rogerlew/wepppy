#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${ROOT_DIR}/src"
RELEASE_DIR="${ROOT_DIR}/release"
COMPILER="${COMPILER:-/usr/bin/gfortran}"
LINK_FLAGS="${LINK_FLAGS:--mcmodel=medium -no-pie}"
TARGET_TAG="${TARGET_TAG:-$(date +%y%m%d)}"
OUTPUT_EXT="${OUTPUT_EXT:-}"
HILL_LABEL="${HILL_LABEL:-hill}"
SOURCE_BRANCH="${SOURCE_BRANCH:-$(git -C "${ROOT_DIR}" branch --show-current)}"
SOURCE_COMMIT="${SOURCE_COMMIT:-$(git -C "${ROOT_DIR}" rev-parse HEAD)}"

if [[ ! -x "${COMPILER}" ]]; then
  echo "error: compiler not executable: ${COMPILER}" >&2
  exit 1
fi

echo "Building WEPP dated release tag: ${TARGET_TAG}"
echo "Compiler: ${COMPILER}"
echo "Link flags: ${LINK_FLAGS}"
echo "Output extension: ${OUTPUT_EXT}"
echo "Hill label: ${HILL_LABEL}"
echo "Source branch: ${SOURCE_BRANCH}"
echo "Source commit: ${SOURCE_COMMIT}"

pushd "${SRC_DIR}" >/dev/null
make clean
# Build sequentially to avoid include-copy race conditions.
make -B \
  COMPILER=gfortran \
  FC="${COMPILER}" \
  LINKER="${COMPILER}" \
  LDFLAGS="${LINK_FLAGS}" \
  wepp
make -B \
  COMPILER=gfortran \
  FC="${COMPILER}" \
  LINKER="${COMPILER}" \
  LDFLAGS="${LINK_FLAGS}" \
  wepp_hill
popd >/dev/null

WATERSHED_OUT="${RELEASE_DIR}/wepp_${TARGET_TAG}${OUTPUT_EXT}"
HILL_OUT="${RELEASE_DIR}/wepp_${TARGET_TAG}_${HILL_LABEL}${OUTPUT_EXT}"

install -m 0755 "${SRC_DIR}/wepp" "${WATERSHED_OUT}"
install -m 0755 "${SRC_DIR}/wepp_hill" "${HILL_OUT}"

python3 "${ROOT_DIR}/tools/generate_wepp_release_sidecar.py" \
  --binary "${WATERSHED_OUT}" \
  --binary-role watershed \
  --release-tag "${TARGET_TAG}" \
  --source-branch "${SOURCE_BRANCH}" \
  --source-commit "${SOURCE_COMMIT}" \
  --pass-components-version 3 \
  --mofe-supported --single-user-defined-inputs-supported
python3 "${ROOT_DIR}/tools/generate_wepp_release_sidecar.py" \
  --binary "${HILL_OUT}" \
  --binary-role hillslope \
  --release-tag "${TARGET_TAG}" \
  --source-branch "${SOURCE_BRANCH}" \
  --source-commit "${SOURCE_COMMIT}" \
  --pass-components-version 3 \
  --mofe-supported --single-user-defined-inputs-supported

for bin in "${WATERSHED_OUT}" "${HILL_OUT}"; do
  echo
  echo "== $(basename "${bin}") =="
  sha256sum "${bin}"
  readelf -p .comment "${bin}" | sed -n '1,120p'
  ldd "${bin}" | sed -n '1,120p' || true

  if readelf -p .comment "${bin}" | grep -Eqi 'Intel\(R\)'; then
    echo "error: Intel toolchain marker detected in ${bin}" >&2
    exit 1
  fi

  if strings "${bin}" | grep -Eq 'for_diags_intel\.c|Intel\(R\) oneAPI|__intel_'; then
    echo "error: Intel runtime fingerprint detected in ${bin}" >&2
    exit 1
  fi
done

echo
echo "Build complete:"
echo "  ${WATERSHED_OUT}"
echo "  ${HILL_OUT}"
