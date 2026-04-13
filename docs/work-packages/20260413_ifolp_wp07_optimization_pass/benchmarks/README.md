# WP-07 Benchmark Artifacts

This directory captures reproducible baseline and post-change IFOLP benchmark evidence for WP-07.

## Fixture Set
Benchmarks ran against staged run-root fixtures from:
- `/tmp/ifolp_wp05_remediate/run1/manifests/fixture-manifest.json`

Fixtures:
- `blackwood_60_5`
- `clueless_aftertaste_anchor_10_100`
- `gatecreek_10m_30_2`

Each fixture was executed **5 repeats** for baseline and post-change runs.

## Files
- `baseline_timings.tsv`: per-repeat wall-clock seconds before optimization changes.
- `post_timings.tsv`: per-repeat wall-clock seconds after optimization changes.
- `baseline_summary.tsv`: mean/min/max summary derived from baseline repeats.
- `post_summary.tsv`: mean/min/max summary derived from post-change repeats.
- `benchmark_comparison.tsv`: baseline vs post mean deltas by fixture.

## Command Pattern
The benchmark loop used `/usr/bin/time` around:

```bash
/workdir/weppcloud-wbt/target/release/whitebox_tools \
  -r=IterativeFirstOrderLinkPrune \
  --wd=/tmp/ifolp_wp05_remediate/run1/ \
  --d8_pntr=<absolute fixture d8 path> \
  --upstream_area=<absolute fixture upstream area path> \
  --output=<tmp output path> \
  --csa=<fixture csa> \
  --mscl=<fixture mscl>
```

The same command form was used for baseline and post-change captures.
