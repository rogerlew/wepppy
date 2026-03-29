# Tracker - Features Export Artifact README Metadata Packaging

> Living document tracking progress, decisions, risks, and validation for dynamic features-export artifact README generation.

## Quick Status

**Started**: 2026-03-29  
**Current phase**: Planning  
**Last updated**: 2026-03-29  
**Active ExecPlan**: `prompts/active/features_export_artifact_readme_metadata_execplan.md`  
**Next milestone**: Implement README builder + service packaging integration (Milestone 1)

## Task Board

### Ready / Backlog
- [ ] Implement `README.md` builder helper using manifest/request/layer/dependency metadata inputs.
- [ ] Integrate README generation into cache-miss artifact publication path in `service.py`.
- [ ] Add/adjust manifest pointer fields if required (`readme_relpath` or equivalent).
- [ ] Add regression tests for zip membership and README/manifest consistency.
- [ ] Run targeted validation suites and document results.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffold authored (`package.md`, `tracker.md`, active ExecPlan) (2026-03-29).
- [x] Updated `features_export` specification with standards baseline, metadata-gap assessment, and dynamic README artifact contract (2026-03-29).

## Timeline

- **2026-03-29** - Package created and scoped for artifact README generation/plumbing.
- **2026-03-29** - Specification updated to include geospatial metadata standards baseline and README contract.

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| README drifts from manifest contract values | High | Medium | Build README from one normalized metadata object and add consistency assertions in tests | Open |
| Non-deterministic README ordering causes noisy artifact diffs | Medium | Medium | Enforce stable section and row ordering with deterministic serialization helpers | Open |
| Cache-hit and cache-miss artifacts diverge in README shape | Medium | Low | Reuse same bundle member contract and assert in cache-hit/cold-hit tests | Open |
| Sensitive host/runtime details leak into README | High | Low | Explicitly filter absolute paths/secrets and test for forbidden patterns | Open |

## Verification Checklist

### Backend Tests
- [ ] `wctl run-pytest tests/nodb/mods/test_features_export_service.py -k "readme or manifest or cache_hit" --maxfail=1`
- [ ] `wctl run-pytest tests/nodb/mods/test_features_export_manifest.py tests/nodb/mods/test_features_export_exporters.py --maxfail=1`
- [ ] `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`

### Documentation
- [ ] `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md`
- [ ] `wctl doc-lint --path docs/work-packages/20260329_features_export_artifact_readme_metadata/package.md`
- [ ] `wctl doc-lint --path docs/work-packages/20260329_features_export_artifact_readme_metadata/tracker.md`
- [ ] `wctl doc-lint --path docs/work-packages/20260329_features_export_artifact_readme_metadata/prompts/active/features_export_artifact_readme_metadata_execplan.md`

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
