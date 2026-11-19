# Soil input capacity 23 tracker

Status: active, 2026-11-19 UTC.

## Progress

- [x] Native eleven-horizon experiment and national inventory completed separately.
- [x] Dedicated implementation branches/worktrees created; package scaffolded.
- [ ] ADR, contracts and consumer inventory.
- [ ] Native 23-horizon implementation, metadata and committed fixtures.
- [ ] Native targeted/full gates and original-input parity.
- [ ] Executable-aware Python integration and writer/consumer regressions.
- [ ] Paired release provenance, full Python gates and review findings closure.
- [ ] Isolated original-project workflow and output readback.
- [ ] Release/rollback preparation and final evidence handoff.

## Decisions

2026-11-19 UTC: user authorized scaffolding and executing the complete agreed
scope. Use `mxhzin=23`, keep `mxnsl=10`, no merging or conductivity edits. Preserve
shared checkout WIP and existing binary/project defaults. Use separate task
worktrees based on completed evaluation; source-lineage integration remains an
explicit release gate.

## Evidence and blockers

Evidence will be retained in `artifacts/` and task-owned external output roots.
No blocker established yet. Remote integration, publication, deployment and
original production incident recovery are distinct from local implementation.
