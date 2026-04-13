# WP-05 Hypothesis Log (F-002 / F-003 / F-004)

## Purpose

Track hypothesis-driven remediation experiments for IFOLP pruning parity drift. Every hypothesis entry must include:
- expected parity impact,
- bounded code-change scope,
- a unique `change_fingerprint`,
- parity evidence after execution,
- disposition (`confirmed`, `rejected`, `partial`, `deferred`, `invalid-run`).

## Anti-Retest Protocol

1. Before code edits, define a `change_fingerprint` and add/update the hypothesis row.
2. Search this log for the same fingerprint.
3. If the fingerprint already has disposition `confirmed`, `rejected`, `partial`, or `deferred`, do not rerun unless a retry gate is satisfied.
4. Allowed retry gates:
   - authoritative fixture provenance changed,
   - oracle/harness contract changed,
   - previous run marked `invalid-run`,
   - materially different code path (new fingerprint; set `supersedes`).
5. Each executed experiment must capture parity evidence before code review/disposition.

## Hypothesis Register

| Hypothesis ID | Target finding(s) | Hypothesis | Planned modification scope | Change fingerprint | Supersedes | Expected parity impact | Status | Disposition | Last canonical hash |
|---|---|---|---|---|---|---|---|---|---|
| H-001 | F-002 | Continue Phase B repasses while any prune occurs in pass, not only on receiver degeneration. | `iterative_first_order_link_prune_phase_b.rs`, `iterative_first_order_link_prune_phase_b_tests.rs` | `phase_b.repass_on_any_inflow_drop.v1` | none | Reduce anchor false positives via additional downstream eligibility. | done | rejected (no parity impact; reverted) | `5e818ce796d5f703ec3bcef86de84c0345d554f7198699265c7ad5c5a5286a79` |
| H-002 | F-002, F-003 | Compare Phase B local MSCL with cell-size-scaled length. | `iterative_first_order_link_prune_phase_b.rs`, `iterative_first_order_link_prune_phase_b_tests.rs` | `phase_b.mscl_threshold_cellsize_scaling.v1` | H-001 | Improve pruning aggressiveness parity in anchor and blackwood. | done | partial (retained; best bounded improvement) | `2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845` |
| H-003 | F-004 | Gatecreek drift is dominated by threshold provenance ambiguity; bounded algorithm edits cannot safely close it. | analysis + provenance artifacts (no code change) | `analysis.provenance_hardblock_gatecreek.v1` | none | Convert unresolved medium finding to explicit hard-blocked low residual with evidence. | done | deferred (hard-blocked by provenance) | `2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845` |
| H-004 | F-003, F-004 | Receiver-group tie handling is driving branch-level drift; selecting the last candidate when shortest-link lengths tie within epsilon may align receiver pruning choice with TopAZ behavior without changing contract thresholds. | `iterative_first_order_link_prune_topology.rs`, `iterative_first_order_link_prune_topology_tests.rs` | `phase_b.tie_break_last_within_epsilon.v1` | H-002 | Reduce mixed FP/FN drift on blackwood/gatecreek while keeping anchor regression bounded. | done | rejected (no parity impact; reverted) | `2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845` |
| H-005 | F-003, F-004 | Residual drift is materially driven by non-authoritative threshold provenance for non-anchor fixtures. | WP-05 provenance artifacts + fixture manifests/docs (no IFOLP code change) | `provenance.authoritative_threshold_backfill.non_anchor.v1` | H-003 | Replace inferred threshold sources with explicit run artifacts; expect parity movement without algorithm edits if prior thresholds were wrong. | done | partial (parity-equivalent probe signal; full artifact backfill still open) | `cd013e16c16f14ac00e4c8b1b2b4cf9c325449bd54a74cd6fd640f37f183beb5` |
| H-006 | F-003, F-004 | Snapshot-copy oracle capture may hide runtime-contract drift; native-runtime oracle manifest may expose oracle-side deltas. | oracle harness/runtime contract artifacts (no IFOLP code change) | `oracle.runtime_contract.native_vs_snapshot.v1` | H-005 | Detect oracle-side divergence before IFOLP comparison and reduce attribution ambiguity. | planned | pending | `2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845` |
| H-007 | F-003 | First divergence is likely pass-level and localization-limited; trace export should isolate first pass/cell divergence. | parity harness trace-mode artifacts (no IFOLP behavior change) | `phase_a.single_pass_contract.trace_localization.v1` | H-006 | Convert broad drift into targeted pass-level decision mismatch evidence. | planned | pending | `2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845` |
| H-008 | F-003, F-004 | Candidate validity handling semantics (strict failure vs permissive stale-skip) may still influence residual drift. | spec/trace validation artifacts (bounded behavior check) | `phase_b.candidate_validity_contract.strictness.v1` | H-007 | Determine whether stricter candidate-validity contract materially changes fixture parity. | planned | pending | `2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845` |
| H-009 | F-002, F-003, F-004 | Phase B currently multiplies local `mscl_m` by cell size before comparing against `length_m`; this likely over-prunes because `length_m` is already in map units. | `iterative_first_order_link_prune_phase_b.rs`, `iterative_first_order_link_prune_phase_b_tests.rs` | `phase_b.mscl_unscaled_meters.v1` | H-002 | Reduce large basin-masked FN-only drift by restoring meter-to-meter MSCL predicate (`length_m < mscl_m - epsilon`). | done | partial (retained; anchor exact and major FN reduction) | `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1` |
| H-010 | F-003, F-004 | Phase A should execute a single row-major inline qualification pass; removing multi-pass rescans may align source-qualification cadence with updated parity contract. | `iterative_first_order_link_prune_phase_a.rs`, `iterative_first_order_link_prune_phase_a_tests.rs` | `phase_a.single_row_major_inline_pass.v1` | H-007 | Reduce residual drift caused by extra Phase A rescans while preserving anchor behavior. | done | partial (retained for spec alignment; no additional parity movement beyond H-009 state) | `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1` |
| H-011 | F-003, F-004 | CSA conversion currently uses fractional cell thresholds with floor-like behavior; parity may require explicit nearest-integer cell conversion with a minimum of one cell. | `iterative_first_order_link_prune.rs`, `iterative_first_order_link_prune_parser_tests.rs` | `thresholds.csa_nearest_integer_min_one.v1` | H-010 | Reduce small residual FP drift after provenance-aligned threshold probes and match enhanced CSA contract. | done | partial (retained for spec alignment; no fixture-level parity movement) | `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1` |

