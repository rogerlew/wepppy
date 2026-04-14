# Iterative First-Order Link Prune WP-10 WEPPpy E2E Cutover (`ifolp` default + legacy selectable mode)

**Status**: Completed (2026-04-14)
**Timezone**: UTC

## Overview
This package executes the WEPPpy-side IFOLP cutover end-to-end: make IFOLP the default stream-pruning method, keep `remove_short_streams` as an explicit legacy option, and validate behavior through backend, UI, and integration gates. The package consumes the finalized IFOLP integration contract from `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wepppy-integration-plan.md`.

## Objectives
- Make `wbt_topaz_emulator` default to IFOLP while preserving explicit legacy selection (`ifolp` | `remove_short_streams`).
- Ensure IFOLP call-site contract includes explicit `max_junctions=3`.
- Add/verify watershed config + state plumbing for `stream_pruning_method` with stable compatibility behavior.
- Add/verify rq-engine parse/validate/pass-through semantics for `stream_pruning_method`.
- Add/verify WEPPcloud WBT control wiring and payload transmission for `Stream Pruning Method`.
- Complete required validation and review disposition with no unresolved high/medium findings.

## Scope
This package is limited to WEPPpy integration/cutover behavior and its validation artifacts.

### Included
- Emulator cutover wiring in `/workdir/wepppy/wepppy/topo/wbt/wbt_topaz_emulator.py` (+ related docs/types as needed).
- Watershed state/config plumbing in NoDb watershed model files.
- rq-engine payload/schema-defaults validation for `stream_pruning_method`.
- WEPPcloud controls + controller payload wiring and targeted frontend tests.
- Regression/method-matrix validation and closure review artifacts.

### Explicitly Out of Scope
- New IFOLP algorithm changes in Rust/WBT.
- Culvert migration to IFOLP unless explicitly chosen under Phase 4 disposition.
- Baseline redefinition for retained IFOLP parity without explicit stakeholder approval.

## Stakeholders
- **Primary**: WEPPpy topology maintainers.
- **Reviewers**: WEPPcloud frontend maintainers, rq-engine maintainers, IFOLP maintainers.
- **Security Reviewer**: optional (see triage below).
- **Informed**: operators and users depending on TOPAZ emulator channel delineation.

## Baseline Contract (Required)
- Retained IFOLP parity baseline hash remains authoritative for IFOLP algorithm behavior unless explicitly re-baselined:
  - `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`
- This package must not silently change IFOLP algorithm semantics in `/workdir/weppcloud-wbt`.

## Success Criteria
- [x] Emulator supports `stream_pruning_method` with default `ifolp` and selectable `remove_short_streams` legacy path.
- [x] IFOLP emulator invocation explicitly uses `max_junctions=3`.
- [x] Watershed config/state contract for `stream_pruning_method` is implemented and tested (default + invalid handling).
- [x] rq-engine route validation and mutation guard tests pass for method contract.
- [x] WEPPcloud control/payload wiring passes frontend tests for method selection propagation.
- [x] Required validation phase commands are executed and recorded in tracker artifacts.
- [x] Mandatory code review/disposition closes with no unresolved high/medium findings.

## Required Validation Phases

### Phase 1: Test Execution (Required)
Run and capture outcomes for:
- `wctl run-pytest tests/microservices/test_rq_engine_watershed_routes.py`
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py`
- `wctl run-pytest tests/topo/test_terrain_processor_wbt_integration.py`
- `wctl run-pytest tests/culverts/test_culvert_batch_rq.py`
- `wctl run-npm lint`
- `wctl run-npm test`

### Phase 2: Code Review and Disposition (Required)
- Perform independent review of implementation, tests, and contract docs.
- Disposition all findings by severity (`fixed`, `accepted-risk`, `deferred` with rationale).
- Closure gate: no unresolved high/medium findings.
- Record review evidence in WP-10 artifacts and tracker notes.

## Dependencies

### Prerequisites
- Closed IFOLP WP-00 through WP-09 packages.
- Updated IFOLP integration contract in `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wepppy-integration-plan.md`.

### Blocks
- WEPPpy rollout of IFOLP-default stream pruning behavior.

## Related Packages
- **Depends on**: [20260414_ifolp_wp09_max_junctions_support](../20260414_ifolp_wp09_max_junctions_support/package.md)
- **Related**: [20260413_ifolp_wp08_wrapper_release_readiness](../20260413_ifolp_wp08_wrapper_release_readiness/package.md)
- **Related**: [20260413_ifolp_wp05_topaz_parity_validation](../20260413_ifolp_wp05_topaz_parity_validation/package.md)

## Timeline Estimate
- **Expected duration**: 1-3 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: payload-validation and UI/control plumbing changes; no auth, secret, or permission-boundary redesign.
- **Security review artifact**: `N/A`

## References
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wepppy-integration-plan.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`

## Deliverables
- `docs/work-packages/20260414_ifolp_wp10_wepppy_e2e_cutover/package.md`
- `docs/work-packages/20260414_ifolp_wp10_wepppy_e2e_cutover/tracker.md`
- `docs/work-packages/20260414_ifolp_wp10_wepppy_e2e_cutover/prompts/completed/ifolp_wp10_wepppy_e2e_cutover_execplan.md` (at close)
- WP-10 test execution evidence (commands + pass/fail outcomes).
- WP-10 review/disposition artifact(s) with severity and closure state.
- Method-matrix validation notes for `ifolp` and `remove_short_streams` emulator paths.

## Closure Summary
- Implemented end-to-end IFOLP cutover with explicit legacy selection across watershed state, rq-engine mutation/default surfaces, RQ enqueue path, and WEPPcloud channel delineation controls.
- IFOLP call-site is explicit and deterministic: `iterative_first_order_link_prune(..., max_junctions=3)`.
- Required Phase 1 validation gates passed (see tracker for command outcomes).
- Method-matrix evidence captured in tests for both `ifolp` and `remove_short_streams`.
- Mandatory review/disposition completed with no unresolved high/medium findings.
- Active ExecPlan archived to `prompts/completed/ifolp_wp10_wepppy_e2e_cutover_execplan.md`.

## Follow-up Work
- If culvert strategy remains legacy, create follow-on package for explicit culvert migration or legacy pinning rationale refresh.

## Kickoff Prompt
- Completed ExecPlan: `docs/work-packages/20260414_ifolp_wp10_wepppy_e2e_cutover/prompts/completed/ifolp_wp10_wepppy_e2e_cutover_execplan.md`
