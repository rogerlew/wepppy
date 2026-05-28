# ExecPlan: Implement Conservative Second-Stage RUSLE K Gap Fill

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, runs with substantial off-channel POLARIS nodata islands should produce less spotty `K` coverage without introducing unconstrained interpolation. Users can verify this through updated manifest stage reports and passing regressions for stage-2 fill behavior.

## Progress

- [x] (2026-05-28 00:00 UTC) Created work-package scaffold and active ExecPlan.
- [x] (2026-05-28 00:22 UTC) Implemented two-stage conservative fill algorithm and manifest reporting updates.
- [x] (2026-05-28 00:30 UTC) Added regression tests for stage-2 fill-applied and stage-2 skip behavior.
- [x] (2026-05-28 00:40 UTC) Updated RUSLE specification/README and added parameterization ADR.
- [x] (2026-05-28 00:45 UTC) Ran targeted validation and closed package docs.

## Surprises & Discoveries

- Observation: In `/wc1/runs/st/strained-mod`, residual off-channel `K` gaps mapped to cells missing all 12 POLARIS layers.
  Evidence: local diagnostic overlap script run before package implementation.
- Observation: Existing checkerboard high-fraction tests now fail at stage-1 but naturally skip stage-2 because no medium-size candidates exist.
  Evidence: updated regression assertion needed to check nested stage reasons.

## Decision Log

- Decision: Use a separate stage-2 pass rather than changing stage-1 limits.
  Rationale: Preserves prior validated behavior and test expectations.
  Date/Author: 2026-05-28 00:00 UTC / Codex.
- Decision: Set stage-2 bounds to `65-4096` px, `<=5%` candidate fraction, `12` px search distance.
  Rationale: Conservative compromise between continuity improvement and overfill risk.
  Date/Author: 2026-05-28 00:22 UTC / Codex.

## Outcomes & Retrospective

The package achieved full scope. Runtime now performs a conservative second fill
stage for medium interior holes and reports stage-specific policy/outcomes in
manifest metadata. Regression coverage was expanded and targeted validation
passed.

## Context and Orientation

Primary implementation file: `wepppy/nodb/mods/rusle/k_integration.py`.
Primary regression file: `tests/nodb/mods/test_rusle_k_integration.py`.
Contract docs: `wepppy/nodb/mods/rusle/specification.md`,
`wepppy/nodb/mods/rusle/README.md`, and
`docs/adrs/ADR-0005-rusle-k-second-stage-gap-fill.md`.

## Plan of Work

Completed.

## Concrete Steps

Completed.

## Validation and Acceptance

Completed and passing:

- `wctl run-pytest tests/nodb/mods/test_rusle_k_integration.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_rusle_controller.py --maxfail=1`
- `wctl doc-lint` on changed docs/work-package/tracker files

## Idempotence and Recovery

Change is additive. If stage-2 appears too aggressive, disable stage-2 and
retain stage-1 behavior unchanged.

## Interfaces and Dependencies

No new dependencies were added.

## Revision Note

Updated on 2026-05-28 00:45 UTC to record completed implementation,
validation, and package closure.
