# Correctness and User-Experience Review - Direct OpenFileGDB cutover

## Metadata

- **Package**: `docs/work-packages/20260821_openfilegdb_cutover/`
- **Reviewer**: Codex preliminary self-review; independent review pending
- **Date**: 2026-08-21
- **Scope reviewed**: geodatabase writer, post-WEPP co-creation, archive/cache
  contract, compatibility alias, and removal wiring
- **Commit/branch context**: uncommitted local `master` based on `ed2b222fe`
- **Canonical contract**:
  `wepppy/nodb/mods/features_export/specification.md`, section 2 and WP-3
- **Related security artifact**: `2026-08-21_security_review.md`

## User Outcome

- **User goal**: request a geodatabase export and download a usable `.gdb.zip`.
- **Success presented to the user as**: unchanged `geodatabase` artifact and
  manifest metadata with a first-level `.gdb/` archive member.
- **Failures that may reach the user**: missing create capability, executable
  missing/not runnable, timeout, GDAL conversion diagnostics, missing output,
  or packaging failure.
- **Partial-state behavior**: exact target `.gdb` and incomplete ZIP are removed
  on timeout, conversion failure, missing output, or packaging failure; staging
  GeoPackage follows the existing artifact-job cleanup lifecycle.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Capability absent | no | explicit backend-unavailable failure | `test_conversion_fails_before_execution_without_create_capability` |
| Source absent | no | explicit `FileNotFoundError` before mutation | converter source guard |
| Empty layer | yes | retained as an empty FileGDB layer | Real OpenFileGDB integration test |
| Populated spatial source | yes | preserve layer, CRS, geometry, values | `test_real_openfilegdb_conversion_preserves_representative_values` |
| Geometryless/nullable multi-layer source | yes | existing staging writer contract preserved | exporter/service focused suite |
| Legacy `f_esri` request token | yes | normalize to `geodatabase` | planner/exporter tests |
| Failed/hostile executable result | no | contextual bounded failure and cleanup | timeout and diagnostic cleanup tests |
| Existing cached `.gdb.zip` | yes | remain cache-valid/downloadable | unchanged validator; forest evidence pending |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Driver cannot create | expected deployment error | backend unavailable | fail explicitly; no SDK fallback |
| Conversion exceeds 1,800 seconds | exceptional | timeout error | prevents indefinitely occupied workers |
| GDAL rejects source layer | exceptional | stdout/stderr-backed writer error | actionable conversion diagnostics |
| Packaging fails | exceptional | packaging error, no partial artifact | cache must never accept partial output |

## Review Checks

- [x] Canonical intent is named.
- [x] Empty spatial and geometryless/nullable states have direct characterization.
- [x] Input and filesystem failure states are reviewed separately.
- [x] Direct unmocked conversion, archive, schema/value, and readback run.
- [x] Failure-boundary mocks preserve the subprocess boundary under test.
- [x] Valid source state is not rejected by capability/cleanup controls.
- [x] Partial success and retry cleanup are explicit.
- [x] Error text is actionable.
- [x] Public format token, alias, artifact name, cache, and manifest remain.
- [x] No exhaustive-coverage claim is made.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-02 | Medium | External GIS client | GDAL direct readback passed, but ArcGIS/QGIS evidence is pending. | Package success criteria | Record forest/operator client smoke. | Open |
| COR-03 | Low | Existing cached artifact | Validator is unchanged, but download-route smoke with a legacy artifact is pending. | Service validator diff | Exercise on forest. | Open |

## Verdict

- **Gate status**: fail pending independent review and open findings
- **Unresolved findings**: High 0; Medium 1; Low 1
- **Release recommendation**: hold production rollout; implementation is ready
  for independent review and forest validation
- **Reviewer sign-off**: Codex preliminary self-review, 2026-08-21
