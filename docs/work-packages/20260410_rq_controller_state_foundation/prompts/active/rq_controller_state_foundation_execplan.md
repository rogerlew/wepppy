# RQ Controller State Foundation Freeze

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and is scoped to foundation hardening only (no runtime route implementation).

## Purpose / Big Picture

This package makes downstream implementation predictable by freezing contract invariants before code work begins. After this package, a new contributor should be able to start `setup_discovery`, `orchestration_reads`, and `schema_defaults` packages without guessing identifier semantics, descriptor requirements, or verification gates.

## Progress

- [x] (2026-04-09 20:54 PT) Created work-package scaffold and active ExecPlan file.
- [x] (2026-04-10 00:15 PT) Ran independent reviewer subagent pass and dispositioned findings in tracker/docs.
- [ ] Validate foundation assumptions against frozen artifacts `endpoint_inventory_freeze_20260208.md` and `route_contract_checklist_20260208.md`.
- [ ] Reconcile any remaining ambiguous MUST/SHOULD language in contract foundation sections.
- [ ] Confirm roadmap package dependencies and handoff criteria in package tracker/docs.
- [ ] Run documentation lint gates for package and contract docs.
- [x] (2026-04-10 00:15 PT) Requested independent subagent review and dispositioned findings.
- [ ] Publish final package handoff summary in tracker progress notes.

## Surprises & Discoveries

- Observation: None yet.
  Evidence: Package just initialized.

## Decision Log

- Decision: Keep this package documentation-only and defer all endpoint implementation to follow-on packages.
  Rationale: Reduces risk of mixed planning/implementation drift and preserves clean sequencing.
  Date/Author: 2026-04-10 / Codex

## Outcomes & Retrospective

- Pending package execution.

## Context and Orientation

The canonical contract draft is `docs/schemas/rq-controller-state-contract.md`. The companion contract is `docs/schemas/rq-engine-agent-api-contract.md`. Route and operation reality checks come from:

- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

This foundation package should align these references and define stable implementation guardrails. It should not modify rq-engine runtime code.

## Plan of Work

First, read the contract foundation sections and identify open ambiguities in identifier semantics, descriptor invariants, and rollout assumptions. Second, cross-check examples and required fields against frozen route inventory/checklist artifacts and note any mismatches. Third, update package tracker records with decisions and risks so follow-on packages have explicit starting criteria. Finally, run docs lint and request an independent subagent review to validate package quality and handoff readiness.

## Concrete Steps

Working directory: `/workdir/wepppy`

1. Review package and contract docs.
   - `nl -ba docs/work-packages/20260410_rq_controller_state_foundation/package.md`
   - `nl -ba docs/work-packages/20260410_rq_controller_state_foundation/tracker.md`
   - `nl -ba docs/schemas/rq-controller-state-contract.md`
2. Cross-check contract assumptions against frozen route artifacts.
   - `nl -ba docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
   - `nl -ba docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
3. Update tracker decisions/progress with any deltas.
4. Run validation.
   - `wctl doc-lint --path docs/work-packages/20260410_rq_controller_state_foundation/package.md --path docs/work-packages/20260410_rq_controller_state_foundation/tracker.md --path docs/work-packages/20260410_rq_controller_state_foundation/prompts/active/rq_controller_state_foundation_execplan.md --path docs/schemas/rq-controller-state-contract.md`
5. Run subagent review and disposition findings in tracker.

## Validation and Acceptance

Acceptance criteria:

- Package docs exist and match work-package conventions (`package.md`, `tracker.md`, active ExecPlan).
- Foundation scope, dependencies, and handoff criteria are explicit and testable.
- Documentation lint passes for package docs and touched contract docs.
- Independent subagent review is completed and findings are either fixed or explicitly documented.

## Idempotence and Recovery

All steps are documentation edits and can be repeated safely. If a change introduces inconsistency, revert only the specific doc section and re-run `wctl doc-lint` to validate recovery.

## Artifacts and Notes

Key artifact paths:

- `docs/work-packages/20260410_rq_controller_state_foundation/package.md`
- `docs/work-packages/20260410_rq_controller_state_foundation/tracker.md`
- `docs/work-packages/20260410_rq_controller_state_foundation/prompts/active/rq_controller_state_foundation_execplan.md`

## Interfaces and Dependencies

This package defines documentation interfaces consumed by follow-on packages:

- Contract baseline interface: `docs/schemas/rq-controller-state-contract.md`
- Companion contract interface: `docs/schemas/rq-engine-agent-api-contract.md`
- Route inventory baseline: `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
- Route checklist baseline: `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`

No runtime code interfaces are introduced in this package.

## Revision Note

- 2026-04-10 / Codex: Initial ExecPlan authored for package kickoff and handoff readiness.
