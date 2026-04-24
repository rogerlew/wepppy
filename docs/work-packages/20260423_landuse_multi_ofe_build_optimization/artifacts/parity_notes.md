# Landuse Multi-OFE Build Parity Notes

- Generated (UTC): 2026-04-23T19:50:22+00:00
- Baseline mode: legacy orchestration emulation with duplicate management build pass.
- Optimized mode: duplicate-pass collapsed orchestration.
- Parity status is based on MOFE management files, management area/coverage values, and DOMLC_MOFE assignments.
- `Parquet Match` is reported for observability; row-level semantics may match even when file-level signatures vary.

| Run | MOFE File Mismatches | Mgmt Area Mismatches | Mgmt Pct Mismatches | Parquet Match | DOMLC_MOFE Match | Status |
| --- | ---: | ---: | ---: | :---: | :---: | --- |
| `moth-eaten-blackhead` | 0 | 0 | 0 | no | yes | match |
| `objectionable-sublimate` | 0 | 0 | 0 | yes | yes | match |
| `cochlear-beriberi` | 0 | 0 | 0 | no | yes | match |
| `ordained-incentive` | 0 | 0 | 0 | no | yes | match |
| `uninsured-deformation` | 0 | 0 | 0 | no | yes | match |

Raw machine-readable data: `artifacts/parity_raw.json`
