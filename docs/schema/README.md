# Contract Documentation Guidance (`docs/schema/`)

## Purpose

Use `docs/schema/` for module-level contract docs as we formalize behavior through ablation testing and stabilization work.

This directory is for implementation-near contracts (for example, specific routines/modules), not broad API/platform schemas.

## Relationship to `docs/schemas/`

- `docs/schemas/` remains the canonical location for cross-subsystem, user/operator-facing, and API-wide contracts.
- `docs/schema/` is the working set for module contracts and routine-level behavior guarantees.
- When a module contract becomes externally normative, either:
  - promote it into `docs/schemas/`, or
  - keep it in `docs/schema/` and add an explicit pointer from the relevant `docs/schemas/*` contract.

## File Naming Convention

- One contract per file.
- Preferred name: `<module_or_routine>.schema.md`.
- Examples: `locate.schema.md`, `frostn.schema.md`, `wshdrv.schema.md`.

## Required Contract Sections

Every module contract SHOULD include at least:

1. `Normative Status`
2. `Scope`
3. `Inputs and Units`
4. `Output Invariants`
5. `Boundary and Error Semantics`
6. `Observability and Debug Signals`
7. `Compatibility and Change Management`
8. `Validation Requirements`
9. `Implementation References`

## Normative Language

Use RFC-2119-style terms consistently:

- `MUST`, `MUST NOT`
- `SHOULD`, `SHOULD NOT`
- `MAY`

If implementation and contract diverge, the same change set MUST either:

- update implementation to match the contract, or
- update the contract to match the intended implementation.

## Authoring Rules

- Prefer precise invariants over prose explanation.
- Specify units explicitly (for example, `m`, `mm`, `kg/m^3`).
- Specify boundary behavior explicitly (clamp, reject, fail, or fallback).
- Document whether behavior is containment-only vs. scientifically authoritative.
- Avoid silent fallback semantics unless intentional and justified.

## Change-Set Rules

When behavior changes in a contracted module:

1. Update the contract in the same PR.
2. Add or update regression tests for the changed behavior.
3. Record observability impacts (new tags/counters/log volume).
4. Call out residual risks and follow-up work.

## Minimal Template

```md
# <module> Contract

## Normative Status

## Scope

## Inputs and Units

## Output Invariants

## Boundary and Error Semantics

## Observability and Debug Signals

## Compatibility and Change Management

## Validation Requirements

## Implementation References
```
