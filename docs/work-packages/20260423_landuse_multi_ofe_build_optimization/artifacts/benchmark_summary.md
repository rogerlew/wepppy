# Landuse Multi-OFE Build Benchmark Summary

- Generated (UTC): 2026-04-23T19:50:22+00:00
- Iterations per mode: 1
- Baseline mode: legacy orchestration emulation (`build_managements` -> `_build_multiple_ofe` -> `build_managements`).
- Optimized mode: current orchestration (`domlc_mofe_d=None` -> `_build_multiple_ofe` -> `build_managements`).

| Run | Baseline Mean (s) | Baseline Std (s) | Optimized Mean (s) | Optimized Std (s) | Delta % |
| --- | ---: | ---: | ---: | ---: | ---: |
| `moth-eaten-blackhead` | 5.126638 | 0.000000 | 5.137338 | 0.000000 | 0.21% |
| `objectionable-sublimate` | 4.741975 | 0.000000 | 4.694615 | 0.000000 | -1.00% |
| `cochlear-beriberi` | 5.835570 | 0.000000 | 5.649574 | 0.000000 | -3.19% |
| `ordained-incentive` | 5.826086 | 0.000000 | 5.401972 | 0.000000 | -7.28% |
| `uninsured-deformation` | 4.778201 | 0.000000 | 4.731373 | 0.000000 | -0.98% |

Raw machine-readable data: `artifacts/benchmark_raw.json`
