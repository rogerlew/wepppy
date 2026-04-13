# WP-05 Parity Mismatch Disposition (Closure Update)

## Scope

Disposition evidence is based on basin-masked (`bound.tif > 0`) parity runs from:

1. retained IFOLP code state (H-002 + H-009 + H-010 + H-011):
   - `/tmp/ifolp_wp05_remediate/run1/reports/parity-report.final_effective.json`
   - `/tmp/ifolp_wp05_remediate/run2/reports/parity-report.final_effective.json`
2. provenance-aligned threshold probe for non-anchor fixtures:
   - `/tmp/ifolp_wp05_probe_thresh/run1 equivalent artifacts`
   - `/tmp/ifolp_wp05_probe_thresh_run2/*`

Deterministic canonical hashes:

- retained-state run1/run2: `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1`
- provenance-probe run1/run2: `cd013e16c16f14ac00e4c8b1b2b4cf9c325449bd54a74cd6fd640f37f183beb5`

## Findings Matrix

| Finding ID | Fixture(s) | Severity (final) | Evidence summary | Root-cause category | Confidence | Disposition |
|---|---|---|---|---|---|---|
| F-001 | `blackwood_60_5` (initial run failure) | resolved | Pointer `0` active-domain failure remains fixed; regression test coverage present. | IFOLP input-contract handling | high | closed-fixed |
| F-002 | `clueless_aftertaste_anchor_10_100` | resolved | Exact binary parity in retained-state run1/run2 (`FP=0`, `FN=0`). | Phase B MSCL predicate correction (H-009) + retained cadence/contracts | high | closed |
| F-003 | `blackwood_60_5` | low | Retained-state manifest contract: `FN=2170`. Provenance-aligned threshold probe (`csa=5`, `mscl=60`): `diff=8` (`FP=8`, `FN=0`). | Non-anchor threshold provenance ambiguity dominates; residual algorithmic delta is small | medium | effective-parity accepted for WP-05 closure |
| F-004 | `gatecreek_10m_30_2` | low | Retained-state manifest contract: `FN=35760`. Provenance-aligned threshold probe (`csa=2`, `mscl=30`): `diff=173` (`FP=173`, `FN=0`); focused local sweep found best `diff=13` near `csa=2.005..2.010`, `mscl=31..33`. | Non-anchor threshold provenance ambiguity dominates; residual algorithmic delta is bounded and small relative to network scale | medium | effective-parity accepted for WP-05 closure |

## Basin-Mask Interpretation Contract

Manual QA established and WP-00 protocol now enforces:

1. candidate/oracle comparisons must be basin-masked for apples-to-apples parity interpretation,
2. full-extent visual mismatch can conflate encoding-stage differences.

This contract was applied for all closure evidence above.

## Code Review / Disposition Notes

1. H-009 (`phase_b.mscl_unscaled_meters.v1`) is retained and is the parity-critical fix that closed F-002 and reduced non-anchor FN drift.
2. H-010 (single row-major Phase A pass) and H-011 (nearest-integer CSA conversion, min one cell) are retained for spec alignment; neither changed fixture-level parity metrics in WP-05 datasets.
3. Provenance-aligned threshold probes produced deterministic, low residual FP-only drift for non-anchor fixtures and were accepted by stakeholder as effectively identical for WP-05 closure.

## Closure Gate

- No unresolved high-severity findings remain.
- No unresolved medium-severity findings remain.
- Remaining deltas are low severity and explicitly accepted as effective parity for WP-05 closure.

## Follow-on (Post-Closure)

1. H-006: capture native-runtime oracle identity contract (`native_runtime` vs `snapshot_copy`) for long-horizon parity governance.
2. Complete authoritative threshold artifact backfill for non-anchor fixtures when source run lineage is available.
