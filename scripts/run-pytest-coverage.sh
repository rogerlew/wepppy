#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "==> Preparing coverage workspace"
rm -rf coverage
mkdir -p coverage

echo "==> Running pytest with coverage reporting"
wctl run-pytest --cov=wepppy --cov-report=term-missing --cov-report=xml:coverage/coverage.xml

if [[ -f ".coverage" ]]; then
  mv .coverage coverage/.coverage
fi

echo "==> Coverage artifacts stored under ${ROOT_DIR}/coverage"
