# Agent Prompt: Phase 6a (Watershed Touchpoint Review + Multi-Stage Plan)

## Mission
Review watershed NoDir touchpoints and produce an implementation-ready, multi-stage execution plan.

This is a planning phase. Do not implement broad production code changes beyond minimal doc updates required to publish the plan.

## Primary Deliverable
Update `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md`:
- Insert or refresh `### Phase 6a` as the authoritative watershed plan section.
- Ensure the section is concrete enough to drive follow-on implementation waves without re-discovery.

## Specs and Inputs (Read First)
Normative contracts:
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/schemas/nodir_interface_spec.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`

Touchpoint and scope inputs:
- `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md`
- `docs/work-packages/20260214_nodir_archives/tracker.md`
- `docs/work-packages/20260214_nodir_archives/notes/implementation_plan.md`

Code areas to audit (watershed-centric):
- `wepppy/nodb/core/watershed.py`
- `wepppy/topo/peridot/peridot_runner.py`
- `wepppy/topo/watershed_abstraction/`
- `wepppy/rq/` watershed-related routes/jobs
- `wepppy/export/` watershed consumers
- `wepppy/microservices/` FS-boundary watershed paths
- relevant `wepppy/nodb/mods/*` watershed consumers/producers

## Required Planning Output
Phase 6a must include:
1. Watershed touchpoint map by class:
- producer
- consumer
- FS-boundary
- serialized-path hazard

2. Behavior decision per touchpoint:
- native (dir/archive read path)
- thaw-required mutation path
- blocked/deferred (with rationale)

3. Multi-stage execution waves for watershed only:
- Wave 1 (lowest risk, high confidence)
- Wave 2
- Wave 3
- Wave 4 (hardening/cleanup)

4. Per-wave gates:
- code scope boundaries
- required tests
- failure/rollback notes
- explicit done criteria

5. Risks and unresolved decisions:
- list only concrete blockers that would stop implementation
- include decision owner and recommended default

## Constraints
- Keep scope tightly watershed-specific (this is 6a, not full Phase 6 for all roots).
- Do not introduce speculative abstractions.
- Align all proposed behavior with existing NoDir contracts and error matrix.
- If contracts are ambiguous, call out exact ambiguity and propose a default decision.

## Validation Steps
After doc updates:
```bash
wctl doc-lint --path docs/work-packages/20260214_nodir_archives
```

If you touched any code to validate assumptions, run targeted tests and report results, but avoid broad code modifications during this planning phase.

## Acceptance Criteria
- `### Phase 6a` in `implementation_plan.md` is complete, actionable, and watershed-only.
- Every watershed touchpoint is assigned to a wave with expected behavior.
- Plan includes test gates and rollback notes per wave.
- Doc lint passes.
