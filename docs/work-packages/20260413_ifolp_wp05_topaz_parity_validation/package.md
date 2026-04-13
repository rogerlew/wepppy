# Iterative First-Order Link Prune WP-05 TopAZ Parity Validation

**Status**: Open (2026-04-13)
**Timezone**: UTC

## Overview
This package governs execution of WP-05 for Iterative First-Order Link Prune in `/workdir/weppcloud-wbt`. WP-05 validates IFOLP parity against checksum-pinned TopAZ oracle outputs using the WP-00 harness, produces deterministic parity reports, and dispositions parity findings with reproducible evidence.

## Objectives
- Run a clean-room parity campaign against TopAZ oracle rasters for approved fixtures.
- Verify deterministic rerun behavior for canonical parity output.
- Disposition mismatches with explicit severity, root-cause category, and fix/accept/defer status.
- Complete a formal code-review findings/disposition phase before package close.

## Scope
This package is limited to WP-05 parity work in `weppcloud-wbt`.

### Included
- Fixture preparation and checksum verification using WP-00 harness tooling.
- Oracle capture verification from pinned `netw0.tif` artifacts.
- Candidate IFOLP output generation for each fixture.
- Metric comparison using `tools/ifolp_wp00_compare_outputs.py`.
- Determinism rerun evidence using canonical report hashing.
- Mismatch triage and any required parity-fix follow-through in IFOLP modules.
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
- [ ] Fixture manifest includes required anchor fixture `/wc1/runs/cl/clueless-aftertaste/dem/wbt`.
- [ ] Candidate IFOLP outputs are generated for all fixtures in the WP-00 manifest.
- [ ] Parity comparison report is generated with canonical summary output.
- [ ] Determinism rerun yields identical canonical parity hash.
- [ ] Mismatches are dispositioned with explicit severity and root-cause category.
- [ ] Code-review findings are dispositioned with no unresolved high/medium issues.
- [ ] `cargo check -p whitebox_tools` and targeted IFOLP tests pass after any parity fixes.
- [ ] WP-05 row in WBT implementation plan is updated to `done` with review/test/parity gates complete.

## Dependencies

### Prerequisites
- WP-04 first-order-link pruning complete.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`.
- WP-00 harness artifacts under `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/` and `tools/ifolp_wp00_*`.

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
- `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/prompts/active/ifolp_wp05_topaz_parity_validation_execplan.md`
- WP-05 parity report artifacts and review-disposition evidence.

## Follow-up Work
- Start WP-06 robustness hardening after parity outcomes are accepted.

## Kickoff Prompt
- Active ExecPlan: `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/prompts/active/ifolp_wp05_topaz_parity_validation_execplan.md`
