# Direct OpenFileGDB cutover

**Status**: Open (2026-08-21)
**Timezone**: UTC

## Overview

Replace the proprietary Esri FileGDB SDK sidecar path with GDAL 3.10.3's
built-in `OpenFileGDB` writer. The cutover removes the idle `f-esri` container,
Docker-socket subprocess hop, vendored SDK image, and `wepppy.f_esri` runtime
coupling while preserving the public `geodatabase` export token and
`.gdb.zip` artifact contract.

The operator accepted the documented OpenFileGDB output caveats on 2026-08-21.
The implementation must request `OpenFileGDB` explicitly; GDAL 3.10 does not
delegate `-f FileGDB` creation to OpenFileGDB.

## Objectives

- Convert staged GeoPackages directly with the runtime image's
  `OpenFileGDB` driver.
- Preserve geodatabase requests, archive names, cache behavior, manifests,
  published profiles, and the legacy input alias `f_esri`.
- Remove the `f-esri` service, image build, SDK/vendor wiring, Docker
  dependencies, host setup, CI inputs, compatibility APIs, and obsolete tests.
- Prove representative export, failure, permission, cleanup, and deployment
  behavior on development and production-equivalent stacks.

## Scope

### Included

- `wepppy/nodb/mods/features_export` conversion and capability boundaries.
- Removal of `wepppy/f_esri`, the root compatibility module, and obsolete
  `all_your_base.geo` wrappers after call-site migration.
- Dockerfiles, Compose variants, deployment automation, host setup, CI build
  arguments, stubs, tests, and affected documentation.
- Direct GDAL capability and conversion tests plus representative artifact
  comparison.
- Forest deployment validation followed by a separately authorized production
  deployment and post-deployment validation.

### Explicitly Out of Scope

- Renaming the public `geodatabase` format or `.gdb.zip` artifact members.
- Removing the accepted legacy request alias `f_esri`; it is data/API
  compatibility, not a runtime dependency.
- Adding a replacement geospatial dependency or pure-Python writer.
- Changing unrelated ESRI shapefile, projection, basemap, or flow-pointer code.
- Promising byte-identical FileGDB output or support for every ArcGIS release.

## Implementation Fidelity and Evidence

**Target**: faithful behavioral replacement, not byte-for-byte artifact
identity.

Implementation is not closable until a current runtime image generates a
real `.gdb.zip`, its layers and representative values are read back, the
archive passes the existing download/cache contract, and an external GIS
consumer smoke test is recorded. Synthetic driver discovery alone is
insufficient.

## Accepted Output Policy

- Use GDAL's default broad ArcGIS compatibility behavior initially.
- Accept the default conversion of source `Integer64` fields to `Float64`.
  This matches the material limitation of the old SDK-backed FileGDB driver
  more closely than requiring ArcGIS Pro 3.2+.
- Do not set `TARGET_ARCGIS_VERSION=ARCGIS_PRO_3_2_OR_LATER` unless a later
  contract decision explicitly trades older-client compatibility for native
  64-bit integer fields.
- Preserve field values within the supported exact-integer range and record
  warnings from GDAL rather than suppressing them.

## Success Criteria

- [x] No production code imports or invokes `wepppy.f_esri`.
- [x] Conversion explicitly selects `OpenFileGDB` and fails clearly when the
  driver lacks vector-create capability.
- [x] Direct conversion has bounded runtime, contextual error reporting, safe
  partial-output cleanup, and correct run-tree ownership/modes.
- [x] Representative multi-layer, empty-layer, geometryless, nullable,
  integer, floating, text, CRS, and geometry cases pass readback.
- [ ] Existing and newly generated `.gdb.zip` artifacts remain downloadable
  and cache-valid without forced regeneration.
- [ ] ArcGIS Pro or another operator-approved external GIS client opens a
  generated archive after normal extraction.
- [x] All `f-esri` service, SDK image, vendor, setup, CI, and deployment wiring
  is removed from every supported stack.
- [ ] Focused tests, Compose rendering, broad pre-handoff tests, correctness
  review, security review, forest smoke, and authorized production smoke pass.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Rationale**: this replaces an artifact backend; no scientific default,
  formula, threshold, unit conversion, or fallback heuristic changes.

## Dependencies

### Prerequisites

- Runtime images remain on GDAL 3.10.3 or a validated newer release.
- `OpenFileGDB` reports vector create/update support in every worker image that
  can execute features-export jobs.

### Blocks

- Removal of the `wepppy-f-esri` image/container from deployed hosts.

## Related Packages

- **Related**: `docs/work-packages/20260329_features_export_legacy_exports_cutover/`
- **Related**: `docs/work-packages/20260813_weppcloud_private_canary_image/`

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: deployment wiring and worker subprocess execution
  change, and generated files are written and packaged under run-scoped paths.
- **Security artifact**:
  `artifacts/2026-08-21_security_review.md` (create during implementation)
- **Correctness artifact**:
  `artifacts/2026-08-21_correctness_review.md` (create during implementation)

## References

- `artifacts/2026-08-21_feasibility_inventory.md`
- `prompts/active/openfilegdb_cutover_execplan.md`
- `wepppy/nodb/mods/features_export/specification.md`
- `docker/docker-compose.dev.yml`
- `docker/docker-compose.prod.yml`
- [GDAL OpenFileGDB driver documentation](https://gdal.org/en/stable/drivers/vector/openfilegdb.html)
- [GDAL FileGDB driver documentation](https://gdal.org/en/stable/drivers/vector/filegdb.html)

## Implementation Status

Repository implementation and local validation completed on 2026-08-21.
Independent correctness/security review, external GIS-client evidence, forest
rollout, and separately authorized
production/Kubernetes promotion remain before package closure.
