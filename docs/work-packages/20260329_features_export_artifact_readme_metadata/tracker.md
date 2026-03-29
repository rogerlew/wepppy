# Tracker - Features Export Artifact README Metadata Packaging

> Living document tracking progress, decisions, risks, and validation for dynamic features-export artifact README generation.

## Quick Status

**Started**: 2026-03-29  
**Current phase**: Complete (implementation + validation)  
**Last updated**: 2026-03-29 20:06Z  
**Active ExecPlan**: `prompts/active/features_export_artifact_readme_metadata_execplan.md`  
**Next milestone**: Package closeout handoff

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffold authored (`package.md`, `tracker.md`, active ExecPlan) (2026-03-29).
- [x] Updated `features_export` specification with standards baseline, metadata-gap assessment, and dynamic README artifact contract (2026-03-29).
- [x] Added deterministic README builder module (`wepppy/nodb/mods/features_export/readme_builder.py`) (2026-03-29 20:00Z).
- [x] Integrated cache-miss service packaging to generate and bundle `README.md` with payload members + `manifest.json` (2026-03-29 20:01Z).
- [x] Updated exports surface for README contracts (`FEATURES_EXPORT_ARTIFACT_README_NAME`, `build_export_readme`) (2026-03-29 20:01Z).
- [x] Added regression coverage for README zip membership, README/manifest consistency, cache-hit packaged-member propagation, and README deterministic redaction (2026-03-29 20:03Z).
- [x] Completed required validation suite and doc-lint checks (2026-03-29 20:06Z).

## Timeline

- **2026-03-29** - Package created and scoped for artifact README generation/plumbing.
- **2026-03-29** - Specification updated to include geospatial metadata standards baseline and README contract.
- **2026-03-29 20:00Z** - README builder implementation completed.
- **2026-03-29 20:01Z** - Cache-miss zip packaging updated to include generated `README.md`.
- **2026-03-29 20:03Z** - Regression tests expanded for README/manifest packaging consistency.
- **2026-03-29 20:06Z** - Validation and doc-lint gates passed.

## Decisions

### 2026-03-29: Keep `manifest.json` canonical and make `README.md` a deterministic derivative
**Context**: User-facing artifact metadata needs to be readable while preserving existing machine-readable contracts.

**Options considered**:
1. Move canonical metadata contract to README.
2. Keep canonical metadata in manifest and derive README from it.

**Decision**: Option 2.

**Impact**: Existing API/cache consumers continue to rely on manifest schema while humans get readable metadata in zip artifacts.

---

### 2026-03-29: Exclude profile files but include generated README
**Context**: Prior packaging changes oscillated around profile/provenance inclusion.

**Options considered**:
1. Bundle profile files + README together.
2. Keep bundles profile-file-free and include generated README + manifest only.

**Decision**: Option 2.

**Impact**: Preserves route-level profile replay contracts while still shipping actionable artifact metadata.

---

### 2026-03-29: Do not add a dedicated `readme_relpath` manifest field in v1
**Context**: README pointer could be modeled explicitly or inferred from packaged member contract.

**Options considered**:
1. Add explicit `readme_relpath` manifest field.
2. Reuse `artifact.packaged_member_relpaths` and `README.md` root-member contract.

**Decision**: Option 2.

**Impact**: Keeps manifest schema stable while still providing deterministic, machine-checkable README membership metadata.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| README drifts from manifest contract values | High | Medium | Build README from one normalized metadata object and add consistency assertions in tests | Mitigated |
| Non-deterministic README ordering causes noisy artifact diffs | Medium | Medium | Enforce stable section and row ordering with deterministic serialization helpers | Mitigated |
| Cache-hit and cache-miss artifacts diverge in README shape | Medium | Low | Reuse same bundle member contract and assert in cache-hit/cold-hit tests | Mitigated |
| Sensitive host/runtime details leak into README | High | Low | Explicitly filter absolute paths/secrets and test for forbidden patterns | Mitigated |

## Verification Checklist

### Backend Tests
- [x] `wctl run-pytest tests/nodb/mods/test_features_export_service.py -k "readme or manifest or cache_hit" --maxfail=1` (`2 passed, 57 deselected`)
- [x] `wctl run-pytest tests/nodb/mods/test_features_export_manifest.py tests/nodb/mods/test_features_export_exporters.py --maxfail=1` (`21 passed`)
- [x] `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` (`21 passed`)

### Documentation
- [x] `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md` (`0 errors, 0 warnings`)
- [x] `wctl doc-lint --path docs/work-packages/20260329_features_export_artifact_readme_metadata/package.md` (`0 errors, 0 warnings`)
- [x] `wctl doc-lint --path docs/work-packages/20260329_features_export_artifact_readme_metadata/tracker.md` (`0 errors, 0 warnings`)
- [x] `wctl doc-lint --path docs/work-packages/20260329_features_export_artifact_readme_metadata/prompts/active/features_export_artifact_readme_metadata_execplan.md` (`0 errors, 0 warnings`)

## Progress Notes

### 2026-03-29: Initial planning and scope freeze
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed current `features_export` contracts, packaging behavior, and manifest metadata availability.
- Researched geospatial metadata standards/guidance references and mapped them to existing export metadata inputs.
- Updated specification contract to require generated artifact `README.md` in zip bundles and documented metadata availability/gaps.
- Created work-package scaffold and active ExecPlan.

**Blockers encountered**:
- None.

**Next steps**:
- Implement README builder helper and service integration.
- Add deterministic packaging/consistency tests.

**Test results**:
- Pending implementation-phase validation.

### 2026-03-29: Implementation and validation complete
**Agent/Contributor**: Codex

**Work completed**:
- Added deterministic README renderer in `wepppy/nodb/mods/features_export/readme_builder.py` with stable section/table ordering and absolute path redaction for relpath fields.
- Updated `wepppy/nodb/mods/features_export/service.py` cache-miss publication to write `README.md`, include it in `bundle_member_sources`, and include it in planned packaged-member relpaths for manifest/cache alignment.
- Updated `wepppy/nodb/mods/features_export/__init__.py` exports to include `FEATURES_EXPORT_ARTIFACT_README_NAME` and `build_export_readme`.
- Extended `tests/nodb/mods/test_features_export_service.py` to assert zip member contract (`README.md`, `manifest.json`, payload member), README/manifest consistency, cache-hit packaged member propagation, and deterministic redaction behavior.

**Blockers encountered**:
- None.

**Next steps**:
- None for this package; handoff is ready.

**Test results**:
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py -k "readme or manifest or cache_hit" --maxfail=1` -> `2 passed, 57 deselected`.
- `wctl run-pytest tests/nodb/mods/test_features_export_manifest.py tests/nodb/mods/test_features_export_exporters.py --maxfail=1` -> `21 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` -> `21 passed`.
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1` -> `59 passed` (extra confidence run).
