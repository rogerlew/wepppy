# Tracker — PRISM temperature ordering

## Quick status

**Started / updated**: 2026-10-13 23:52 UTC
**Phase**: Planning complete; implementation not started
**Next milestone**: M1 reviewed contract checkpoint
**Security impact**: low; dedicated security artifact not required under current scope
**Plan**: [ExecPlan](prompts/active/prism_temperature_ordering_execplan.md)

## Task board

- [x] Operator accepted midpoint proposal and requested implementation work-package plus ADR.
- [x] Scope all four writers, candidate evidence, native build, compatibility, and consumer validation.
- [x] Accept ADR-0092 for implementation; retain explicit conformance-pending status.
- [ ] M1: Current contracts, exact diagnostic fields, two independent reviews, and ancestor checkpoint commit.
- [ ] M2: Rust daily and three Python paths; analytical and serializer regression tests.
- [ ] M3: Rebuilt extension provenance, project/consumer validation, non-EDDE case, retained 24-case parity, WEPP and performance evidence.
- [ ] M4: Required gates, correctness review, final docs and handoff.

## Decisions

2026-10-13 23:52 UTC, operator/Codex conversation: carry out the evaluated midpoint correction through a dedicated package and ADR. Valid adjusted extrema remain untouched; only finite crossed extrema collapse to their midpoint before existing serialization. Preserve daily midpoint rather than choosing one extreme arbitrarily; do not invent a positive range floor or redesign all-day variability. ADR-0092 owns the durable numerical rule.

The authoring request creates planning artifacts, not production completion or deployment authorization. The prior proposal and prototype do not satisfy the independent contract checkpoint or rebuilt-native-path acceptance gates. No new branch is required or authorized.

## Risks and verification

Primary risks: missing the Rust production path, Python/Rust rounding differences, accidental changes to valid weather or breakpoint records, and stale extension imports. Require generated-content comparisons and exact consumed-artifact evidence. The EDDE study's full suite stopped at an unrelated SBS metadata assertion; rerun/report current results without changing unrelated behavior.

The finite acceptance matrix and rollback criteria are in [package.md](package.md). No external execution blocker has been established; source/build inspection belongs to M1/M3. Temporary mitigation layers: none. Retire only the EDDE introduced-inversion rejection after repair validation.

## Progress

2026-10-13 23:52 UTC: authored package and active plan, promoted existing ADR-0092 from proposal to accepted implementation decision, and linked parent/successor packages. Runtime code and native artifacts remain unchanged. Scoped documentation lint passed for the package, ADR, ADR index, and root tracker; spelling preview and git diff whitespace checks were clean. No runtime tests are required for this documentation-only change.
