#!/usr/bin/env bash
set -euo pipefail

fixture_root="${FIXTURE_ROOT:-/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes}"
binary="$fixture_root/bin/wepp_260803_hill"
scenario_filter="${1:-all}"
hillslope_filter="${2:-all}"

test -x "$binary"
test -s "$binary.json"

if [[ "$scenario_filter" == "all" ]]; then
  scenarios=(burned undisturbed high_severity)
else
  scenarios=("$scenario_filter")
fi

if [[ "$hillslope_filter" == "all" ]]; then
  hillslope_ids=($(seq 49 61))
else
  hillslope_ids=("$hillslope_filter")
fi

for scenario in "${scenarios[@]}"; do
  runs_dir="$fixture_root/$scenario/wepp/runs"
  output_dir="$fixture_root/$scenario/wepp/output"
  test -d "$runs_dir"
  mkdir -p "$output_dir"

  for sidecar in \
    gwcoeff.txt snow.txt pmetpara.txt wepp_ui.txt chntyp.txt tc.txt chan.inp
  do
    test -e "$runs_dir/$sidecar"
  done

  for hillslope_id in "${hillslope_ids[@]}"; do
    run_file="p${hillslope_id}.run"
    stderr_file="p${hillslope_id}.wepp_260803_hill.stderr.log"
    test -s "$runs_dir/$run_file"

    echo "Running $scenario H$hillslope_id"
    (
      cd "$runs_dir"
      "$binary" < "$run_file" > /dev/null 2> "$stderr_file"
    )

    water_file="$output_dir/H${hillslope_id}.wat.dat"
    graphics_file="$output_dir/H${hillslope_id}.grph.dat"
    test -s "$water_file"
    test -s "$graphics_file"
    grep -q 'SoilWaterTotal=Full-profile soil water (mm)' "$water_file"
    grep -q 'ProfileFCStore=Full-profile field capacity storage (mm)' "$water_file"
    grep -q '{Soil water in layer 10 (mm)}' "$graphics_file"
  done
done

echo "Requested wepp_260803 hillslope replays completed"
