#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FOREST_DIR="${FOREST_DIR:-/workdir/wepp-forest}"
FOREST_BUILD_SCRIPT="${FOREST_DIR}/tools/build_wepp_260319_pinned.sh"
TARGET_TAG="${TARGET_TAG:-260319}"
COMPILER="${COMPILER:-/usr/bin/gfortran}"
CONTAINER="${CONTAINER:-weppcloud}"

if [[ ! -x "${FOREST_BUILD_SCRIPT}" ]]; then
  echo "error: missing build script: ${FOREST_BUILD_SCRIPT}" >&2
  exit 1
fi

echo "Rebuilding wepp_${TARGET_TAG} binaries from ${FOREST_DIR} using ${COMPILER}"
COMPILER="${COMPILER}" TARGET_TAG="${TARGET_TAG}" "${FOREST_BUILD_SCRIPT}"

src_wepp="${FOREST_DIR}/release/wepp_${TARGET_TAG}"
src_hill="${FOREST_DIR}/release/wepp_${TARGET_TAG}_hill"
dst_wepp="${ROOT_DIR}/wepp_runner/bin/wepp_${TARGET_TAG}"
dst_hill="${ROOT_DIR}/wepp_runner/bin/wepp_${TARGET_TAG}_hill"

install -m 0755 "${src_wepp}" "${dst_wepp}"
install -m 0755 "${src_hill}" "${dst_hill}"

echo
echo "Running provenance checks"
"${ROOT_DIR}/tools/check_wepp_binary_provenance.sh" "${dst_wepp}" "${dst_hill}"

echo
echo "Running container smoke checks in ${CONTAINER}"
CONTAINER="${CONTAINER}" "${ROOT_DIR}/tools/smoke_wepp_binary_in_container.sh" "${dst_hill}"
CONTAINER="${CONTAINER}" "${ROOT_DIR}/tools/smoke_wepp_binary_in_container.sh" "${dst_wepp}"

echo
echo "Vendor refresh complete:"
echo "  ${dst_wepp}"
echo "  ${dst_hill}"
