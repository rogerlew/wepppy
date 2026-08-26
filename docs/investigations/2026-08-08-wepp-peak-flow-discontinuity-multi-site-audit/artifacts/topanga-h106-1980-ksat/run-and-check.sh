#!/usr/bin/env bash
set -euo pipefail

fixture_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$fixture_dir/../../../../.." && pwd)
observer_binary=${WEPP_GATE21_OBSERVER_BINARY:?set WEPP_GATE21_OBSERVER_BINARY to the ea25ad79 observer build}
replay_binary=${WEPP_GATE21_REPLAY_BINARY:?set WEPP_GATE21_REPLAY_BINARY to the standalone replay build}
phase1_artifacts="$repo_root/docs/work-packages/20260808_peakflow_phase1/artifacts"
fixture_1986="$repo_root/docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/openwepp-hill106-effective-duration-reproducer"

exec "$repo_root/.venv/bin/python" "$repo_root/tools/peakflow_gate21_acceptance.py" \
  --fixture "$fixture_dir" \
  --fixture-1986 "$fixture_1986" \
  --observer-binary "$observer_binary" \
  --observer-manifest "$phase1_artifacts/observer-build-manifest.json" \
  --replay-binary "$replay_binary" \
  --replay-manifest "$phase1_artifacts/replay-build-manifest.json" \
  --artifacts "$phase1_artifacts"
