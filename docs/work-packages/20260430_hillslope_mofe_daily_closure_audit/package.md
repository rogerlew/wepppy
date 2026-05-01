# Hillslope MOFE Daily Closure Audit + Contract Definition

**Status**: Open (2026-04-30)  
**Timezone**: UTC

## Overview
Stakeholders need a MOFE-specific daily water-balance audit path that goes beyond single-hillslope closure checks and explicitly validates MOFE-to-MOFE transfer/closure behavior. The package scope now explicitly targets **full physical daily closure interpretation** (with clear exported-term limits), not only legacy storage-proxy residuals.

This package defines and delivers:
1. A WEPP-source-backed MOFE water-balance contract.
2. A new repeatable tool `tools/hillslope_mofe_daily_closure_audit.py` with tests.
3. Real-run evaluation using `drilled-plight` plus focused review/disposition artifacts.

## Objectives
- Define MOFE water-balance contract from `/workdir/wepp-forest` source terms and routing behavior.
- Encode explicit full-physics daily closure equations and term semantics for MOFE hillslopes.
- Implement `tools/hillslope_mofe_daily_closure_audit.py` to audit one MOFE hillslope (by `wepp_id` or `topaz_id`).
- Add regression tests for contract-aligned MOFE behavior and edge conditions.
- Run exemplar evaluation on `drilled-plight` and capture evidence artifacts.
- Require subagent review gate specifically for contract milestone before implementation milestone closes.

## Scope

### Included
- New contract document based on WEPP source analysis, including:
  - term dictionary (surface, subsurface, lateral, storage terms),
  - MOFE routing semantics across OFEs,
  - day-level closure equations and tolerated residual behavior.
- New tool:
  - `tools/hillslope_mofe_daily_closure_audit.py`.
- New tests:
  - `tests/tools/test_hillslope_mofe_daily_closure_audit.py`.
- Work-package artifacts:
  - contract evidence notes,
  - review disposition,
  - run evaluation summaries.

### Explicitly Out of Scope
- Changes to WEPP runoff physics in this package.
- Changes to legacy `totalwatsed3` contract outside documented cross-reference updates.
- WEPP production reruns as part of package definition work (evaluation consumes available outputs).

## Stakeholders
- **Primary**: Hydrology analysts reviewing MOFE runoff/closure behavior.
- **Reviewers**: WEPPpy interchange/tool maintainers and a delegated subagent reviewer.
- **Informed**: Operators triaging suspicious hillslope episodes.

## Success Criteria
- [x] Contract milestone completed with explicit source citations from `/workdir/wepp-forest` and subagent reviewer sign-off artifact.
- [x] `tools/hillslope_mofe_daily_closure_audit.py` implemented and runnable.
- [x] Tool supports `--wepp-id` XOR `--topaz-id` for target hillslope selection.
- [x] MOFE-specific closure outputs include explicit transfer/closure terms across OFEs and residual diagnostics.
- [x] Regression tests pass for synthetic MOFE closure cases and selector behavior.
- [ ] Real-run exemplar evaluation captured for `drilled-plight` MOFE hillslopes.
- [ ] Independent review findings dispositioned before package closure.

## Dependencies

### Prerequisites
- Existing closure baseline:
  - `tools/hillslope_daily_closure_audit.py`
  - `tools/totalwatsed3_daily_closure_audit.py`
- WEPP source tree for contract derivation:
  - `/workdir/wepp-forest`
- Candidate evaluation run:
  - `/wc1/runs/dr/drilled-plight` (or host equivalent path where mounted).

### Blocks
- Follow-on operator workflows that depend on finalized MOFE closure contract.

## Related Packages
- **Related**: [20260430_hillslope_daily_closure_audit](../20260430_hillslope_daily_closure_audit/package.md)
- **Related**: [20260429_totalwatsed3_storage_optional_terms](../20260429_totalwatsed3_storage_optional_terms/package.md)
- **Related**: [20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation](../20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/package.md)

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions
- **Complexity**: Medium-High
- **Risk level**: Medium

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Analytical tooling and documentation changes only; no new auth/session/public ingress.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)
- **Failure signature(s)**: Suspected MOFE day-level closure anomalies (notably OFE chain effects following a single OFE-day outlier).
- **Related prior hardening efforts**:
  - [20260430_hillslope_daily_closure_audit](../20260430_hillslope_daily_closure_audit/package.md)
  - [20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation](../20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/package.md)
- **Health signals**:
  - Contract terms align with WEPP source behavior.
  - Tool residuals are explainable against documented routing/storage transitions.
- **Danger signals**:
  - Contract/tool mismatch on MOFE transfer terms.
  - Non-repeatable closure behavior across reruns of same artifact set.
- **Observation window**: Package execution + review gate.
- **Temporary calluses introduced**: None expected.
- **Callus softening hypothesis (if applicable)**: N/A.

## References
- `/workdir/wepp-forest` source files governing hillslope/MOFE water balance (to be enumerated in milestone artifact).
- `tools/hillslope_daily_closure_audit.py`
- `tools/totalwatsed3_daily_closure_audit.py`
- `wepppy/wepp/interchange/totalwatsed3.py`
- `wepppy/wepp/interchange/hill_wat_interchange.py`
- `wepppy/wepp/interchange/hill_pass_interchange.py`

## Deliverables
- New contract definition doc (source-backed, review-gated).
- `tools/hillslope_mofe_daily_closure_audit.py`.
- `tests/tools/test_hillslope_mofe_daily_closure_audit.py`.
- Evaluation and review disposition artifacts under this package.

## Follow-up Work
- Potential batch wrapper for multi-hillslope MOFE closure comparisons across a run.
- Optional integration of MOFE closure diagnostics into operator troubleshooting routes.