## Experiment Index

| Run ID | Timestamp (UTC) | Hypothesis ID | Change fingerprint | Run roots | Canonical hash | Outcome |
|---|---|---|---|---|---|---|
| E-000 | 2026-04-13T16:34:00Z | baseline | `baseline.wp05_cycle1.v1` | `/tmp/ifolp_wp05_remediate/run1`, `/tmp/ifolp_wp05_remediate/run2` | `5e818ce796d5f703ec3bcef86de84c0345d554f7198699265c7ad5c5a5286a79` | Deterministic mismatch baseline confirmed. |
| E-001 | 2026-04-13T17:05:00Z | H-001 | `phase_b.repass_on_any_inflow_drop.v1` | `/tmp/ifolp_wp05_remediate/run1` | `5e818ce796d5f703ec3bcef86de84c0345d554f7198699265c7ad5c5a5286a79` | No parity movement; rejected and reverted. |
| E-002 | 2026-04-13T17:32:00Z | H-002 | `phase_b.mscl_threshold_cellsize_scaling.v1` | `/tmp/ifolp_wp05_remediate/run1` | `2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845` | Anchor improved materially; retained as partial fix. |
| E-003 | 2026-04-13T17:58:00Z | H-003 | `analysis.provenance_hardblock_gatecreek.v1` | `/tmp/ifolp_wp05_remediate/run1`, `/tmp/ifolp_wp05_remediate/run2` | `2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845` | Hard-block disposition for residual gatecreek mismatch. |
| E-004 | 2026-04-13T18:37:00Z | H-004 | `phase_b.tie_break_last_within_epsilon.v1` | `/tmp/ifolp_wp05_remediate/run1` | `2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845` | No metric/hash movement; rejected and reverted. |
| E-005 | 2026-04-13T18:58:00Z | baseline-v2 | `baseline.wp05_basin_mask_contract.v1` | `/tmp/ifolp_wp05_remediate/run1`, `/tmp/ifolp_wp05_remediate/run2` | `fe0ff76290d241e040f5dfa89ab02a11fd007b377b655ea01924e8c4da3891bd` | Basin-masked baseline rerun under manifest/report v2 shows FN-only over-pruning on all fixtures (FP=0). |
| E-006 | 2026-04-13T19:37:00Z | H-009 | `phase_b.mscl_unscaled_meters.v1` | `/tmp/ifolp_wp05_remediate/run1` | `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1` | Valid rerun after explicit rebuild improved to anchor exact and reduced non-anchor FN-only residuals. |
| E-007 | 2026-04-13T20:41:00Z | H-010 | `phase_a.single_row_major_inline_pass.v1` | `/tmp/ifolp_wp05_remediate/run1` | `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1` | No additional movement vs H-009 retained state; retained for updated spec alignment. |
| E-008 | 2026-04-13T21:20:00Z | H-011 | `thresholds.csa_nearest_integer_min_one.v1` | `/tmp/ifolp_wp05_remediate/run1`, `/tmp/ifolp_wp05_remediate/run2` | `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1` | Spec-alignment change had no fixture-level parity movement; retained for numeric contract compliance. |
| E-009 | 2026-04-13T22:05:00Z | H-005 | `provenance.authoritative_threshold_backfill.non_anchor.v1` | `/tmp/ifolp_wp05_probe_thresh*` | `cd013e16c16f14ac00e4c8b1b2b4cf9c325449bd54a74cd6fd640f37f183beb5` | Provenance-aligned threshold probe (`blackwood 5/60`, `gatecreek 2/30`) reduced residual to low FP-only deltas and met stakeholder effective-parity acceptance. |

