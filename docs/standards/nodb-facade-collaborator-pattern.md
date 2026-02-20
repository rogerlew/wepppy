# NoDb Facade + Collaborator Pattern

## Purpose

Use this standard when refactoring a NoDb controller monolith into collaborator
modules while preserving public facade behavior.

This pattern is contract-first:

1. The facade class remains the public entrypoint.
2. Collaborators stay internal implementation details.
3. Extraction happens in small, test-backed steps.

## Scope

Applies to NoDb controllers under `wepppy/nodb/core/` (for example `Wepp`,
`Climate`, and future controllers using the same extraction style).

## Non-Negotiable Contracts

1. Preserve public facade contracts.
   Facade methods/properties used by routes, RQ jobs, and tests must keep
   behavior unless a package explicitly approves a contract change.
2. Preserve lock and mutation boundaries.
   Keep `with self.locked()` placement, `nodb_setter` behavior, and
   `dump_and_unlock` semantics stable.
3. Preserve persistence and side effects.
   Do not move persistence across route/RQ boundaries without explicit approval.
4. Keep failures explicit.
   Do not add silent fallbacks that hide missing dependencies or bad state.

## Option-2 Extraction Sequence (Required)

Use this sequence unless a package documents and approves a different order:

1. Input parsing and validation service.
2. Build router or orchestrator.
3. Mode-specific build services.
4. Scaling service.
5. Artifact export service.
6. Station or catalog resolution service.

Each step should be independently testable and reversible.

## Implementation Conventions

1. Collaborators live in `wepppy/nodb/core/` and use focused names like
   `<Controller><Domain>Service`, `<Controller>BuildRouter`, or
   `<Controller>InputParser`.
2. Keep module-level collaborator singletons on the facade module when existing
   tests monkeypatch those seams (for example `_CLIMATE_SCALING_SERVICE`).
3. Facade methods stay thin wrappers that enforce lock/persistence boundaries
   and delegate focused logic to collaborators.
4. Avoid speculative abstractions; extract only proven cohesive logic.
5. Keep shared enums/contracts where callers already import them unless
   migration is explicitly planned.

## Exception and Logging Rules

1. No bare `except:` and no broad `except Exception` in production flow unless
   the catch is a true boundary.
2. Catch expected exception types (for example `OSError`) and log with context.
3. Never swallow errors silently. If continuing is intentional, document why in
   a short boundary comment and emit structured logging (`exc_info=True` when
   useful).

## Test and Validation Requirements

1. Add/maintain facade characterization tests for route/RQ-facing behavior.
2. Add collaborator unit tests for each extracted branch (success + key
   failures).
3. Add regression tests for lock/mutation/persistence behavior affected by the
   extraction.
4. If integration suites are environment-gated and may skip, add deterministic
   non-skipped tests for the same acceptance paths.
5. Run focused iteration tests and final gate:
   `wctl run-pytest tests --maxfail=1`.

## Reviewer Checklist

- Facade API and side effects unchanged unless explicitly approved.
- Locking and persistence boundaries preserved.
- Collaborator responsibilities are cohesive and non-overlapping.
- No silent exception swallow paths introduced.
- Regression tests cover the exact extracted/fixed paths.

## References

- `wepppy/nodb/AGENTS.md`
- `docs/mini-work-packages/completed/20260220_nodb_wepp_option2_refactor_execplan.md`
- `docs/mini-work-packages/20260220_nodb_climate_option2_facade_execplan.md`
