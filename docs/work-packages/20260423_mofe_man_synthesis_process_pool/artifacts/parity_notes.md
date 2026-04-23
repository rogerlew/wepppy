# MOFE `.mofe.man` Synthesis Parity Notes

- Generated (UTC): 2026-04-23T18:30:33+00:00
- Baseline mode: forced sequential (`cpu_count=1`), used as the pre-migration parity oracle.
- Concurrent mode: canonical process-pool path (`cpu_count=4`), matching the bounded MOFE synthesis worker cap in production.

| Run | Files (Baseline/Concurrent) | Mismatches | Synthetic MOFE Adaptation | Status |
| --- | ---: | ---: | :---: | --- |
| `moth-eaten-blackhead` | 209/209 | 0 | no | match |
| `objectionable-sublimate` | 60/60 | 0 | yes | match |
| `cochlear-beriberi` | 520/520 | 0 | no | match |
| `ordained-incentive` | 333/333 | 0 | no | match |
| `uninsured-deformation` | 104/104 | 0 | no | match |

Raw machine-readable data: `artifacts/parity_raw.json`
