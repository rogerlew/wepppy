# EBE `peak_runoff` Regression Ablation and Repair

**Status**: Completed with Residual Follow-ups (2026-05-13)  
**Timezone**: UTC

## Overview

`/wc1/runs/of/off-the-rack-neoprene` rerun with `wepp_260513` shows a semantic regression: `ebe_pw0.parquet.peak_runoff` is all zeros while corresponding `chan.out.parquet` peak discharge is nonzero on the same day/element keys. This package creates an ablation-first path to isolate the first failing stage, implement a minimal contract-preserving fix, and vendor the corrected WEPP binary into `wepppy` with reproducible evidence.

## Objectives

- Build a staged ablation matrix for the `ebe_pw0.peak_runoff` pipeline (producer -> parser -> interchange -> consumer cross-check).
- Identify the first stage where nonzero peak values are lost.
- Land a minimal fix with regression coverage at the failing boundary.
- Re-run three-cohort semantic comparison and confirm no unintended routing/closure regressions.
- Vendor the corrected binary in `wepppy` with provenance, hash evidence, and rollback notes.

## Scope

### Included

- Regression reproduction on:
  - `/wc1/runs/of/off-the-rack-neoprene` (`wepp_260513`)
  - `/wc1/runs/ca/carnivorous-adobo` (`wepp_dcc52a6` baseline)
- Ablation instrumentation and evidence artifacts for `ebe_pw0.peak_runoff` serialization path.
- Minimal fix in the responsible layer (producer/parsing/serialization contract).
- Regression tests for the exact failure mode (all-zero `peak_runoff` while `chan.out` nonzero).
- Binary vendoring in `wepppy` after fix acceptance.
- Updated operator/developer docs for the corrected contract.

### Explicitly Out of Scope

- Broad hydrology retuning or unrelated routing-physics changes.
- Changes to deferred WB-36 retained sites (`RI-018`, `RI-024`) unless directly proven causal to this defect.
- Unrelated schema redesign in interchange products.
- Silent fallback behavior that masks missing/invalid peak values.

## Implementation Fidelity and Evidence (Required for modernization/migrations)

- **Fidelity target**: `faithful extraction`
- **Authoritative source path(s)**:
  - Channel peak source: `chan.out` / route peak publish surface
  - Event export target: `ebe_pw0` (`peak_runoff`)
- **Cutover proof required**:
  - On identical day/element keys, `ebe_pw0.peak_runoff` is nonzero when source channel peak is nonzero.
  - Cross-run semantic drift stays within expected baseline envelope; no new closure break introduced.
- **Acceptance evidence type**: `both`

## Stakeholders

- **Primary**: Hydrology/model maintainers and WEPPcloud operators.
- **Reviewers**: WEPP serialization/path-contract maintainers (`wepp-forest` + `wepppy`).
- **Security Reviewer**: Not required by default (no auth/secrets attack-surface change expected).
- **Informed**: openWEPP parity consumers and release operators.

## Success Criteria

- [x] Ablation matrix executed with explicit stage-level pass/fail evidence.
- [x] Root-cause stage identified with reproducible proof artifact.
- [ ] Minimal fix landed with regression tests that fail pre-fix and pass post-fix.
- [ ] Three-cohort semantic comparison rerun confirms regression resolved and no new high-magnitude drift.
- [x] Corrected binary vendored in `wepppy` with SHA256 and provenance docs.

## Closure Disposition (2026-05-13)

Package closeout is accepted with two explicit follow-up residuals:

1. Add targeted regression coverage for the all-zero `ebe_pw0.peak_runoff` failure mode.
2. Run broader three-cohort recertification beyond the off-run confirmation and baseline semantic comparison.

Closed evidence confirming the primary defect resolution:

- Rerun verification on `/wc1/runs/of/off-the-rack-neoprene` shows `ebe_pw0.peak_runoff` nonzero on all rows and no `chan_peak>0` / `ebe_peak=0` mismatches.
- Candidate/baseline alignment remains in expected small delta envelope (see `artifacts/post_fix_semantic_compare.json`).

## Dependencies

### Prerequisites

- Comparable runs and interchange artifacts available under `/wc1/runs/`.
- Access to build and run candidate WEPP binaries from `wepp-forest`.
- Existing semantic rubric in `/workdir/wepp-forest/docs/pass-serialization-channel-routing-comparison-report.md`.

### Blocks

- Downstream release recertification and parity-signoff for affected pass family.

## Related Packages

- **Related**: `docs/work-packages/20260502_mofe_flagged_hillslope_triage/`
- **Related**: `docs/work-packages/20260430_uncapped_spectacular_h2637_ablation_campaign/`
- **External context**: `/workdir/wepp-forest/docs/work-packages/20260510-wb36-watershed-routing-legacy-retirement-and-recertification/`

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium (contract break with release implications).

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Data-contract and numerical output correctness work; no new auth/session/secret or external egress surfaces expected.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)

- **Failure signature(s)**:
  - `ebe_pw0.parquet.peak_runoff == 0` across all rows while `chan.out.parquet.Peak_Discharge (m^3/s) > 0` on matching keys.
- **Related prior hardening efforts**:
  - `/workdir/wepp-forest/docs/pass-serialization-channel-routing-comparison-report.md`
  - WB-36 mechanism evidence (`/workdir/wepp-forest/docs/work-packages/20260510-wb36-watershed-routing-legacy-retirement-and-recertification/artifacts/`)
- **Health signals**:
  - `ebe_pw0.peak_runoff` tracks channel/event peaks with nonzero values where expected.
  - Cross-table consistency checks (`chan.out` vs `ebe_pw0`) pass.
- **Danger signals**:
  - Fix introduces order-of-magnitude drift in streamflow/peak metrics.
  - Closure checks fail or previously stable cohorts diverge unexpectedly.
- **Observation window**: 7-14 days across representative reruns.
- **Temporary calluses introduced**: none planned.
- **Callus softening hypothesis (if applicable)**: not applicable.

## References

- `/workdir/wepp-forest/docs/pass-serialization-channel-routing-comparison-report.md` - comparison rubric and semantic assessment pattern.
- `/tmp/off260513_vs_ca_dcc52a6_semantic_compare.json` - current semantic comparison evidence.
- `/wc1/runs/of/off-the-rack-neoprene/wepp/output/interchange/` - candidate run artifacts (`wepp_260513`).
- `/wc1/runs/ca/carnivorous-adobo/wepp/output/interchange/` - baseline run artifacts (`wepp_dcc52a6`).
- `docs/ablation/README.md` - ablation artifact conventions.

## Deliverables

- New work package scaffold and active ExecPlan.
- Ablation matrix + evidence artifacts (stage-by-stage).
- Root-cause note and fix commit with targeted tests.
- Updated semantic comparison report for post-fix validation.
- Binary vendoring provenance artifact for the corrected build.

## Follow-up Work

- Optional broader pass-family contract audit if additional serialization fields show similar zeroing patterns.
- Optional automated semantic guard in CI for `chan.out` vs `ebe_pw0` peak consistency on fixture runs.
