# Tracker - Project Config Locale and View Authority (WP12B)

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-27 06:12 UTC
**Current phase**: Closed
**Last updated**: 2026-08-27 13:21 UTC
**Next milestone**: WP12 production-acceptance handoff
**Security impact**: `high`
**Dedicated security review**: `yes`
**Parameterization ADR**: `docs/adrs/ADR-0047-project-config-locale-authority.md`

## Task Board

### In Progress

None.

### Pending

None.

### Blocked

None.

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
- [x] Deployed revision `3e8d0d09bcf5` to exact host `forest` by restarting the
  development services without building an image; web and rq-engine health
  checks passed.
- [x] Created and reopened Builder run `matted-smooth`, proving durable
  `continental-us` normalizes to runtime `us` and stored schema-v2 authority
  drives all five run-scoped discovery surfaces.
- [x] Proved all advertised data/executable providers are present and healthy,
  all 72 WEPP provider values resolve both executable roles, and real GDAL,
  WBT fill, TOPAZ channel, and default WEPP watershed/hillslope executions
  succeed.
- [x] Rejected an unsupported landuse dataset with diagnostic HTTP 400 and no
  controller state, revision, ETag, or persisted-selection change.
- [x] Recorded Forest acceptance, closed WP12B, and handed the accepted
  revision to WP12. Production remains unchanged.

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

### 2026-08-27 13:13 UTC: Accept WP12B on Forest and retain the wider WP12 gate

**Decision**: Accept the one Builder-exposed profile after revision-bound
provider presence, run creation/reopen, stored discovery, no-mutation rejection,
and representative real provider-family execution. Do not treat this as the
wider contract's production acceptance or deploy it to production.

**Rationale**: WP12B proves the locale-authority feature and its complete
Builder exposure population. WP12 remains the explicit owner of production
promotion and the per-binary/full-project operational matrix.

## Follow-up

- Repair the unrelated file-isolation auditor failure involving the
  profile-recorder Flask stub and JSON serialization. This does not reopen
  WP12B unless a later run identifies a WP12B-scoped isolation failure.
- Correct the TerrainProcessor BLC integration test so its helper arguments
  honor the fail-on-unresolved diagnostics contract, and prevent failed WBT
  calls from leaking their process working directory into later tests. WP12
  must exercise BLC and Multiple OFE on a suitable real project; WP12B does not
  claim that execution.
