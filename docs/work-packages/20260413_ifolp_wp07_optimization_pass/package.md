# Iterative First-Order Link Prune WP-07 Optimization Pass

**Status**: Open (2026-04-13)
**Timezone**: UTC

## Overview
This package governs execution of WP-07 for Iterative First-Order Link Prune in `/workdir/weppcloud-wbt`. WP-07 targets performance improvements (multithreading and related optimizations) while preserving WP-05/WP-06 retained behavior through required parity-regression checks and mandatory code-review disposition.

## Objectives
- Improve IFOLP runtime performance on representative fixture workloads.
- Implement safe multithreading and related bounded optimizations.
- Preserve retained IFOLP behavior and deterministic parity outcomes.
- Complete formal review findings/disposition before package close.

## Scope
This package is limited to WP-07 optimization work in `weppcloud-wbt`.

### Included
- Baseline and post-change performance measurement on approved fixtures.
- Bounded optimization changes (including multithreading where justified).
- Deterministic parity-regression checks against retained baseline artifacts.
- Targeted regression tests for correctness and thread-safety-sensitive paths.
- WP-07 implementation-plan updates and review-disposition evidence.

### Explicitly Out of Scope
- New pruning-semantics redesign.
- Error-contract redesign beyond WP-06 hardened scope.
- Wrapper/release-readiness scope (WP-08).
- WEPPpy integration work.

## Stakeholders
- **Primary**: WEPPcloud WBT maintainers.
- **Reviewers**: stream-network-analysis maintainers and parity reviewers.
- **Security Reviewer**: not required for this package scope.
- **Informed**: WEPPpy maintainers coordinating IFOLP rollout.

## Baseline Contract (Required)
All WP-07 parity checks must preserve retained IFOLP behavior from WP-05/WP-06 unless an explicit superseding package changes baseline.

Retained baseline evidence:
- Canonical basin-masked retained artifact hash: `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83` (`/tmp/ifolp_wp05_remediate/run1,run2`).
- Retained code state: WP-05 retained semantics + WP-06 hardening guards.

## Success Criteria
- [ ] Baseline performance measurements are captured with reproducible commands.
- [ ] Optimization changes produce measurable improvement on target fixtures.
- [ ] Parity-regression evidence confirms no retained-state drift.
- [ ] Determinism and targeted IFOLP test coverage remain passing.
- [ ] Code-review findings are dispositioned with no unresolved high/medium issues.
- [ ] `cargo check -p whitebox_tools` and targeted IFOLP tests pass.
- [ ] WP-07 row in WBT implementation plan is updated with review/test/parity/perf gate states.

## Dependencies

### Prerequisites
- WP-05 closed (retained parity baseline accepted).
- WP-06 closed (error-contract hardening complete).
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`.

### Blocks
- WP-08 release readiness should consume WP-07 performance and parity outcomes.

## Related Packages
- **Depends on**: [20260413_ifolp_wp06_error_contract_robustness_hardening](../20260413_ifolp_wp06_error_contract_robustness_hardening/package.md)
- **Related**: [20260413_ifolp_wp05_topaz_parity_validation](../20260413_ifolp_wp05_topaz_parity_validation/package.md)
- **Follow-up**: WP-08 WBT Wrapper Exposure + Release Readiness.

## Timeline Estimate
- **Expected duration**: 2-5 focused sessions.
- **Complexity**: High.
- **Risk level**: High.

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: internal algorithm/performance behavior only; no auth/secrets/public boundary changes.
- **Security review artifact**: `N/A`

## References
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `/workdir/weppcloud-wbt/AGENTS.md`
- `/workdir/weppcloud-wbt/DEVELOPING_TOOLS.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Deliverables
- `docs/work-packages/20260413_ifolp_wp07_optimization_pass/package.md`
- `docs/work-packages/20260413_ifolp_wp07_optimization_pass/tracker.md`
- `docs/work-packages/20260413_ifolp_wp07_optimization_pass/prompts/active/ifolp_wp07_optimization_pass_execplan.md`
- WP-07 optimization code/tests + benchmark/parity/review evidence.

## Follow-up Work
- Start WP-08 release readiness after WP-07 optimization outcomes are accepted.

## Kickoff Prompt
- Active ExecPlan: `docs/work-packages/20260413_ifolp_wp07_optimization_pass/prompts/active/ifolp_wp07_optimization_pass_execplan.md`
