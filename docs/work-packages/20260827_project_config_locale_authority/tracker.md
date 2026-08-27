# Tracker - Project Config Locale and View Authority (WP12B)

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-27 06:12 UTC
**Current phase**: Forest acceptance and final evidence
**Last updated**: 2026-08-27 12:59 UTC
**Next milestone**: Forest acceptance and file-isolation audit disposition
**Security impact**: `high`
**Dedicated security review**: `yes`
**Parameterization ADR**: `docs/adrs/ADR-0047-project-config-locale-authority.md`

## Task Board

### In Progress

- [ ] Pass Forest deployed-provider and representative execution acceptance.
- [ ] Complete the file-isolation audit after the unrelated checker failure.

### Pending

- [ ] Close WP12B after Forest evidence is recorded.

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
- [x] Committed the standalone contract checkpoint as `4a975657f`.
- [x] Implemented 16 typed profiles, complete provider definition identities,
  WEPP role-resolved executable provenance, schema-v2
  graph serialization/validation, and `continental-us` -> `us` normalization.
- [x] Wired Builder/run views and Flask/RQ mutation/discovery boundaries to the
  stored graph, including Multiple OFE landuse adjacency and full WEPP provider
  authority.
- [x] Added generated round-trip, hostile v2, v1/legacy compatibility,
  no-mutation, discovery, and frontend graph tests.
- [x] Passed 533 touched Python tests, the 220-test authority subset, and the
  71-test Builder matrix.
- [x] Passed frontend lint and all 107 suites / 792 tests.
- [x] Passed schema stubtest, stub completeness, broad-exception enforcement,
  endpoint inventory, and route-contract checklist guards.
- [x] Received Ready dispositions from independent implementation correctness,
  contract correctness, security, and governance reviews.
- [x] Passed the full Python suite: 7,034 passed and 63 skipped.
- [x] Passed isolation seeds 42, 123, 999, 1337, and 8,675,309. The subsequent
  parallel file audit aborted on an unrelated profile-recorder Flask-stub
  collection failure plus checker JSON-serialization defect; all WP12B
  project-config/locale-authority modules reported `Isolated OK` beforehand.

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

### 2026-08-27 09:02 UTC: Correct the provider inventory, do not invent support

**Decision**: Record 163 landcover entries and omit eMapR 1983 because the live
provider's range ends at 1984. Map Tenerife's lowercase CORINE spelling to the
same stable identity as the canonical provider spelling.

**Rationale**: The typed authority must describe executable provider behavior,
not preserve a checkpoint transcription error or create an unshipped dataset.
