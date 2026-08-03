#!/usr/bin/env bash
set -euo pipefail

fixture_root="${1:-/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes}"
repo_root="/workdir/wepppy"
binary_name="wepp_260803_hill"

mkdir -p \
  "$fixture_root/bin" \
  "$fixture_root/burned/wepp/runs" \
  "$fixture_root/burned/wepp/output" \
  "$fixture_root/undisturbed/wepp/runs" \
  "$fixture_root/undisturbed/wepp/output"

install -m 0755 \
  "$repo_root/wepp_runner/bin/$binary_name" \
  "$fixture_root/bin/$binary_name"
install -m 0644 \
  "$repo_root/wepp_runner/bin/$binary_name.json" \
  "$fixture_root/bin/$binary_name.json"

stage_scenario() {
  local production_run="$1"
  local scenario="$2"
  local destination="$fixture_root/$scenario/wepp/runs/"

  rsync -aH --prune-empty-dirs \
    --exclude='p*.err' \
    --include='p49.*' \
    --include='p5[0-9].*' \
    --include='p6[0-1].*' \
    --include='gwcoeff.txt' \
    --include='snow.txt' \
    --include='pmetpara.txt' \
    --include='wepp_ui.txt' \
    --include='chntyp.txt' \
    --include='tc.txt' \
    --include='chan.inp' \
    --exclude='*' \
    "wepp1:/geodata/wc1/runs/$production_run/wepp/runs/" \
    "$destination"
}

stage_scenario "ca/callable-shred" "burned"
stage_scenario "st/stabilized-housecleaning" "undisturbed"

for scenario in burned undisturbed; do
  runs_dir="$fixture_root/$scenario/wepp/runs"
  for hillslope_id in $(seq 49 61); do
    for extension in run man slp cli sol; do
      test -s "$runs_dir/p${hillslope_id}.${extension}"
    done

    # Production line 17 disables large-graphics output. That output is the
    # WEPP contract carrying full-depth, layer-by-layer daily soil water.
    run_file="$runs_dir/p${hillslope_id}.run"
    if [[ "$(sed -n '17p' "$run_file")" == "No" ]]; then
      sed -i "17cYes\n../output/H${hillslope_id}.grph.dat" "$run_file"
    fi
    [[ "$(sed -n '17p' "$run_file")" == "Yes" ]]
    [[ "$(sed -n '18p' "$run_file")" == "../output/H${hillslope_id}.grph.dat" ]]
  done
  for sidecar in \
    gwcoeff.txt snow.txt pmetpara.txt wepp_ui.txt chntyp.txt tc.txt chan.inp
  do
    test -e "$runs_dir/$sidecar"
  done
done

"$repo_root/.venv/bin/python" \
  "$repo_root/docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/add_high_severity_hillslope_fixture.py" \
  "$fixture_root"

echo "Hillslope fixtures staged at $fixture_root"
echo "Binary: $fixture_root/bin/$binary_name"
