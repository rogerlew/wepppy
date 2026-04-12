# Tracker - Upload Boundary Helpers Unification

> Living document tracking progress, decisions, risks, and verification evidence for this package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-12 16:11 UTC  
**Current phase**: Complete  
**Last updated**: 2026-04-12 16:39 UTC  
**Next milestone**: None (package closed)  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260412_upload_boundary_helpers_unification/artifacts/2026-04-12_security_review.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, active ExecPlan path, artifacts directory) (2026-04-12 16:11 UTC).
- [x] Confirmed canonical ZIP helper requirement: keep `wepppy/microservices/shape_converter/archive_validation.py` as authoritative ZIP boundary layer (2026-04-12 16:11 UTC).
- [x] Completed initial route inventory of upload-capable endpoints and duplicated helper implementations (`ash`, `omni`, `roads`) (2026-04-12 16:11 UTC).
- [x] Implemented canonical non-ZIP upload boundary core in `wepppy/microservices/upload_boundary.py` (2026-04-12 16:22 UTC).
- [x] Migrated duplicated helper paths in `ash_routes.py`, `omni_routes.py`, `upload_helpers.py`, and `roads_bp.py` to canonical helpers (2026-04-12 16:27 UTC).
- [x] Added helper and route parity regressions (`test_upload_boundary_helpers`, `ash`, `omni`) (2026-04-12 16:29 UTC).
- [x] Ran targeted and full pytest gates successfully (2026-04-12 16:35 UTC).
- [x] Closed security review artifact with no unresolved medium/high findings (2026-04-12 16:35 UTC).
- [x] Passed docs lint gate for package/tracker/ExecPlan/security artifact/contract tracker docs (2026-04-12 16:39 UTC).

## Timeline

- **2026-04-12 16:11 UTC** - Package created and scoped from endpoint/helper inventory and consistency goal.
- **2026-04-12 16:22 UTC** - Added shared non-ZIP helper module for filename/extension/size/save boundary policy.
- **2026-04-12 16:27 UTC** - Completed route migrations for `ash`, `omni`, and Roads with compatibility preserved.
- **2026-04-12 16:35 UTC** - Validation and security gates passed; package marked complete.
- **2026-04-12 16:39 UTC** - Docs lint gate passed and package documentation closure finalized.

## Decisions Log

### 2026-04-12 16:11 UTC: Keep ZIP boundaries anchored to `shape_converter` helpers
**Context**: The package targets helper unification across upload routes and includes both ZIP and non-ZIP surfaces.

**Options considered**:
1. Build new ZIP helper abstractions in rq-engine.
2. Keep ZIP helper authority in `wepppy/microservices/shape_converter/archive_validation.py` and unify only non-ZIP boundary helpers.

**Decision**: Option 2.

**Impact**: Preserves validated archive controls and avoids parallel ZIP validator drift.

---

### 2026-04-12 16:18 UTC: Introduce a shared cross-framework non-ZIP helper core
**Context**: Existing shared helper coverage was rq-engine centric (`upload_helpers.py`), while `ash`, `omni`, and Flask Roads duplicated boundary checks.

**Options considered**:
1. Keep per-route helper stacks and tune each route.
2. Add a small shared helper module consumed by both FastAPI and Flask surfaces and keep route adapters thin.

**Decision**: Option 2.

**Impact**: Eliminates duplicated checks and keeps endpoint-specific caps/messages/status mapping explicit at route boundaries.

---

### 2026-04-12 16:27 UTC: Preserve per-endpoint response contracts while migrating internals
**Context**: Helper migration could collapse status differences or change message text relied on by tests/clients.

**Options considered**:
1. Normalize all upload failures to `400`.
2. Preserve existing route behavior and continue mapping explicit size failures to `413`.

**Decision**: Option 2.

