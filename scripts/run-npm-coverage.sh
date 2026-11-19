#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"
OUTPUT_DIR="${ROOT_DIR}/coverage/npm"

echo "==> Preparing npm coverage workspace"
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

echo "==> Installing locked npm dependencies"
wctl run-npm ci --legacy-peer-deps

echo "==> Running Jest tests with V8 coverage"
# Pass coverage options to Jest itself. npm test also chains Node's test runner;
# appending flags to that script sends them to Node instead of enabling coverage.
NODE_OPTIONS=--experimental-vm-modules wctl run-npm exec -- jest \
  --config="${ROOT_DIR}/wepppy/weppcloud/static-src/jest.config.mjs" \
  --coverage --coverageProvider=v8 --coverageDirectory="${OUTPUT_DIR}" \
  --coverageReporters=text --coverageReporters=lcov
wctl run-npm exec -- node --test "${ROOT_DIR}"/wepppy/weppcloud/static-src/tests/node/*.test.mjs
test -s "${OUTPUT_DIR}/lcov.info"
echo "==> NPM coverage artifacts stored under ${OUTPUT_DIR}"
