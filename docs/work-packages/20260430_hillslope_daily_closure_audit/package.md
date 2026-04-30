# Hillslope Daily Closure Audit Tool (MOFE + Single OFE)

**Status**: Completed (2026-04-30)  
**Timezone**: UTC

## Overview
`tools/totalwatsed3_daily_closure_audit.py` currently audits watershed-wide daily closure from `totalwatsed3.parquet`. Analysts also need hillslope-level closure diagnostics to evaluate suspect runoff behavior on individual hillslopes and compare MOFE vs single-OFE behavior directly from interchange artifacts.

This package delivers a new `tools/hillslope_daily_closure_audit.py` tool with regression tests and a small real-run evaluation set covering both MOFE (`uninsured-deformation`) and single-OFE (`bovine-clipboard`) hillslopes.

## Objectives
- Implement `tools/hillslope_daily_closure_audit.py` based on `tools/totalwatsed3_daily_closure_audit.py`.
- Support hillslope targeting by `wepp_id` or `topaz_id`.
- Compute daily water-balance closure from hillslope interchange inputs: `H.wat`, `H.pass`, optional `H.soil` and `H.element`.
- Preserve MOFE-correct handling (especially lateral-flow accounting and daily aggregation across OFEs).
- Add tests covering single-OFE and MOFE closures plus selector/CLI behavior.
- Run and document closure evaluations for a small exemplar set from `uninsured-deformation` and `bovine-clipboard`.
- Include independent code review and explicit finding disposition.

## Scope

### Included
- New tool `tools/hillslope_daily_closure_audit.py` with CLI outputs analogous to the totalwatsed3 audit tool.
- Input selection contract:
  - Required run/interchange context (`.../wepp/output/interchange`).
  - Selector: either `wepp_id` directly or `topaz_id` resolved through watershed translator.
- Daily closure metrics and summary outputs for a single hillslope:
  - Primary precipitation-basis closure.
  - Rain+Melt diagnostic closure.
  - Storage deltas from legacy/enriched terms when available.
  - Optional profile/storage diagnostics (`SoilWaterTotal`, `Profile*`, `TSMF`, `QRain`, `QSnow`) when present.
- Output artifacts:
  - `hillslope_daily_closure_audit_summary.json`
  - `hillslope_daily_closure_audit_top_days.csv`
- Unit/regression tests under `tests/tools/`.
- Real-run evaluation artifacts for selected MOFE and single-OFE hillslopes.
- Code review + disposition record artifact.

### Explicitly Out of Scope
- Changes to WEPP runoff/subsurface physics.
- Changes to `totalwatsed3` aggregation behavior beyond shared helper reuse that is required for parity.
- Multi-hillslope batch orchestration tool (this package is single-hillslope audit only).
- UI/report integration of hillslope closure outputs.

## Stakeholders
- **Primary**: Hydrology analysts validating hillslope runoff/closure behavior.
- **Reviewers**: WEPPpy interchange/tooling maintainers.
- **Security Reviewer**: Not required for this scope.
- **Informed**: Operators triaging suspect runs (`uninsured-deformation`, `bovine-clipboard`).

## Success Criteria
- [x] `tools/hillslope_daily_closure_audit.py` exists and is documented in help text.
- [x] Tool accepts either `--wepp-id` or `--topaz-id` (mutually exclusive), with deterministic topaz→wepp resolution.
- [x] MOFE handling is explicit and tested (last OFE lateral-flow rule preserved; runoff basis uses PASS `runvol`).
- [x] Regression tests pass for:
  - single-OFE synthetic closure case,
  - MOFE synthetic closure case,
  - selector behavior (`wepp_id` and `topaz_id`),
  - CLI output artifact generation.
- [x] Real-run closure audit artifacts are captured for at least 3 MOFE and 3 single-OFE exemplar hillslopes.
- [x] Code review findings are captured and dispositioned before closure.
- [x] `docs/dev-notes/totalwatsed-interchange.spec.md` is updated if any new tool contract decisions are made.

## Dependencies

### Prerequisites
- Existing watershed-level audit baseline: `tools/totalwatsed3_daily_closure_audit.py`.
- Interchange inputs present under run paths:
  - `/wc1/runs/un/uninsured-deformation/wepp/output/interchange`
  - `/wc1/runs/bo/bovine-clipboard/wepp/output/interchange`
- Topaz/wepp translation available through `wepppy.nodb.core.Watershed` for `--topaz-id` support.

### Blocks
- Follow-on package(s) that may consume hillslope audit outputs for UI/reporting.

## Related Packages
- **Related**: [20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation](../20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/package.md)
- **Related**: [20260429_totalwatsed3_storage_optional_terms](../20260429_totalwatsed3_storage_optional_terms/package.md)
- **Follow-up**: Potential package for multi-hillslope batch/compare reporting.

## Timeline Estimate
- **Expected duration**: 2-3 focused sessions
- **Complexity**: Medium
- **Risk level**: Medium

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Local diagnostics tool and tests only; no auth/session/secrets/new ingress surface.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)
- **Failure signature(s)**: Hillslope-level daily runoff/closure appears non-physical in analyst review, especially in MOFE hillslopes.
- **Related prior hardening efforts**:
  - [20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation](../20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/package.md)
  - [20260429_totalwatsed3_storage_optional_terms](../20260429_totalwatsed3_storage_optional_terms/package.md)
- **Health signals**:
  - Repeatable hillslope closure outputs for both MOFE and single-OFE runs.
  - Clear split between precipitation-basis and rain+melt diagnostic closure metrics.
- **Danger signals**:
  - MOFE double-counting regressions (especially lateral flow).
  - Selector ambiguity between `wepp_id` and `topaz_id`.
- **Observation window**: Package execution + reviewer pass.
- **Temporary calluses introduced**: None expected.
- **Callus softening hypothesis (if applicable)**: N/A.

## References
- `tools/totalwatsed3_daily_closure_audit.py` - Watershed-level closure audit baseline and naming conventions.
- `wepppy/wepp/interchange/totalwatsed3.py` - MOFE aggregation rules and volume/depth conversions.
- `wepppy/wepp/interchange/hill_wat_interchange.py` - Hillslope WAT schema and optional fields.
- `wepppy/wepp/interchange/hill_pass_interchange.py` - PASS runoff/subsurface terms.
- `wepppy/wepp/interchange/hill_soil_interchange.py` - Optional `TSMF` semantics.
- `wepppy/wepp/interchange/hill_element_interchange.py` - Optional `QRain`/`QSnow` semantics.
- `docs/dev-notes/totalwatsed-interchange.spec.md` - Water-balance contract for totalwatsed/interchange terms.

## Deliverables
- `tools/hillslope_daily_closure_audit.py` and tests.
- Evaluation artifacts under this package `artifacts/` for selected MOFE and single-OFE hillslopes.
- Code review artifact with finding disposition.

## Follow-up Work
- Optional batch wrapper to run closure audit for an entire hillslope set and emit comparative dashboard-ready artifacts.
- Optional integration of hillslope-closure outputs into operator troubleshooting workflows.
