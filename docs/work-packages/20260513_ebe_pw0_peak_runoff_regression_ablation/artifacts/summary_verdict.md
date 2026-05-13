# EBE `peak_runoff` Ablation Verdict (Pre-Fix)

Date: 2026-05-13 UTC

## Scope

This verdict covers ablation execution for:

- Candidate: `/wc1/runs/of/off-the-rack-neoprene` (`_wepp_bin=wepp_260513`, `_pass_family=hbp`)
- Baseline: `/wc1/runs/ca/carnivorous-adobo` (`_wepp_bin=wepp_dcc52a6`, `_pass_family=legacy_ascii`)

## Verdict

The `ebe_pw0.peak_runoff` regression is **real** and the first-loss boundary is **producer-side** in raw `ebe_pw0.txt` generation for the candidate run family.

- `off_ablation_first_loss_boundary=producer_raw_ebe_txt`
- Parser/interchange path is not causal for this signature.

## Evidence

1. Candidate current run has all-zero `ebe_pw0.peak_runoff` while `chan.out` peaks are nonzero:
   - `artifacts/ablation_stage_summary.json` -> `off_current`
2. Candidate ablation replay preserves the same defect in raw producer text:
   - `off_ablation.ebe_raw_txt.zero_rows=60270`
   - `off_ablation.chan_raw_txt.zero_rows=0`
3. Parser-path control on identical raw input shows no additional loss:
   - `artifacts/off_ablation_parser_path_comparison.json`
   - `pipeline`, `python`, and `rust` parquet outputs are identical (`max_abs_delta=0`)
4. Baseline run + baseline ablation replay are healthy:
   - `artifacts/ablation_stage_summary.json` -> `ca_current`, `ca_ablation`
   - Both raw and parquet stages preserve nonzero peak values

## Interpretation

- The failure occurs **before** interchange serialization.
- `pass_pw0.txt` presence is non-causal for this defect (`hbp` pass-family treats it as optional/non-authoritative in this path).
- Repair should target producer-side peak assignment that feeds `ebe_pw0.txt`.

## Next Step (Repair Boundary)

Implement a minimal producer-side fix, then rerun three-cohort semantic comparison and binary vendoring steps with updated provenance artifacts.

## Post-Fix Update (2026-05-13 UTC)

Producer-side fix candidate was built and replayed on the off-run ablation clone with preserved raw outputs.

- Raw `ebe_pw0.txt` peaks are restored (`zero_rows=0`, `max_peak=3.59151`).
- Parquet `ebe_pw0.peak_runoff` is no longer all-zero (`zero_rows=0`).
- Candidate chan-vs-ebe alignment is restored to expected small deltas:
  - `mean_abs_delta=6.294e-05`
  - `max_abs_delta=0.005`
  - `chan_pos_ebe_zero=0`

Evidence:

- `artifacts/post_fix_semantic_compare.json`
- `artifacts/binary_provenance.md`
