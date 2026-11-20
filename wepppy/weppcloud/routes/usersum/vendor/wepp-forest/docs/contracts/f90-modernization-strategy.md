# `.f90` Modernization Strategy and Quality Gates

Date: 2026-05-03
Repository: `/workdir/wepp-forest`

## Normative Status

- This document is normative for `.f90` authoring and modification workflows.
- It defines modernization phases, coding standards, linting policy, and review gates.
- This policy is additive to existing runtime/release gates in `AGENTS.md`.

## Scope

Applies to:

- new `.f90` source units under `src/`,
- `.for`/`.inc` to `.f90` migration work,
- tests and tooling introduced to validate `.f90` behavior.

Does not replace:

- release/vendoring gates for `wepp` and `wepp_hill`,
- ablation protocol requirements for incident-driven numerical stabilization.

## Modernization Principles

1. Preserve behavior contracts first; modernize structure second.
2. Separate translation from logic changes wherever possible.
3. Keep release build path stable (`make` remains the production path).
4. Use explicit interfaces and typed boundaries for new `.f90` code.
5. Treat legacy runtime behavior as evidence baseline, not automatic authority.
6. Preserve trajectory ownership: one production row, routine invocation, and
   binary call chain must be owned by one coherent trajectory.
7. Treat modernization as a public-release strategy grounded in scientific
   accountability: record provenance, publish reproducible artifacts, replace
   legacy implementation paths with process/specification/test-driven code, and
   retire legacy trajectories promptly after acceptance gates clear.

## Build and Packaging Strategy

### Production build path

- Canonical release binaries continue to come from `src/makefile`.
- `make` gates remain the authority for vendored binary promotion.

### `fpm` adoption path

- `fpm` is adopted as a modernization/test harness, not as immediate replacement
  for release build orchestration.
- Bootstrap status (active):
  - manifest: `fpm.toml`,
  - bootstrap source harness: `fpm-src/`,
  - bootstrap tests: `fpm-test/`.
- Initial `fpm` usage focuses on:
  - compiling modular `.f90` rewrite units,
  - running unit/integration tests quickly in local and CI loops.
- Any future `fpm` promotion to release build authority requires an explicit
  cross-repo decision and parity evidence against `make` outputs.

## Phase Plan

0. **Contract and baseline capture**
   - Freeze affected runtime/output contracts.
   - Capture baseline behavior from legacy implementation on replay corpus.

1. **Structural translation**
   - Convert selected units to `.f90` with no intended logic changes.
   - Keep adapters compatible with current include/common-block contracts.

2. **Unit isolation and targeted testing**
   - Extract testable kernels and add deterministic unit tests.
   - Validate parity against baseline artifacts for touched surfaces.

3. **Controlled behavior improvements**
   - Apply approved bug fixes with explicit divergence disposition tags.
   - Re-run parity/audit gates before merging.

4. **Consolidation**
   - Remove duplicated legacy pathways only after parity and downstream
     contract confidence are established.

## `.f90` Coding Standards

### Language and file conventions

- New source files use `.f90` (or `.F90` only when preprocessing is required).
- Prefer one module/program/submodule per file.
- File/module naming should be lowercase and consistent.

### Required code-level practices

- `implicit none` required in every program unit.
- Explicit `intent(...)` on all dummy arguments.
- Prefer explicit kind usage (`iso_fortran_env`) over legacy kind syntax.
- Prefer explicit interfaces/modules over implicit external procedure usage.
- Avoid introducing new obsolescent constructs (`common`, `pause`, `entry`,
  arithmetic `if`, computed `goto`) in modernized code.

### Transitional compatibility rules

- Existing include/common-block contracts may be consumed by adapters during
  migration phases.
- New `.f90` kernels should accept explicit inputs/outputs and avoid hidden file
  or global mode probing.

### Migration header requirements

- All migrated `.f90` source follows:
  - `docs/contracts/f90-migration-header-schema.md`

### Trajectory ownership requirements

- All subsystem cutover and legacy retirement work follows:
  - `docs/contracts/trajectory-ownership-contract.md`
- Field-by-field comparison may be used as evidence; field-by-field production
  cutover is prohibited. Adapters may only cross coherent ownership boundaries
  during active modernization, and must preserve the single-trajectory
  invariant.

## Linting and Formatting Policy

### Linter

- Fortitude is the standard lint engine for `.f90` modernization work.
- Preferred invocation:
  - `fortitude check <touched .f90/.F90 files>`
  - `fortitude check --fix <touched .f90/.F90 files>` (safe fixes only unless explicitly approved)
- During rollout phases 1-2, do **not** require repo-wide Fortitude pass as a
  merge gate; lint gates are scoped to touched `.f90/.F90` files.

Configuration location:

- `fortitude.toml` or `.fortitude.toml` at repository root, or
- `[extra.fortitude.*]` inside `fpm.toml` when using fpm-based configuration.
- Current repository baseline uses root `fortitude.toml`.

### Rollout model

1. Advisory mode on touched `.f90` files.
2. Required pass on touched `.f90` files.
3. Broader repo-level enforcement after debt burn-down and explicit policy update.

### Formatter

- Auto-formatting is optional and non-authoritative during initial rollout.
- If used, formatter changes should be isolated from logic edits whenever possible.

## Testing Strategy

### Unit tests

- Use `fpm test` for fast local regression cycles on `.f90` kernels/modules.
- Use `test-drive` as default lightweight unit-test framework for serial tests.

### Parallel/MPI tests

- Use `pFUnit` where MPI/parallel behavior must be validated at unit-test level.
- Keep `pFUnit` usage scoped to cases that need it due to setup complexity.

### Runtime regression and parity

- Existing pytest and replay/parity tooling remain mandatory for release-facing
  behavior confidence.
- `.f90` test success does not waive required runtime replay gates.

## Mandatory Review Gates for `.f90` Tasks

For `.f90` authoring/modification tasks, both reviews are required before
handoff:

1. `f90_code_reviewer` (primary correctness gate)
2. `f90_qa_reviewer` (secondary quality/lint/test gate)

Gate intent:

- prevent numerical/contract regressions,
- enforce modernization standards consistently,
- keep style/lint/test debt from accumulating during migration.

Role definitions live in:

- `.codex/agents/f90_code_reviewer.toml`
- `.codex/agents/f90_qa_reviewer.toml`

## Minimum Merge Checklist for `.f90` Changes

1. Migration header compliance confirmed.
2. Build/test evidence reported (at minimum targeted tests for touched behavior).
3. Fortitude lint run on touched `.f90` files (or documented exception).
4. `f90_code_reviewer` findings resolved or explicitly accepted.
5. `f90_qa_reviewer` findings resolved or explicitly accepted.
6. Downstream parity/contract impact documented when behavior changes.
7. Trajectory ownership impact documented for any source unit that owns or
   exports model state.
8. Legacy retirement or retention disposition recorded when a migrated unit
   replaces an active legacy path.

## References

- `AGENTS.md`
- `src/AGENTS.md`
- `docs/contracts/f90-migration-header-schema.md`
- `docs/contracts/trajectory-ownership-contract.md`
