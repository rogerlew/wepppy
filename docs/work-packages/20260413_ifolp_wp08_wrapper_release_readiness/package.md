# Iterative First-Order Link Prune WP-08 WBT Wrapper Exposure + Release Readiness

**Status**: Closed (2026-04-13)
**Timezone**: UTC

## Overview
This package governs execution of WP-08 for Iterative First-Order Link Prune in `/workdir/weppcloud-wbt`. WP-08 exposes/validates IFOLP through wrapper and release-facing surfaces, then closes release-readiness gates with mandatory review and findings disposition.

## Objectives
- Verify IFOLP wrapper exposure and release-surface readiness.
- Validate wrapper/CLI contract consistency for retained behavior.
- Complete release-readiness checks and artifact updates.
- Require formal review findings/disposition before package close.

## Scope
This package is limited to WP-08 release-readiness work in `weppcloud-wbt`.

### Included
- Wrapper exposure verification for IFOLP (CLI + Python wrapper surfaces).
- Release-readiness contract checks (help text, argument behavior, packaging-facing smoke tests).
- Parity-regression spot checks against retained baseline artifacts.
- Documentation and orchestration updates for release readiness.
- Mandatory review/disposition artifact with severity closure gates.

### Explicitly Out of Scope
- New pruning semantics or algorithm changes.
- Additional optimization redesign (WP-07 scope).
- WEPPpy integration rollout beyond WBT wrapper/package readiness.

## Stakeholders
- **Primary**: WEPPcloud WBT maintainers.
- **Reviewers**: stream-network-analysis maintainers and release reviewers.
- **Security Reviewer**: not required for this package scope.
- **Informed**: WEPPpy maintainers coordinating IFOLP rollout.

## Baseline Contract (Required)
WP-08 validation must preserve retained IFOLP behavior from WP-05/WP-06/WP-07.

Retained baseline evidence:
- Canonical basin-masked retained artifact hash: `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`.
- Retained code state: WP-05 semantics + WP-06 hardening + WP-07 optimization.

## Success Criteria
- [x] IFOLP wrapper surfaces are verified callable and contract-consistent.
- [x] Wrapper/CLI smoke checks pass for expected arguments and help text.
- [x] Parity-regression spot checks show no retained-state drift.
- [x] Release-readiness docs/orchestration rows are updated.
- [x] Review findings are dispositioned with no unresolved high/medium issues.
- [x] Required gates pass (`cargo check`, targeted IFOLP tests, wrapper sanity checks).
- [x] WP-08 row in WBT implementation plan is updated with closure evidence.

## Dependencies

### Prerequisites
- WP-05 closed (retained parity baseline accepted).
- WP-06 closed (error-contract hardening complete).
- WP-07 closed (optimization/perf gates complete).
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`.

### Blocks
- Final IFOLP release handoff depends on WP-08 closure.

## Related Packages
- **Depends on**: [20260413_ifolp_wp07_optimization_pass](../20260413_ifolp_wp07_optimization_pass/package.md)
- **Related**: [20260413_ifolp_wp06_error_contract_robustness_hardening](../20260413_ifolp_wp06_error_contract_robustness_hardening/package.md)

## Timeline Estimate
- **Expected duration**: 1-3 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: release-surface validation only; no auth/secrets/public boundary changes.
- **Security review artifact**: `N/A`

## References
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `/workdir/weppcloud-wbt/AGENTS.md`
- `/workdir/weppcloud-wbt/DEVELOPING_TOOLS.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Deliverables
- `docs/work-packages/20260413_ifolp_wp08_wrapper_release_readiness/package.md`
- `docs/work-packages/20260413_ifolp_wp08_wrapper_release_readiness/tracker.md`
- `docs/work-packages/20260413_ifolp_wp08_wrapper_release_readiness/review_disposition.md`
- `docs/work-packages/20260413_ifolp_wp08_wrapper_release_readiness/prompts/completed/ifolp_wp08_wrapper_release_readiness_execplan.md`
- WP-08 wrapper/release-readiness evidence bundle.

## Follow-up Work
- Promote IFOLP as release-ready in downstream planning once WP-08 closes.

## Kickoff Prompt
- Completed ExecPlan archive: `docs/work-packages/20260413_ifolp_wp08_wrapper_release_readiness/prompts/completed/ifolp_wp08_wrapper_release_readiness_execplan.md`
