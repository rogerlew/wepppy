# Closure Memo - Milestone 7 Single-OFE Open-Slice Closure

## 1. Executive Summary

- Open slices at start: `9`.
- Final status counts:
  - `patched=4`
  - `accepted_upstream=5`
  - `deferred=0`
- Full calibrated rerun sensitivity gate:
  - campaign root: `/home/workdir/wepp-forest/generative-inputs-fuzzing/results/milestone7_single_ofe_campaign_post_patch`
  - controls: `5/5`
  - `sensitivity_gate_pass=true`

## 2. Per-Slice Disposition Table

Evidence convention:
`/home/workdir/wepp-forest/generative-inputs-fuzzing/results/milestone7_single_ofe_open_slice_closure/targeted/{pre_patch,post_patch_rerun1,post_patch_rerun2}/<slug>/{campaign_summary.json,composite_case_disposition.csv}`

| Slice | Final Status | Closure Evidence | Patch/Test References | Residual Risk |
| --- | --- | --- | --- | --- |
| `wet:moderate:P5_SLOPE_RESPONSE_AMPLIFICATION` | `accepted_upstream` | slug=`wet_moderate_p5`; pre `200/61`, r1 `200/24`, r2 `200/24` | patch: `/home/workdir/wepppy/wepppy/wepp/fuzzing/seeded_soil_landuse_generators.py`; tests: `test_p5_slope_amplification_mutations_clamp_sat_texture_and_bd`, `test_p5_slope_amplification_management_window_is_stabilized` | Reduced materially but not closed after bounded patch attempt. |
| `wet:steep:P5_SLOPE_RESPONSE_AMPLIFICATION` | `accepted_upstream` | slug=`wet_steep_p5`; pre `200/76`, r1 `200/29`, r2 `200/22` | same P5 patch/tests as above | Reduced materially but not closed after bounded patch attempt. |
| `dry:steep:P5_SLOPE_RESPONSE_AMPLIFICATION` | `patched` | slug=`dry_steep_p5`; pre `200/30`, r1 `200/0`, r2 `200/0` | same P5 patch/tests as above | Closed under frozen gate (`2` consecutive reruns, `>=200`, `0` non-pass). |
| `wet:gradual:P5_SLOPE_RESPONSE_AMPLIFICATION` | `accepted_upstream` | slug=`wet_gradual_p5`; pre `200/45`, r1 `200/5`, r2 `200/8` | same P5 patch/tests as above | Reduced materially but not closed after bounded patch attempt. |
| `mesic:gradual:P5_SLOPE_RESPONSE_AMPLIFICATION` | `patched` | slug=`mesic_gradual_p5`; pre `200/45`, r1 `200/0`, r2 `200/0` | same P5 patch/tests as above | Closed under frozen gate. |
| `dry:moderate:P2_EVENT_EDGE` | `patched` | slug=`dry_moderate_p2`; pre `200/20`, r1 `200/0`, r2 `200/0` | patch: `/home/workdir/wepppy/wepppy/wepp/fuzzing/seeded_soil_landuse_generators.py`; test: `test_p2_event_edge_management_mutations_stay_within_safe_bounds` | Closed under frozen gate. |
| `wet:moderate:P2_EVENT_EDGE` | `accepted_upstream` | slug=`wet_moderate_p2`; pre `200/70`, r1 `200/15`, r2 `200/20` | same P2 patch/test as above | Reduced materially but not closed after bounded patch attempt. |
| `wet:steep:P4_TEXTURE_DENSITY_DISCONTINUITY` | `accepted_upstream` | slug=`wet_steep_p4`; pre `200/72`, r1 `200/23`, r2 `200/31` | patch: `/home/workdir/wepppy/wepppy/wepp/fuzzing/seeded_soil_landuse_generators.py`; test: `test_p4_texture_discontinuity_mutations_keep_texture_sum_bounded` | Reduced materially but not closed after bounded patch attempt. |
| `dry:steep:P4_TEXTURE_DENSITY_DISCONTINUITY` | `patched` | slug=`dry_steep_p4`; pre `200/38`, r1 `200/0`, r2 `200/0` | same P4 patch/test as above | Closed under frozen gate. |

## 3. Campaign Comparison Summary (M6 Post-Patch vs M7 Final)

Comparison artifact:
`/home/workdir/wepp-forest/docs/work-packages/20260422-generative-fuzzing-milestone7-single-ofe-open-slice-closure/artifacts/pre_post_metrics_comparison.json`

- Overall:
  - executed: `1008 -> 1008`
  - composite non-pass: `134 -> 41` (delta `-93`)
  - oracle flags: `134 -> 41` (delta `-93`)
- Per-bin composite non-pass deltas:
  - `dry:gradual -10`
  - `dry:moderate -7`
  - `dry:steep -17`
  - `mesic:gradual -14`
  - `mesic:moderate -9`
  - `mesic:steep -4`
  - `wet:gradual -8`
  - `wet:moderate -19`
  - `wet:steep -5`
- Priority-profile deltas:
  - `P5_SLOPE_RESPONSE_AMPLIFICATION: 60 -> 11` (delta `-49`)
  - `P2_EVENT_EDGE: 33 -> 4` (delta `-29`)
  - `P4_TEXTURE_DENSITY_DISCONTINUITY: 34 -> 8` (delta `-26`)

## 4. Required Gates Summary

- Rosetta host parity: pass.
- Rosetta container parity: pass.
- wepppy pytest gates:
  - `wctl run-pytest tests/wepp/test_single_ofe_stratified_campaign.py tests/wepp/test_seeded_soil_landuse_generators.py` pass (`28 passed`).
  - `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py` pass (`51 passed`).
  - `wctl run-pytest tests/nodb/test_wepp_input_parser.py tests/wepp/test_wepp_wrapper_property_contracts.py` pass (`110 passed`).
- wepp-forest classifier test gate:
  - `pytest tests/test_generative_signature_classifier.py` pass (`3 passed`).
- milestone0 known-failure gate:
  - `classify_signatures.py --manifest milestone0_known_failures.csv --enforce-expected` pass (`5/5`).

## 5. Follow-On Recommendation

- Milestone 8 multi-OFE pilot readiness: **conditionally ready**.
- Prerequisites before opening Milestone 8:
  - Carry forward patched mechanism clamps and targeted-slice runner surfaces as baseline.
  - Treat remaining `accepted_upstream` slices as explicit watchlist gates in early multi-OFE pilots, with same `>=200` deterministic slice-rerun discipline before status changes.