**Impact**: No contract drift for existing upload-facing clients while still consolidating internal boundary logic.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Helper abstraction changes endpoint behavior (status/messages) | High | Medium | Locked behavior with new route regression tests for 400/413 and message parity | Closed |
| Cross-framework helper API is awkward for FastAPI vs Flask call sites | Medium | Medium | Implemented shared stream core plus thin route adapters (`save_upload_file`, Roads stream helper) | Closed |
| Hidden upload endpoints remain on divergent helper paths | Medium | Low | Re-ran endpoint/helper inventory; package scope limited to `ash`, `omni`, and Roads per ExecPlan | Closed |
| ZIP helper drift introduced unintentionally during unification | High | Low | No ZIP helper changes; canonical ZIP authority unchanged in `archive_validation.py` | Closed |

## Verification Checklist

### Code/Contract
- [x] Canonical helper API defined and documented.
- [x] Duplicated helper implementations removed from targeted routes.
- [x] Route-level caps and allowlists remain unchanged unless explicitly documented.
- [x] ZIP handling remains canonical via `archive_validation.py`.

### Security
- [x] Security impact triage documented (`high`).
- [x] Dedicated security artifact created.
- [x] No unresolved medium/high findings remain at closure.

### Tests
- [x] Helper-level unit tests added for boundary behavior.
- [x] Targeted route suites for migrated routes pass.
- [x] Full suite gate passes (`wctl run-pytest tests --maxfail=1`).

### Docs
- [x] Package/tracker/ExecPlan scaffolded.
- [x] Upload contract and affected route helper ownership docs updated.
- [x] `wctl doc-lint` passes on changed docs.

## Progress Notes

### 2026-04-12 16:11 UTC: Package kickoff and inventory capture
**Agent/Contributor**: Codex

**Work completed**:
- Created work-package scaffold for upload boundary helper unification.
- Captured explicit hard requirement to keep ZIP helpers canonical in `shape_converter/archive_validation.py`.
- Documented current endpoint/helper split: shared `upload_helpers.py` coverage vs duplicated helper paths in `ash_routes.py`, `omni_routes.py`, and `roads_bp.py`.

**Blockers encountered**:
- None.

**Next steps**:
- Finalize active ExecPlan with concrete helper API and migration milestones.
- Start implementation with helper core + adapter scaffolding.

**Test results**:
- Not run (documentation/scoping session).

---

### 2026-04-12 16:35 UTC: Implementation and gate completion
**Agent/Contributor**: Codex

**Work completed**:
- Added `wepppy/microservices/upload_boundary.py` as canonical non-ZIP helper layer.
- Migrated `wepppy/microservices/rq_engine/upload_helpers.py`, `ash_routes.py`, `omni_routes.py`, and `wepppy/weppcloud/routes/nodb_api/roads_bp.py` to shared helper usage.
- Added regression tests for helper behavior and route-level 400/413 parity.

**Blockers encountered**:
- None.

**Next steps**:
- Package closure and handoff.

**Test results**:
- Targeted suites: `137 passed`.
- Full suite: `3511 passed`, `36 skipped`.
- Docs lint: `6 files validated, 0 errors, 0 warnings`.

## Watch List

- Preserve shape-converter ZIP helper authority for future upload packages.
- Keep `wepppy/weppcloud/routes/usersum/generated/docs_index.json` untouched when dirty.

## Communication Log

### 2026-04-12 16:11 UTC: User directive
**Participants**: User, Codex  
**Question/Topic**: Create a work-package to unify upload boundary helpers across more routes and keep ZIP helpers canonical from `shape_converter.archive_validation`.  
**Outcome**: New package created with high-security triage, scoped migration targets, and active ExecPlan.

### 2026-04-12 16:35 UTC: Package completion
**Participants**: User, Codex  
**Question/Topic**: Complete package end-to-end including tests, docs, and security closeout.  
**Outcome**: Code changes merged in workspace, test gates passed, and security artifact closed with pass verdict.
