# Drilled-Plight Evaluation Summary

## Scope
Executed `tools/hillslope_mofe_daily_closure_audit.py` (full-physics rework) against representative `drilled-plight` hillslopes selected by prior PASS-runoff triage:
- `wepp_id=4`
- `wepp_id=99`
- `wepp_id=115`

Run command basis (per hillslope):
- `PYTHONPATH=/workdir/wepppy python tools/hillslope_mofe_daily_closure_audit.py /wc1/runs/dr/drilled-plight/wepp/output/interchange --wepp-id <id> --output-dir <artifact_dir> --top-n 25`

## Result Table
| artifact_dir | wepp_id | rows | n_ofe_min | n_ofe_max | mofe_chain_rows | full_physical_storage_basis | full_physical_closure_residual_total_mm | full_physical_closure_residual_pct_of_rm_total | full_physical_closure_max_abs_daily_mm | mean_abs_daily_closure_reconstructed_with_storage_mm |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| drilled_plight_H4 | 4 | 18262 | 1 | 1 | 0 | SoilWaterTotal_plus_SnowWater | 92.170427 | 0.157591 | 78.090000 | 0.008214 |
| drilled_plight_H99 | 99 | 18262 | 1 | 1 | 0 | SoilWaterTotal_plus_SnowWater | 110.515442 | 0.188957 | 78.090000 | 0.007795 |
| drilled_plight_H115 | 115 | 18262 | 1 | 1 | 0 | SoilWaterTotal_plus_SnowWater | 104.662424 | 0.178950 | 78.100000 | 0.007623 |

## Blocker Evidence (MOFE Exemplar Availability)
`drilled-plight` interchange exists, but contains no MOFE hillslopes:
- Query basis: `H.wat.parquet` grouped by `wepp_id` and `COUNT(DISTINCT ofe_id)`.
- Result: `hillslopes=277`, `mofe_hillslopes=0`, `max_n_ofe=1`.

Implication:
- Required adjacent-OFE MOFE chain diagnostics cannot be exercised on `drilled-plight` because there are no multi-OFE hillslopes in this run.
- Evaluation artifacts above are valid single-OFE runs and confirm tool execution/output generation for the full-physics rework, but they do not validate MOFE chain behavior on this run.

## Notable Outliers
- All three evaluated hillslopes report `mofe_chain_rows=0` because `n_ofe_max=1` throughout.
- The reworked full-physics diagnostic shows non-zero whole-run residual totals, which are now explicitly reported as exported-term residual diagnostics rather than strict model-failure assertions.
