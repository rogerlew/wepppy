# MOFE Map Assignment Benchmark

- Source run: `/wc1/runs/po/pointy-toed-fluff`
- Comparison subset: first `200` hillslope ids with `.mofe.slp` files and subwta coverage
- Raster shape: `(3103, 3031)`
- Isolation: each sample executed with in-memory array copies and wrote output to a unique temp directory.
- Alternation pattern: old/new across `6` samples (3 old, 3 new).

## Per-Run Timings

| Sample | Mode | Elapsed (s) | Temp Dir |
| --- | --- | ---: | --- |
| 1 | old | 76.935823 | `/tmp/mofe-map-bench-old-01-v24n3qc9` |
| 2 | new | 0.296297 | `/tmp/mofe-map-bench-new-02-uy_af3zv` |
| 3 | old | 65.073763 | `/tmp/mofe-map-bench-old-03-ay_r6rz0` |
| 4 | new | 0.282671 | `/tmp/mofe-map-bench-new-04-92bc87et` |
| 5 | old | 55.838639 | `/tmp/mofe-map-bench-old-05-rdt31bs5` |
| 6 | new | 0.268094 | `/tmp/mofe-map-bench-new-06-067z884t` |

## Aggregate Stats

| Metric | Old | New |
| --- | ---: | ---: |
| Mean (s) | 65.949408 | 0.282354 |
| Stddev (s) | 10.575815 | 0.014104 |

- Percent delta (`new` vs `old`): `-99.57%`

Raw machine-readable data: `artifacts/benchmark_raw.json`
