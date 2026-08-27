# Tracker - Project Config Locale and View Authority (WP12B)

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-27 06:12 UTC
**Current phase**: Contract checkpoint
**Last updated**: 2026-08-27 07:14 UTC
**Next milestone**: Standalone contract checkpoint commit, then implementation
**Security impact**: `high`
**Dedicated security review**: `yes`
**Parameterization ADR**: `docs/adrs/ADR-0047-project-config-locale-authority.md`

## Task Board

### In Progress

- [ ] Ratify the canonical locale/dependency/view-authority contract.

### Pending

- [ ] Implement the canonical locale profile catalog and dependency closure.
- [ ] Expand flattened capability axes and normalize `continental-us`.
- [ ] Wire paired UI and server enforcement.
- [ ] Pass generated-matrix, security, correctness, and Forest gates.

### Blocked

- WP12 production cutover is blocked on WP12B closure.

### Done

- [x] Inventoried the current Builder registry, climate/landuse catalogs,
  flattened capability reader, templates, and paired endpoints.
- [x] Recorded the operator's WP12B scope and no-migration requirement.
- [x] Dispositioned first correctness/governance review findings by adding a
  closed inventory, stored graph edges/tuples, profile composition/state rules,
  compatibility matrix, exact endpoint boundary, and checkpoint artifacts.
- [x] Received final Ready dispositions from independent correctness,
  governance, and high-impact security reviewers.

## Decisions Log

### 2026-08-27 06:12 UTC: Per-project capabilities remain run-view authority

**Decision**: Builder pages consume the current validated registry. Once a run
is created, its flattened `[capabilities]` section—not the live registry—drives
view rendering and server validation.

**Rationale**: This preserves snapshot independence while ensuring presentation
and mutation share one authority.

### 2026-08-27 06:12 UTC: Preserve the `continental-us` stable ID

**Decision**: Normalize `continental-us` into the canonical locale profile
schema without renaming it to the runtime token `us`.

**Rationale**: Stable component IDs are durable provenance. A profile may map
to one or more runtime locale tokens without adopting those tokens as its ID.