## Experiment Entries

### E-000: Baseline before remediation edits
- **Timestamp (UTC)**: 2026-04-13T16:34:00Z
- **Hypothesis ID**: baseline
- **Change fingerprint**: `baseline.wp05_cycle1.v1`
- **Files changed**: none
- **Parity evidence**:
  - Canonical hash (run1/run2): `5e818ce796d5f703ec3bcef86de84c0345d554f7198699265c7ad5c5a5286a79`.
  - `blackwood_60_5`: `differing_cell_count=4486`, `stream_delta=+146`.
  - `clueless_aftertaste_anchor_10_100`: `differing_cell_count=803`, `stream_delta=+803`.
  - `gatecreek_10m_30_2`: `differing_cell_count=65951`, `stream_delta=-5569`.
- **Disposition**: baseline evidence.

### E-001: H-001
- **Timestamp (UTC)**: 2026-04-13T17:05:00Z
- **Change fingerprint**: `phase_b.repass_on_any_inflow_drop.v1`
- **Files changed**:
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b.rs`
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b_tests.rs`
- **Parity evidence**: canonical hash unchanged (`5e818ce...`); fixture metrics unchanged.
- **Disposition**: rejected, reverted.

### E-002: H-002
- **Timestamp (UTC)**: 2026-04-13T17:32:00Z
- **Change fingerprint**: `phase_b.mscl_threshold_cellsize_scaling.v1`
- **Files changed**:
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b.rs`
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b_tests.rs`
- **Parity evidence**:
  - Canonical hash: `2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845`.
  - `blackwood_60_5`: `4486 -> 4467`, `+146 -> +121`.
  - `clueless_aftertaste_anchor_10_100`: `803 -> 392`, `+803 -> -42`.
  - `gatecreek_10m_30_2`: `65951 -> 65949`, `-5569 -> -5575`.
- **Disposition**: partial, retained.

### E-003: H-003 disposition pass
- **Timestamp (UTC)**: 2026-04-13T17:58:00Z
- **Change fingerprint**: `analysis.provenance_hardblock_gatecreek.v1`
- **Files changed**: none
- **Parity evidence**: final canonical hash stable across reruns (`2ef1aff...`); gatecreek residual remained high.
- **Disposition**: deferred (hard-blocked pending provenance follow-on).

### E-004: H-004
- **Timestamp (UTC)**: 2026-04-13T18:37:00Z
- **Change fingerprint**: `phase_b.tie_break_last_within_epsilon.v1`
- **Files changed**:
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_topology.rs`
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_topology_tests.rs`
- **Parity evidence**:
  - Canonical hash unchanged (`2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845`).
  - `blackwood_60_5`: unchanged (`differing_cell_count=4467`, `stream_delta=+121`).
  - `clueless_aftertaste_anchor_10_100`: unchanged (`differing_cell_count=392`, `stream_delta=-42`).
  - `gatecreek_10m_30_2`: unchanged (`differing_cell_count=65949`, `stream_delta=-5575`).
- **Disposition**: rejected and reverted (no parity impact despite unit-test-visible tie behavior).

