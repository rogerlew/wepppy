# Iterative First-Order Link Prune WP-01 Tool Scaffolding

**Status**: Open (2026-04-13)
**Timezone**: UTC

## Overview
This package governs execution of WP-01 for Iterative First-Order Link Prune in `/workdir/weppcloud-wbt`. WP-01 delivers the initial tool skeleton, registration wiring, and argument/help scaffolding so the command is discoverable and invokable before core algorithm implementation begins.

## Objectives
- Create the `iterative_first_order_link_prune` tool skeleton in WBT.
- Register the tool in stream-network and global tool registries.
- Implement argument parsing/help metadata scaffolding aligned with the WP spec.
- Add parser/contract tests for required arguments and defaults.

## Scope
This package is limited to WP-01 in `weppcloud-wbt`.

### Included
- Tool file creation at `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs`.
- Registration updates in:
  - `whitebox-tools-app/src/tools/stream_network_analysis/mod.rs`
  - `whitebox-tools-app/src/tools/mod.rs`
- Initial `run` scaffolding with placeholders for phase-A/phase-B processing.
- CLI/interface contract updates and parser behavior tests.
- WP-01 orchestration table row completion in WBT implementation plan.

### Explicitly Out of Scope
- Core topology or pruning logic (WP-02+).
- TopAZ parity validation package work (WP-05).
- Performance/multithreading optimization work (WP-07).
- WEPPpy integration work.

## Stakeholders
- **Primary**: WEPPcloud WBT maintainers.
- **Reviewers**: stream-network-analysis maintainers.
- **Security Reviewer**: not required for this package scope.
- **Informed**: WEPPpy maintainers coordinating IFOLP rollout sequencing.

## Success Criteria
- [ ] Tool skeleton exists at the specified WBT path and compiles.
- [ ] Tool is registered and discoverable via WBT command listing/help.
- [ ] Required argument parsing and help metadata are implemented per spec contract.
- [ ] Parser/default/required-arg tests pass for WP-01 scope.
- [ ] `cargo check -p whitebox_tools` passes with WP-01 changes.
- [ ] WP-01 row in WBT implementation plan is updated to `done` with review/test gates complete.

## Dependencies

### Prerequisites
- WP-00 complete artifacts in `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/`.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`.
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`.

### Blocks
- WP-02 cannot begin until WP-01 tool contract and registration are complete.

## Related Packages
- **Depends on**: [20260412_ifolp_wp00_parity_harness](../20260412_ifolp_wp00_parity_harness/package.md)
- **Related**: `docs/work-packages/20260403_roads_map_drilldown/package.md` (execution process pattern)
- **Follow-up**: WP-02 package for deterministic topology kernel implementation.

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: WBT internal CLI scaffolding only; no auth/secrets/public boundary changes.
- **Security review artifact**: `N/A`

## References
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`
- `/workdir/weppcloud-wbt/AGENTS.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`
- `/workdir/weppcloud-wbt/DEVELOPING_TOOLS.md`

## Deliverables
- `docs/work-packages/20260412_ifolp_wp01_tool_scaffolding/package.md`
- `docs/work-packages/20260412_ifolp_wp01_tool_scaffolding/tracker.md`
- `docs/work-packages/20260412_ifolp_wp01_tool_scaffolding/prompts/active/ifolp_wp01_tool_scaffolding_execplan.md`
- WBT WP-01 scaffolding code and tests (in `/workdir/weppcloud-wbt`).

## Follow-up Work
- Begin WP-02 topology kernel once WP-01 scaffolding is merged and stable.

## Kickoff Prompt
- Active ExecPlan: `docs/work-packages/20260412_ifolp_wp01_tool_scaffolding/prompts/active/ifolp_wp01_tool_scaffolding_execplan.md`
