#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

OUTPUT_DIR="${ROOT_DIR}/coverage/npm"

echo "==> Preparing npm coverage workspace"
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

echo "==> Installing npm dependencies"
wctl run-npm install

echo "==> Running Jest tests with coverage"
COVERAGE_DIRECTORY="${OUTPUT_DIR}" \
  wctl run-npm test -- --coverage --coverageDirectory="${OUTPUT_DIR}" --coverageReporters=text --coverageReporters=lcov

echo "==> NPM coverage artifacts stored under ${OUTPUT_DIR}"
