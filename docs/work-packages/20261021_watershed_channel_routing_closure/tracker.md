# Watershed channel routing closure tracker

**Started / updated**: 2026-10-21 16:42 UTC
**Phase**: Scaffold complete; execution pending
**Security impact**: none; dedicated security review not required

## Progress

- [x] Record investigation-only authority and simulation-change prohibition.
- [x] Scaffold package, active ExecPlan, and discovery links.
- [ ] M1: Inventory exact execution paths, provenance, boundaries, and hypotheses.
- [ ] M2: Add only necessary observations and prove three-way output parity.
- [ ] M3: Execute controlled and real-project closure ledgers and diagnostic controls.
- [ ] M4: Review findings, publish reproducible conclusions, and close investigation.

## Decisions

- 2026-10-21 16:42 UTC — Roger authorized observability but no simulation changes.
  Diagnosis is independent of remediation; no correction is required or permitted
  to make this investigation successful.
- 2026-10-21 16:42 UTC — Retain physical WAT, filtered PASS delivery, and routed
  outlet balances separately so threshold omissions cannot masquerade as area errors.

## Risks and blockers

No scaffold blockers. Original workbook inputs and matching historical executable
are not yet inventoried. No runtime closure or instrumentation parity claim exists.
Shared repository changes must be recorded and preserved during builds/replays.

## Validation

Scaffold validation passed: package doc-lint (3 files, zero errors/warnings),
root onboarding size check (160 lines), and `git diff --check`. Spelling
normalization was previewed and the single prose correction applied. Execution
must record build/test commands, artifact hashes, parity comparisons, diagnostic
controls, numerical tolerance rationale, and full-period coverage in artifacts.

## Next action

On execution authorization, begin M1 of the
[ExecPlan](prompts/active/watershed_channel_routing_closure_execplan.md).
