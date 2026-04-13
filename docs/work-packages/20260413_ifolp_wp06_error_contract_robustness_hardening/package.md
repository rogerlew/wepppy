# Iterative First-Order Link Prune WP-06 Error Contract + Robustness Hardening

**Status**: Open (2026-04-13)
**Timezone**: UTC

## Overview
This package governs execution of WP-06 for Iterative First-Order Link Prune in `/workdir/weppcloud-wbt`. WP-06 hardens IFOLP error contracts and robustness paths after WP-05 parity closure, while preserving the retained WP-05 algorithm as the parity baseline.

## Objectives
- Harden IFOLP error contracts for invalid/missing/degenerate runtime states.
- Add deterministic robustness behavior for recoverable edge cases.
- Expand targeted negative-path and regression tests.
- Require mandatory code-review findings/disposition before package close.

## Scope
This package is limited to WP-06 hardening work in `weppcloud-wbt`.

### Included
- IFOLP error-message and failure-path contract hardening in parser/prep/phase boundaries.
- Robustness checks for stale/degenerate/no-channel/invalid-threshold conditions.
- Targeted regression and negative-path test coverage.
- Parity-regression checks that use the retained WP-05 IFOLP state as baseline.
- WP-06 implementation-plan row updates and review-disposition evidence.

### Explicitly Out of Scope
- New pruning semantics or parity-model redesign.
- Performance/multithreading optimization scope (WP-07).
- Wrapper/release-readiness scope (WP-08).
- WEPPpy integration work.

## Stakeholders
- **Primary**: WEPPcloud WBT maintainers.
- **Reviewers**: stream-network-analysis maintainers and parity reviewers.
- **Security Reviewer**: not required for this package scope.
- **Informed**: WEPPpy maintainers coordinating IFOLP rollout.

## Baseline Contract (Required)
All WP-06 parity checks must use the retained WP-05 IFOLP algorithm as baseline unless an explicit superseding package changes this rule.

Retained baseline evidence:
- Deterministic basin-masked canonical hash: `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1`.
- Retained code state: H-002 + H-009 + H-010 + H-011.

## Success Criteria
- [ ] Error-contract behaviors are explicitly defined and implemented for all targeted negative paths.
- [ ] Robustness changes preserve retained WP-05 parity baseline semantics.
- [ ] Targeted IFOLP tests include new negative-path and regression cases.
- [ ] Parity-regression evidence confirms no unintended drift from retained baseline.
- [ ] Code-review findings are dispositioned with no unresolved high/medium issues.
- [ ] `cargo check -p whitebox_tools` and targeted IFOLP tests pass.
- [ ] WP-06 row in WBT implementation plan is updated with review/test/parity gate states.

## Dependencies

### Prerequisites
- WP-05 closed with accepted effective parity equivalence.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`.
- WP-00/WP-05 parity harness tooling and reports.

### Blocks
- WP-07 optimization should consume WP-06 hardened contracts.
- WP-08 release readiness should consume WP-06 hardened failure behavior.

## Related Packages
- **Depends on**: [20260413_ifolp_wp05_topaz_parity_validation](../20260413_ifolp_wp05_topaz_parity_validation/package.md)
- **Related**: [20260412_ifolp_wp00_parity_harness](../20260412_ifolp_wp00_parity_harness/package.md)
- **Follow-up**: WP-07 Optimization Pass.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: High.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: internal raster algorithm/error-path hardening only; no auth/secrets/public boundary changes.
- **Security review artifact**: `N/A`

## References
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `/workdir/weppcloud-wbt/AGENTS.md`
- `/workdir/weppcloud-wbt/DEVELOPING_TOOLS.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Deliverables
- `docs/work-packages/20260413_ifolp_wp06_error_contract_robustness_hardening/package.md`
- `docs/work-packages/20260413_ifolp_wp06_error_contract_robustness_hardening/tracker.md`
- `docs/work-packages/20260413_ifolp_wp06_error_contract_robustness_hardening/prompts/active/ifolp_wp06_error_contract_robustness_hardening_execplan.md`
- WP-06 hardening code/tests + review/disposition evidence.

## Follow-up Work
- Start WP-07 optimization after WP-06 hardening outcomes are accepted.

## Kickoff Prompt
- Active ExecPlan: `docs/work-packages/20260413_ifolp_wp06_error_contract_robustness_hardening/prompts/active/ifolp_wp06_error_contract_robustness_hardening_execplan.md`
