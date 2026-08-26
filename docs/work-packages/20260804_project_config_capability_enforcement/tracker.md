# Tracker - Project Config Capability Enforcement (WP05)

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-26 21:20 UTC
**Current phase**: Complete
**Last updated**: 2026-08-26 21:48 UTC
**Next milestone**: WP06 builder API
**Security impact**: `high`
**Dedicated security review**: required
**Starting revision**: `9d7956259`
**Initiative branch**: `feature/project-owned-config`
**Upstream state at start**: ahead 4

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Verified WP02/WP03/WP04 prerequisites and contract ownership (2026-08-26 21:20 UTC).
- [x] Recorded compatibility and generated-artifact regression plan before implementation edits (2026-08-26 21:20 UTC).
- [x] Completed endpoint inventory and shared capability authority (2026-08-26 21:31 UTC).
- [x] Wired snapshot population and paired climate/soil/land-use enforcement (2026-08-26 21:38 UTC).
- [x] Passed 94 focused tests and exact suite (6,888 passed, 63 skipped) plus all static/docs gates (2026-08-26 21:48 UTC).

## Requirement Ledger

| Contract area | Tasks | Planned evidence | Status |
| --- | --- | --- | --- |
| Capability resolution | N-004, N-068, N-069 | generated stable-ID section and exact mapping tests | complete |
| Paired enforcement | N-070, R-049 | UI/server parity and hidden-submit rejection | complete |
| Legacy carve-out | N-071, N-072 | persisted-state and legacy project regression | complete |

## Decisions Log

### 2026-08-26 21:20 UTC: Enforce only recognized flattened authorities

**Decision**: A missing capability section remains legacy behavior. A valid
flattened config with capabilities uses those IDs for new choices, while its
already persisted NoDb selection remains displayable and routable.

**Rationale**: This is the contract's explicit compatibility boundary and
prevents a dormant rollout from changing existing projects.

### 2026-08-26 21:20 UTC: Use explicit stable-ID/runtime mappings

**Decision**: Define stable IDs and their current runtime catalog IDs or enum
values explicitly rather than deriving them from UI labels or enum positions.

**Rationale**: Climate catalog IDs are already semantic; soil enums contain
aliases; land-use database tokens need durable identifiers.

## Risks and Issues

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| UI hides a choice that server still accepts | High | paired matrix and parity tests | Open |
| Current persisted choice becomes unusable | High | explicit persisted-state carve-out | Open |
| Legacy project behavior changes | High | absent-section bypass tests | Open |
| Nested run reads the wrong config | High | WP02 top-level authority helper/tests | Open |
| Numeric enum becomes durable capability ID | Medium | explicit semantic-ID schema tests | Open |

## Verification Checklist

- [x] Generated snapshot contains semantic IDs and reopens through WP02.
- [x] Every inventoried UI/server pair has parity evidence.
- [x] Hidden submissions fail before NoDb mutation or RQ enqueue.
- [x] Legacy and persisted-selection carve-outs pass.
- [x] Correctness and dedicated security artifacts have no unresolved findings.
- [x] Writer/enforcement rollout remains dormant by default.

## Watch List

- WP06 must reuse these stable IDs in builder descriptions and submissions.
- WP11 owns deployed endpoint exercise, mixed readers, and Forest evidence.
