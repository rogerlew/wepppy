#!/usr/bin/env bash
set -euo pipefail

fixture_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$fixture_dir/../../../../.." && pwd)
binary=${WEPP_PHASE1_BINARY:-$repo_root/wepp_runner/bin/wepp_260803}

exec "$repo_root/.venv/bin/python" "$repo_root/tools/peakflow_phase1_fixture.py" \
  "$fixture_dir" --binary "$binary"
