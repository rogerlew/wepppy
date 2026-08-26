# Project Config Reader Foundation (WP02)

**Status**: Closed (2026-08-26)
**Timezone**: UTC
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate

## Overview

WP02 teaches every NoDb configuration reader to recognize a valid flattened
project-owned config and load it without shared fallback. It also validates the
version-1 provenance manifest, reports safe structured degradation warnings,
and makes the validated top-level run root authoritative for nested projects.
This package adds readers only; it does not create or amend project configs.

## Objectives

- Add default-off flattened-config recognition with explicit schema failures.
- Preserve legacy local/shared resolution exactly when the marker is absent.
- Validate manifest v1 and expose deduplicated, secret-safe status warnings.
- Preserve child-local legacy configs while safely inheriting parent authority.
- Inventory and prove the common web/RQ reader boundary through NoDb fixtures.

## Scope

### Included

- `wepppy/nodb/base.py` reader integration and nested containment semantics.
- A focused project-config reader collaborator and typed public test seams.
- Manifest schema/digest status, structured logging, and update-disable state.
- Reader feature flags, deterministic unit/integration fixtures, and docs.

### Explicitly Out of Scope

- Project-owned config or manifest writers (WP04/WP06).
- Registry composition and serialization (WP03).
- Update APIs/jobs and authenticated header UI (WP08/WP09).
- Fork/archive/restore integration (WP10) and deployed fleet proof (WP11).

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extension of the central legacy reader.
- **Authoritative source paths**: `wepppy/nodb/base.py` and
  `docs/schemas/project-owned-config-contract.md` at revision `ceb10fc96`.
- **Cutover proof required**: the common NoDb accessor path uses the new reader
  when explicitly enabled, while disabled and unmarked paths retain legacy
  resolution.
- **Acceptance evidence type**: both fixtures and restarted development-stack
  evidence; deployed-fleet evidence remains WP11 scope.

## Owned Requirements

- PC-01, PC-08, and PC-16.
- Normative tasks N-001, N-002, N-005, N-013 through N-016, N-021, N-022,
  N-034, N-035, N-037, and N-073 through N-078.
- Regression tasks R-001, R-015 through R-017, R-026, R-034, and A-001.

## Compatibility and Regression Plan

This package changes run-scoped configuration authority but does not change
persisted NoDb keys, config tokens, option names, or parameter values. The
reader remains default-off and legacy behavior remains the disabled-path and
unmarked-file baseline. With the reader enabled, only a local file explicitly
marked `[config] flattened = true` enters flattened mode; it is parsed alone,
never layered with defaults or shared presets, and malformed/unsupported schema
fails without fallback. A valid flattened file remains usable when its manifest
is missing, malformed, secret-bearing, filename-inconsistent, newer-schema, or
digest-inconsistent; updates are disabled and warnings expose identifiers and
digests but no contents. Nested fixtures cover child-local legacy precedence,
validated persisted parent authority, sibling/prefix escape rejection, and
shared fallback. Tests compare legacy parser contents and direct NoDb accessors,
assert no file mutation, and exercise representative web/RQ-facing controller
loads. No generated `wepp/runs/*` artifacts change because WP02 is reader-only;
fixture inspection proves config and manifest bytes are unchanged by reads.

## Success Criteria

- [x] Flattened configs load alone and unsupported/malformed schema fails.
- [x] Manifest degradation and digest mismatch are warning-only for loading.
- [x] Warnings are structured, secret-safe, and deduplicated per controller.
- [x] Nested authority is containment-validated and preserves legacy children.
- [x] Reader flag is default-off and no writer or read-triggered mutation exists.
- [x] Focused, NoDb, full-suite, docs, security, correctness, and stack gates pass.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes
- **Rationale**: authority and validation change; no defaults, formulas,
  thresholds, conversions, heuristics, or effective values are altered.

## Dependencies

- **Depends on**: WP00R and closed WP01 at `ceb10fc96`.
- **Available prerequisites**: WP00A sanitization and WP00B normalization.
- **Blocks**: WP04, WP05, WP08, WP09, WP10, and WP11.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: config/manifest path authority, containment, and
  secret-safe logging are filesystem and data-boundary changes.
- **Security review artifact**:
  `artifacts/2026-08-26_security_review.md`.

## References

- `docs/schemas/project-owned-config-contract.md` sections 5, 6.1, 6.4, 10,
  14, and 15.
- `docs/schemas/project-owned-config-implementation-roadmap.md` WP02.
- `docs/work-packages/20260804_project_config_contract_ratification/artifacts/normative_requirement_checklist.md`.

## Deliverables

- Reader collaborator and NoDb facade integration.
- Manifest/status and nested-authority fixtures.
- Reader inventory, correctness/security reviews, and WP11 handoff evidence.

## Follow-up Work

- WP03 supplies registry/serializer behavior; WP04 is the first writer.
- WP09 owns authenticated header presentation; WP11 owns deployed acceptance.

## Closure Notes

**Closed**: 2026-08-26

**Summary**: WP02 implemented and wired a default-off, reader-only foundation
for flattened project configs. The common NoDb facade now recognizes schema v1,
loads it without shared fallback, validates manifest v1 into immutable status,
keeps digest mismatch warning-only, and inherits one containment-validated root
for nested controllers while preserving child-local legacy configs. The work
also removed the preexisting string-prefix containment weakness. No writer,
route, queue edge, or read-triggered mutation was added.

**Evidence**: `artifacts/2026-08-26_reader_foundation_evidence.md`,
`artifacts/2026-08-26_correctness_review.md`, and
`artifacts/2026-08-26_security_review.md`.

**Implementation revision**: recorded by the WP02 closing commit and follow-up
revision note.

**Promotion state**: implemented on `feature/project-owned-config`; the reader
flag remains deployment-default-off and the work is neither Forest accepted nor
promoted to `master`.

**Lessons Learned**: compatibility requires preserving failure types and token
parsing, not only successful effective values. Direct-child names also require
resolved-path checks when they become runtime authority.

**Archive Status**: package, reviews, evidence, and completed ExecPlan retained.
