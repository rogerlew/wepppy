# Tracker – Direct OpenFileGDB cutover

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-21 15:38 UTC
**Current phase**: Implementation complete; review and rollout pending
**Last updated**: 2026-08-21 16:17 UTC
**Next milestone**: Independent review and forest rollout
**Security impact**: `high`
**Dedicated security review**: `yes`

## Task Board

### Ready / Backlog

- [ ] Complete external GIS-client characterization.
- [ ] Complete independent correctness, QA, and security reviews.
- [ ] Deploy and smoke on forest; deploy to production only with separate
  operator authorization.

### In Progress

- [ ] None.

### Blocked

- [ ] External ArcGIS interoperability evidence requires an ArcGIS-capable
  operator or test environment; GDAL readback does not replace this check.

### Done

- [x] Inventoried runtime, compatibility, Docker, CI, deployment, stub, test,
  and documentation references (2026-08-21 15:38 UTC).
- [x] Verified GDAL 3.10.3 OpenFileGDB vector create/update support in the batch
  worker on wepp1 and forest (2026-08-21 15:38 UTC).
- [x] Completed a direct two-layer GeoPackage-to-OpenFileGDB write and update
  readback on both hosts (2026-08-21 15:38 UTC).
- [x] Operator selected direct OpenFileGDB and accepted documented output
  caveats (2026-08-21 15:45 UTC).
- [x] Amended the canonical specification and implemented the direct bounded
  OpenFileGDB conversion boundary (2026-08-21 16:17 UTC).
- [x] Preserved the legacy input alias and `.gdb.zip` contract while changing
  ZIP members to a first-level `.gdb/` directory (2026-08-21 16:17 UTC).
- [x] Removed runtime compatibility modules and all live SDK/sidecar build,
  Compose, CI, host setup, and deployment wiring (2026-08-21 16:17 UTC).
- [x] Passed focused tests, direct GDAL and zipped readback, supported Compose
  renders, import/stub hygiene, exception, vulture, shell, and code-quality
  gates (2026-08-21 16:17 UTC).
- [x] Characterized empty spatial and populated geometryless/nullable layers
  through direct conversion and readback (2026-08-21 16:17 UTC).

## Decisions Log

### 2026-08-21 15:45 UTC: Replace FileGDB SDK with direct OpenFileGDB

**Context**: GDAL 3.10.3 in the common worker image reports native
OpenFileGDB write/update support and passed direct host smoke tests. The old
sidecar runs GDAL 3.0.0 with Esri's FileGDB SDK.

**Decision**: Call `OpenFileGDB` explicitly in the normal runtime and remove
the sidecar after parity validation. Retain the legacy `f_esri` request alias
but remove implementation symbols and infrastructure carrying that name.

**Impact**: The export path no longer requires the Esri SDK, a Docker socket
hop, or a permanently idle container. Output equivalence is behavioral rather
than byte-identical.

### 2026-08-21 15:45 UTC: Prefer broad ArcGIS compatibility

**Context**: OpenFileGDB defaults convert Integer64 fields to Float64. Setting
`TARGET_ARCGIS_VERSION=ARCGIS_PRO_3_2_OR_LATER` preserves Integer64 but narrows
client compatibility. The old FileGDB driver also lacks Integer64 support.

**Decision**: Keep OpenFileGDB's default compatibility mode for this cutover.

**Impact**: Integer64-to-Float64 warnings and exact-value checks become
explicit test evidence; native Integer64 output is deferred.

## Risks and Issues

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Accidentally retaining `-f FileGDB` still requires the missing SDK on GDAL 3.10 | High | Assert explicit `OpenFileGDB` selection in tests | Open |
| Schema or geometry behavior differs from SDK output | High | Representative source/output characterization and external-client smoke | Open |
| ZIP root layout is not accepted after extraction | High | Inspect member paths and exercise normal download/extract/open workflow | Open |
| Direct subprocess loses old timeout/error behavior | Medium | Preserve bounded subprocess execution and contextual stdout/stderr | Open |
| Direct output inherits worker umask/ownership differences | Medium | Run under deployed worker identity on mounted run storage | Open |
| Removing a Compose dependency breaks a variant | High | Render dev, HPC, base prod, wepp1, and worker configurations | Open |
| Existing cached GDB artifacts become invalid | Medium | Keep format/cache/archive contracts and test legacy artifacts | Open |

The existing-cache risk is mitigated by leaving the cache validator and public
filename contract unchanged. It remains open until forest exercises a legacy
artifact and a newly generated artifact through the download route.

## Verification Checklist

### Code Quality

- [x] Focused exporter/service tests pass.
- [x] Stub completeness and import checks pass.
- [ ] Broad Python suite is clean apart from documented unrelated harness and
  fixture blockers.
- [x] Changed broad-exception and quality observability checks are reviewed.

### Security and Correctness

- [x] Direct command uses argument arrays, resolved paths, bounded timeout, and
  explicit failure behavior.
- [x] Run-scope containment, partial cleanup, archive contents, permissions,
  and hostile filenames are reviewed.
- [ ] Correctness and security artifacts have no unresolved medium/high
  findings.

### Deployment

- [x] Every supported Compose configuration renders without `f-esri`.
- [x] Common and worker Dockerfiles contain no SDK/vendor residue.
- [ ] Forest export smoke passes.
- [ ] Production deployment is separately authorized and validated.

## Progress Notes

### 2026-08-21 15:45 UTC: Feasibility and package scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Identified the direct runtime and infrastructure coupling.
- Verified GDAL and functional write support on wepp1 and forest.
- Recorded the operator's output-policy decision and scaffolded the package.

**Blockers encountered**: No implementation blocker. External ArcGIS readback
remains an acceptance dependency.

**Next steps**: Amend the canonical features-export specification, add direct
conversion characterization, then implement the replacement before removing
infrastructure.

**Test results**: Host feasibility smoke passed on both targets; no repository
tests were run because this session changed planning documentation only.

### 2026-08-21 16:17 UTC: Direct backend implementation and validation

**Agent/Contributor**: Codex

**Work completed**:

- Implemented native OpenFileGDB conversion and migrated both runtime callers.
- Removed the SDK sidecar and repository-wide live infrastructure coupling.
- Made `.gdb.zip` directly GDAL-readable with a first-level `.gdb/` member.
- Added direct success, schema/value, capability, timeout, diagnostic cleanup,
  permission, archive-layout, and zipped-readback coverage.

**Blockers encountered**:

- The container Docker CLI lacks the Compose plugin; the two canary Compose
  tests pass in the host virtualenv and supported stack renders pass directly.
- The broad suite passed 4,528 tests before an unrelated Topanga test found a
  mounted authority directory but a missing tracked study manifest. The
  remaining WEPP/WEPPcloud selection passed 1,630 tests with only that exact
  case deselected.
- `stubtest wepppy.all_your_base.geo` is blocked before surface comparison by
  existing untyped-GDAL, tuple-return, enum-stub, and webclient-export errors;
  `wctl check-test-stubs` passes.

**Next steps**: Independent reviews, empty-layer/external-client evidence,
forest rollout, then separately authorized production/Kubernetes promotion.

**Test results**: Focused 98 passed before subtraction; backend 6 passed after
final packaging; broad 4,528 passed/61 skipped before unrelated fixture failure;
remaining 1,630 passed/2 skipped/1 deselected; host canary 2 passed.
