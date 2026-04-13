# Iterative First-Order Link Prune WP-05 TopAZ Parity Validation

**Status**: Closed - Effective Parity Accepted (2026-04-14)
**Timezone**: UTC

## Overview
This package governs execution of WP-05 for Iterative First-Order Link Prune in `/workdir/weppcloud-wbt`. WP-05 remediation concluded with stakeholder acceptance of effective parity equivalence after iterative hypothesis testing, basin-masked parity protocol alignment, and deterministic rerun evidence capture.

## Objectives
- Define and maintain a hypothesis log for F-002, F-003, and F-004 mismatch causes.
- Implement bounded IFOLP modifications per hypothesis with explicit intent and rollback safety.
- Run parity testing after each hypothesis modification and on full reruns.
- Complete code review/disposition only after parity test evidence is captured.
- Prevent duplicate experiment runs by enforcing change-fingerprint and retry-gate rules.

## Scope
This package is limited to WP-05 parity-remediation work in `weppcloud-wbt`.

### Included
- Fixture preparation and checksum verification using WP-00 harness tooling.
- Oracle capture verification from pinned `netw0.tif` artifacts.
- Candidate IFOLP output generation for each fixture.
- Metric comparison using `tools/ifolp_wp00_compare_outputs.py`.
- Determinism rerun evidence using canonical report hashing.
- Hypothesis-driven parity-fix follow-through in IFOLP modules.
- Per-hypothesis parity evidence capture and disposition.
- Anti-retest experiment ledger rules (change fingerprinting, supersession, and retry criteria).
- WP-05 implementation-plan row updates and review-disposition evidence.

### Explicitly Out of Scope
- New algorithmic features beyond parity defect correction for IFOLP.
- Error-contract hardening package scope (WP-06).
- Optimization and multithreading pass (WP-07).
- WEPPpy integration work.

## Stakeholders
- **Primary**: WEPPcloud WBT maintainers.
- **Reviewers**: stream-network-analysis maintainers and parity reviewers.
- **Security Reviewer**: not required for this package scope.
- **Informed**: WEPPpy maintainers coordinating IFOLP rollout.

## Success Criteria
- [x] Hypothesis log exists with F-002/F-003/F-004 root-cause hypotheses and experiment plans.
- [x] At least one bounded code modification is executed for each accepted hypothesis track.
- [x] Parity test evidence is captured after each hypothesis modification.
- [x] Every executed experiment records a unique change fingerprint and duplicate attempts are prevented unless explicit retry criteria are met.
- [x] Every partial/rejected hypothesis is either superseded by a new fingerprint or explicitly parked with rationale.
- [x] Full rerun parity report and canonical determinism hash are regenerated.
- [x] F-002/F-003/F-004 are resolved to accepted parity outcome or blocked with explicit hard evidence.
- [x] Code review/disposition is completed after parity testing with no unresolved high/medium findings.
- [x] `cargo check -p whitebox_tools` and targeted IFOLP tests pass after remediation changes.
- [x] WP-05 row in WBT implementation plan is updated with remediation outcomes and gate states.

## Iteration Control Rules
1. Every hypothesis attempt must have a `change_fingerprint` before code edits begin.
2. An attempt cannot run if the same fingerprint already has a `confirmed`, `rejected`, `partial`, or `deferred` disposition unless retry-gate evidence is provided in `hypothesis_log.md`.
3. The required execution order remains strict for each attempt:
   - bounded code modification,
   - immediate parity run,
   - post-parity code review/disposition.
4. If a hypothesis is superseded, the successor must reference the prior hypothesis ID and explain why the fingerprint is materially different.

## Dependencies

### Prerequisites
- WP-04 first-order-link pruning complete.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`.
- WP-00 harness artifacts under `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/` and `tools/ifolp_wp00_*`.
- Existing WP-05 mismatch evidence in `mismatch_disposition.md`.

### Blocks
- WP-06 robustness hardening and WP-07 optimization should consume parity outcomes from WP-05.

## Related Packages
- **Depends on**: [20260413_ifolp_wp04_first_order_link_pruning](../20260413_ifolp_wp04_first_order_link_pruning/package.md)
- **Related**: [20260412_ifolp_wp00_parity_harness](../20260412_ifolp_wp00_parity_harness/package.md)
- **Follow-up**: WP-06 Error Contract + Robustness Hardening.

## Timeline Estimate
- **Expected duration**: 1-3 focused sessions.
- **Complexity**: High.
- **Risk level**: High.

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: internal raster parity verification/tests only; no auth/secrets/public boundary changes.
- **Security review artifact**: `N/A`

## References
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `/workdir/weppcloud-wbt/AGENTS.md`
- `/workdir/weppcloud-wbt/DEVELOPING_TOOLS.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/fixture-catalog.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/parity-metrics-spec.md`

## Deliverables
- `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/package.md`
- `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/tracker.md`
- `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/hypothesis_log.md`
- `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/mismatch_disposition.md`
- `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/prompts/completed/ifolp_wp05_topaz_parity_validation_execplan.md`
- `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/prompts/completed/ifolp_wp05_pruning_drift_remediation_execplan.md`
- `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/prompts/completed/ifolp_wp05_pruning_drift_remediation_execplan_closure_20260414.md`
- WP-05 remediation parity artifacts and post-test review-disposition evidence.

## Follow-up Work
- Start WP-06 robustness hardening after WP-05 mismatch remediation outcomes are accepted.
- Use retained IFOLP WP-05 state (H-002 + H-009 + H-010 + H-011; canonical hash `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1`) as the parity baseline for all follow-on packages unless explicitly superseded.

## Kickoff Prompt
- WP-05 closed; latest remediation ExecPlan is archived at `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/prompts/completed/ifolp_wp05_pruning_drift_remediation_execplan_closure_20260414.md`
