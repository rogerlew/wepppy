# MOFE Segmentation Benchmark (pointy-toed-fluff)

- Source run: `/wc1/runs/po/pointy-toed-fluff`
- Source slope files per sample: `3345`
- Isolation: each sample executed in its own temp working directory; source run files were never modified.
- Alternation pattern: old/new across 10 samples (5 old, 5 new).
- Parameters:
  - `target_length=60.0`
  - `buffer_length=30.0`
  - `max_ofes=19`

## Per-Run Timings

| Sample | Mode | Elapsed (s) | Files |
| --- | --- | ---: | ---: |
| 1 | old | 2.186575 | 3345 |
| 2 | new | 0.967019 | 3345 |
| 3 | old | 2.136804 | 3345 |
| 4 | new | 0.937504 | 3345 |
| 5 | old | 2.152559 | 3345 |
| 6 | new | 0.952568 | 3345 |
| 7 | old | 2.162081 | 3345 |
| 8 | new | 0.934187 | 3345 |
| 9 | old | 2.104486 | 3345 |
| 10 | new | 0.900596 | 3345 |

## Aggregate Stats

| Metric | Old | New |
| --- | ---: | ---: |
| Mean (s) | 2.148501 | 0.938375 |
| Stddev (s) | 0.030515 | 0.024837 |

- Percent delta (`new` vs `old`): `-56.32%`

Raw machine-readable data: `artifacts/benchmark_raw.json`