### E-005: Basin-mask v2 baseline rerun
- **Timestamp (UTC)**: 2026-04-13T18:58:00Z
- **Hypothesis ID**: baseline-v2
- **Change fingerprint**: `baseline.wp05_basin_mask_contract.v1`
- **Files changed**: none
- **Parity evidence**:
  - Canonical hash (run1/run2): `fe0ff76290d241e040f5dfa89ab02a11fd007b377b655ea01924e8c4da3891bd`.
  - `blackwood_60_5`: `differing_cell_count=2173`, `false_positives=0`, `false_negatives=2173`, `stream_delta=-2173`.
  - `clueless_aftertaste_anchor_10_100`: `differing_cell_count=217`, `false_positives=0`, `false_negatives=217`, `stream_delta=-217`.
  - `gatecreek_10m_30_2`: `differing_cell_count=35762`, `false_positives=0`, `false_negatives=35762`, `stream_delta=-35762`.
- **Disposition**: baseline evidence under apples-to-apples comparison contract.

### E-006: H-009 (valid rerun after rebuild)
- **Timestamp (UTC)**: 2026-04-13T19:37:00Z
- **Change fingerprint**: `phase_b.mscl_unscaled_meters.v1`
- **Files changed**:
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b.rs`
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b_tests.rs`
- **Retry-gate evidence**: prior immediate run for same fingerprint was invalid because candidate generation used a stale binary before explicit rebuild.
- **Parity evidence**:
  - Canonical hash (run1): `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1`.
  - `blackwood_60_5`: `false_negatives=2170` (improved from `2173`).
  - `clueless_aftertaste_anchor_10_100`: exact parity (`false_positives=0`, `false_negatives=0`).
  - `gatecreek_10m_30_2`: `false_negatives=35760` (improved from `35762`).
- **Disposition**: partial, retained.

### E-007: H-010
- **Timestamp (UTC)**: 2026-04-13T20:41:00Z
- **Change fingerprint**: `phase_a.single_row_major_inline_pass.v1`
- **Files changed**:
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_a.rs`
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_a_tests.rs`
- **Parity evidence**:
  - Canonical hash unchanged vs H-009 retained state (`07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1`).
  - Fixture-level basin-masked metrics unchanged.
- **Disposition**: partial, retained (spec-aligned with no additional parity movement).

### E-008: H-011
- **Timestamp (UTC)**: 2026-04-13T21:20:00Z
- **Change fingerprint**: `thresholds.csa_nearest_integer_min_one.v1`
- **Files changed**:
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs`
  - `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_parser_tests.rs`
- **Parity evidence**:
  - Canonical hash stable across run1/run2 at `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1`.
  - No fixture-level metric movement.
- **Disposition**: partial, retained (numeric contract aligned; no parity movement).

### E-009: H-005 provenance-aligned threshold probe
- **Timestamp (UTC)**: 2026-04-13T22:05:00Z
- **Change fingerprint**: `provenance.authoritative_threshold_backfill.non_anchor.v1`
- **Files changed**: none (probe manifests only under `/tmp` run roots)
- **Probe thresholds**:
  - `blackwood_60_5`: `csa_ha=5.0`, `mscl_m=60.0`
  - `gatecreek_10m_30_2`: `csa_ha=2.0`, `mscl_m=30.0`
- **Parity evidence**:
  - Canonical hash (probe run1/probe run2): `cd013e16c16f14ac00e4c8b1b2b4cf9c325449bd54a74cd6fd640f37f183beb5`.
  - `blackwood_60_5`: `differing_cell_count=8` (`FP=8`, `FN=0`).
  - `clueless_aftertaste_anchor_10_100`: exact parity.
  - `gatecreek_10m_30_2`: `differing_cell_count=173` (`FP=173`, `FN=0`).
  - Focused local sweep around gatecreek probe minima found floor `differing_cell_count=13` near `csa_ha=2.005..2.010`, `mscl_m=31..33`; no exact `0` point observed in tested neighborhood.
- **Disposition**: partial (effective-parity signal accepted for WP-05 closure; full authoritative provenance backfill remains open follow-on).

## Notes

- Strict sequence remains mandatory for each hypothesis: modification -> parity -> code review/disposition.
- Final retained code state for WP-05 closure includes H-002 + H-009 + H-010 + H-011 (H-010/H-011 are spec-alignment retains with no additional parity movement).
- Use H-004+ rows for additional cycles; do not reuse existing fingerprints without retry-gate evidence.
- Manual QA discovery (2026-04-13): full-extent candidate/oracle rasters are at different encoding stages (`0/1` extent vs channel-only `1`+NoData); basin-masked diagnostics (`bound.tif > 0`) show candidate is over-pruned relative to oracle for gatecreek/clueless.
- Harness contract change (2026-04-13): WP-00 comparison tooling/docs now default to basin-masked parity (`--comparison-domain basin_mask`, manifest schema v2); this qualifies as retry-gate evidence category "oracle/harness contract changed" for future superseding fingerprints.
