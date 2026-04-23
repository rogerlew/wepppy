# MOFE `.mofe.man` Synthesis Benchmark

- Generated (UTC): 2026-04-23T18:30:33+00:00
- Baseline mode: forced sequential (`cpu_count=1`), matching pre-migration single-process behavior.
- Concurrent mode: canonical process-pool path (`cpu_count=4`), matching the bounded MOFE synthesis worker cap in production.
- Iterations per mode: 3

| Run | Baseline Mean (s) | Baseline Std (s) | Concurrent Mean (s) | Concurrent Std (s) | Delta % | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `moth-eaten-blackhead` | 2.189896 | 0.115061 | 5.325303 | 0.228807 | 143.18% | match |
| `objectionable-sublimate` | 0.874813 | 0.003296 | 4.754715 | 0.041067 | 443.51% | synthetic single-OFE MOFE map |
| `cochlear-beriberi` | 4.285387 | 0.295896 | 5.744411 | 0.179908 | 34.05% | match |
| `ordained-incentive` | 3.418026 | 0.042330 | 5.591124 | 0.121779 | 63.58% | match |
| `uninsured-deformation` | 1.239582 | 0.040714 | 4.789036 | 0.152450 | 286.34% | match |

Raw machine-readable data: `artifacts/benchmark_raw.json`
