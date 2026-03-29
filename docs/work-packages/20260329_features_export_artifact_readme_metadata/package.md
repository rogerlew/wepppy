# Features Export Artifact README Metadata Packaging

**Status**: Closed (2026-03-29)

## Overview
This package adds deterministic, dynamically generated artifact `README.md` files to all `features_export` zip products. The README will be derived from resolved export metadata (manifest/request/layer/dependency context), aligned to geospatial metadata standards guidance, and packaged alongside `manifest.json` and payload members.

## Objectives
- Generate artifact-level `README.md` dynamically during features-export publication.
- Include the generated README in every artifact zip bundle (`cache_miss` publication path).
- Keep `manifest.json` as the machine-readable source of truth while ensuring README values are consistent derivatives.
- Align README section coverage with geospatial metadata best-practice baselines (FGDC CSDGM essential elements, ISO 19115-1 orientation, GeoParquet/GeoPackage/GeoJSON format semantics).
- Add regression tests for packaging membership, README content shape, and cache-hit reuse behavior.

## Scope

### Included
- `wepppy/nodb/mods/features_export/specification.md` contract updates for README packaging and standards alignment.
- New README builder/helper implementation in `wepppy/nodb/mods/features_export/`.
- Service orchestration changes in `wepppy/nodb/mods/features_export/service.py` to generate and package README during artifact publication.
- Manifest-field alignment if needed for README provenance pointers.
- Regression tests in `tests/nodb/mods/test_features_export_service.py` and related manifest/packaging suites.
- Work-package tracker and ExecPlan updates through completion.

### Explicitly Out of Scope
- New export data-layer families or selector modes.
- Introduction of profile-file bundling (`profile.yml`, built-in profile files remain excluded).
- API route contract changes outside README packaging metadata additions.
- Introducing external metadata dependencies or online lookups at export time.

## Stakeholders
- **Primary**: NoDb `features_export` maintainers and Runs-page operators.
- **Reviewers**: rq-engine route owners, QA reviewers for export artifact contracts.
- **Informed**: users relying on downloadable artifact provenance and reproducibility.

## Success Criteria
- [x] Every features-export zip artifact contains payload members, `manifest.json`, and generated `README.md`.
- [x] README generation is deterministic for identical resolved inputs and contains standards-aligned metadata sections.
- [x] README content matches manifest values (no contract drift).
- [x] Cache-hit jobs reuse existing artifact README without regenerating divergent bundle content.
- [x] Targeted backend regression suites pass.
- [x] Package tracker, ExecPlan, and closeout artifacts are complete.

## Dependencies

### Prerequisites
- Current `features_export` service and manifest baseline from:
  - `docs/work-packages/20260328_features_export_service_compliance_refactor/`
  - `docs/work-packages/20260329_features_export_legacy_exports_cutover/`
- Updated standards/readme contract text in `wepppy/nodb/mods/features_export/specification.md`.

### Blocks
- Follow-on metadata enhancements (PID/license/contact/bbox/temporal-extent enrichment) that build on README infrastructure.

## Related Packages
- **Related**: [20260328_features_export_profiles_provenance_zip](../20260328_features_export_profiles_provenance_zip/package.md)
- **Related**: [20260328_features_export_service_compliance_refactor](../20260328_features_export_service_compliance_refactor/package.md)
- **Depends on**: [20260329_features_export_legacy_exports_cutover](../20260329_features_export_legacy_exports_cutover/package.md)
- **Follow-up**: metadata enrichment package for PID/license/contact/extent augmentation.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium.

## References
- `wepppy/nodb/mods/features_export/specification.md` - source-of-truth contract (includes standards baseline and README requirements).
- `wepppy/nodb/mods/features_export/service.py` - artifact packaging orchestration path.
- `wepppy/nodb/mods/features_export/manifest.py` - machine-readable metadata contract.
- `tests/nodb/mods/test_features_export_service.py` - service/packaging regression coverage.
- `tests/nodb/mods/test_features_export_manifest.py` - manifest contract regression coverage.

## Deliverables
- Work-package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- Dynamic README builder implementation and service integration.
- Regression tests for README package membership/content consistency.
- Updated specification/tracker/ExecPlan with closure notes.

## Follow-up Work
- Add optional PID/license/contact fields to manifest and README once authoritative ownership contracts are finalized.
- Evaluate layer-level `bbox` and temporal extent aggregation for richer metadata summaries.
- Evaluate optional internal export of standards-native XML/JSON records (ISO/FGDC profile documents) if required by downstream catalogs.
