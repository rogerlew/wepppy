# Landuse/Disturbed Lane Benchmark Summary

- Generated (UTC): 2026-04-25T01:08:03+00:00
- Iterations per mode: 5

| Lane | Run | Baseline Mean (s) | Baseline Std (s) | Optimized Mean (s) | Optimized Std (s) | Delta % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `lane1_build_managements_consolidation` | `apprehensive-caw-simulated` | 0.090497 | 0.000112 | 0.030287 | 0.000073 | -66.53% |
| `lane2_logging_compaction` | `apprehensive-caw-simulated` | 0.037720 | 0.048786 | 0.014890 | 0.000949 | -60.52% |
| `lane3_pair_count_reuse_guard` | `apprehensive-caw-simulated` | 0.040698 | 0.000214 | 0.020612 | 0.000190 | -49.35% |

Lane-specific notes:
- `lane1_build_managements_consolidation` baseline: Legacy duplicate rebuild chain emulation
- `lane1_build_managements_consolidation` optimized: Deferred remap rebuilds + one final build
- `lane2_logging_compaction` baseline: Verbose-info emulation (debug routed to info)
- `lane2_logging_compaction` optimized: Compact INFO summaries with DEBUG detail
- `lane2_logging_compaction` info-log count: baseline=12008 optimized=6
- `lane3_pair_count_reuse_guard` baseline: Forced pair-count miss between consecutive passes
- `lane3_pair_count_reuse_guard` optimized: Guarded same-cycle reuse
- `lane3_pair_count_reuse_guard` pair-count calls: baseline=2 optimized=1

Raw machine-readable data: `artifacts/lane_benchmark_raw.json`
