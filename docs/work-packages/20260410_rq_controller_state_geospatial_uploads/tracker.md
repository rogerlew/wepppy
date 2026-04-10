# Tracker - RQ Controller State Geospatial and Upload Metadata

> Living document tracking progress, decisions, risks, and closeout evidence for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-10 20:17 UTC  
**Current phase**: Complete  
**Last updated**: 2026-04-10 21:06 UTC  
**Next milestone**: Handoff to roadmap package `20260410_rq_controller_state_errors_progress_outputs`.  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260410_rq_controller_state_geospatial_uploads/artifacts/2026-04-10_security_review.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Completed required-reading pass (contract docs, package sources, frozen artifacts, and route inventory).
- [x] Implemented `GET /api/runs/{runid}/{config}/geospatial-metadata` with canonical auth and error boundaries.
- [x] Added run-resolved geospatial metadata payload assembly for coverage/defaults/constraints/availability fields.
- [x] Hardened upload metadata descriptor/schema/default surfaces for:
  - `rq_engine_upload_dem`
  - `rq_engine_upload_cli`
  - `rq_engine_upload_sbs`
  - `rq_engine_upload_cover_transform`
- [x] Added explicit upload-size limits (`max_bytes`) in live upload handlers and aligned descriptor metadata to those limits.
- [x] Added/extended regression tests:
  - `tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py`
  - `tests/microservices/test_rq_engine_upload_climate_routes.py`
  - `tests/microservices/test_rq_engine_upload_disturbed_routes.py`
  - `tests/microservices/test_rq_engine_watershed_routes.py`
  - `tests/microservices/test_rq_engine_openapi_contract.py`
- [x] Updated route contract guards and frozen artifacts:
  - `tools/rq_engine_contract_rules.py`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- [x] Completed `reviewer`, `qa_reviewer`, and `security_reviewer` passes and re-reviews; all medium/high findings resolved.
- [x] Completed security artifact and lifecycle docs.
- [x] Archived ExecPlan to `prompts/completed/` with outcome note.
- [x] Updated `PROJECT_TRACKER.md` lifecycle entry to completed state.

## Timeline

- **2026-04-10 20:17 UTC** - Package scaffold and active ExecPlan authored.
- **2026-04-10 20:44 UTC** - Geospatial route + upload descriptor metadata + initial tests/artifact updates completed.
- **2026-04-10 20:54 UTC** - Required code-gate command suite passed first full run.
- **2026-04-10 21:00 UTC** - Reviewer/QA/security findings triaged; medium findings identified (parity drift, broad-exception annotation, upload-size enforcement).
- **2026-04-10 21:05 UTC** - Remediation edits applied (shared parity helpers, max-bytes enforcement, oversize tests, boundary tests, filename sanitization).
- **2026-04-10 21:06 UTC** - Required code gates re-run and passed; reviewer/QA/security re-reviews returned no unresolved medium/high findings; docs closeout completed.

## Decisions Log

### 2026-04-10 20:17 UTC: Keep package scope aligned to roadmap row 5 geospatial/upload metadata
**Context**: Schema/default package is already complete and later roadmap rows own outputs/progress/errors and auth-concurrency hardening.

**Options considered**:
1. Fold outputs/progress/error catalog work into this package.
2. Keep strict row-5 scope and hand off subsequent surfaces to planned packages.

**Decision**: Option 2.

**Impact**: Maintains dependency order and keeps validation/review surfaces focused.

### 2026-04-10 20:57 UTC: Resolve parity drift with shared metadata helpers instead of endpoint-local patches
**Context**: Reviewer findings identified inconsistent climate/soils mode constraints and watershed defaults between `/geospatial-metadata` and controller metadata surfaces.

**Options considered**:
1. Patch each endpoint independently.
2. Introduce shared helper functions for climate mode availability, soils mode catalog, and watershed defaults.

**Decision**: Option 2.

**Impact**: Single source of truth for parity-sensitive values and simpler regression coverage.

### 2026-04-10 21:01 UTC: Enforce upload size limits in handlers and descriptors within this package
**Context**: Security review flagged unbounded upload size as medium risk for authenticated storage/processing DoS.

**Options considered**:
1. Leave runtime unbounded and document ingress-layer limits only.
2. Add per-route `max_bytes` enforcement and align descriptor metadata/tests.

**Decision**: Option 2.

**Impact**: Eliminates unresolved medium security finding and keeps machine-readable contract aligned with live behavior.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Geospatial defaults diverge from run-specific coverage/controller state | High | Medium | Introduced shared parity helpers + cross-surface regression tests | Mitigated |
| Upload metadata incomplete or inconsistent with runtime validation | High | Medium | Added explicit upload `max_bytes` enforcement + descriptor parity assertions and oversize tests | Mitigated |
| Sensitive run internals leak through metadata payloads | High | Medium | Sanitized uploaded DEM filename before payload exposure; security review completed | Mitigated |
| Frozen inventory/checklist artifacts lag endpoint implementation | Medium | Medium | Updated artifacts and re-ran guard scripts/tests | Mitigated |

## Verification Checklist

### Code Gate
- [x] `wctl run-pytest tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py --maxfail=1`
- [x] `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- [x] `python tools/check_endpoint_inventory.py`
- [x] `python tools/check_route_contract_checklist.py`
- [x] `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1`

### QA Gate
- [x] Independent `reviewer` pass completed.
- [x] Independent `qa_reviewer` pass completed.
- [x] Findings dispositioned in this tracker.
- [x] No unresolved medium/high QA findings.

### Security Gate
- [x] Security artifact created/updated: `artifacts/2026-04-10_security_review.md`.
- [x] Independent `security_reviewer` pass completed.
- [x] Auth/scope/session, upload metadata disclosure, and validation-contract implications reviewed.
- [x] No unresolved medium/high security findings.

### Docs Gate
- [x] `wctl doc-lint` run on changed docs (`package.md`, `tracker.md`, completed ExecPlan/outcome, security artifact, schema docs, freeze/checklist docs, and `PROJECT_TRACKER.md`).

## Reviewer Findings Disposition

### Independent Reviewer (`reviewer`) - 2026-04-10
1. **Medium**: Climate mode parity mismatch between geospatial metadata and climate schema.  
   **Disposition**: Resolved with shared `_available_climate_modes(...)` helper and parity test.
2. **Medium**: Soils mode parity mismatch between geospatial metadata and soils schema.  
   **Disposition**: Resolved with shared `_supported_soils_modes(...)` helper and parity test.
3. **Medium**: Watershed defaults drift between geospatial metadata and controller defaults.  
   **Disposition**: Resolved with shared `_resolved_watershed_defaults(...)` helper and cross-surface test.

### QA Reviewer (`qa_reviewer`) - 2026-04-10
1. **Medium**: Geospatial auth broad exception catch lacked boundary annotation and failed changed-file broad-exception enforcement.  
   **Disposition**: Resolved by adding boundary annotation and validating `tools/check_broad_exceptions.py --enforce-changed` pass.
2. **Low**: Missing negative-path tests for unexpected geospatial auth/state helper failures.  
   **Disposition**: Resolved by adding explicit 401/500 boundary tests.
3. **Low**: Literal-based parity assertions for upload CLI/cover descriptor fields.  
   **Disposition**: Resolved by asserting against shared route constants.

### Security Reviewer (`security_reviewer`) - 2026-04-10
1. **Medium**: Unbounded upload sizes in runtime handlers (`upload_dem`, `upload_cli`, `upload_sbs`, `upload_cover_transform`).  
   **Disposition**: Resolved with per-route `max_bytes` enforcement, aligned descriptor metadata, and oversize regression tests.
2. **Low**: Potential path-like uploaded DEM filename disclosure in geospatial metadata.  
   **Disposition**: Resolved by sanitizing to `Path(...).name` + `secure_filename(...)` before payload emission.
3. **Low (re-review)**: No direct test for filename sanitization branch in `_load_runtime_state`.  
   **Disposition**: Accepted residual low risk (behavior covered in implementation review; no medium/high impact).

## Verification Evidence (Command Outcomes)

- `wctl run-pytest tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py --maxfail=1` -> `21 passed`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `9 passed`
- `python tools/check_endpoint_inventory.py` -> `Endpoint inventory check passed`
- `python tools/check_route_contract_checklist.py` -> `Route contract checklist check passed`
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` -> `2 passed`
- `wctl run-pytest tests/microservices/test_rq_engine_upload_climate_routes.py tests/microservices/test_rq_engine_upload_disturbed_routes.py tests/microservices/test_rq_engine_watershed_routes.py --maxfail=1` -> `37 passed`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> `PASS`
- `wctl doc-lint --path docs/schemas/rq-controller-state-contract.md --path docs/work-packages/20260410_rq_controller_state_geospatial_uploads/package.md --path docs/work-packages/20260410_rq_controller_state_geospatial_uploads/tracker.md --path docs/work-packages/20260410_rq_controller_state_geospatial_uploads/prompts/completed/rq_controller_state_geospatial_uploads_execplan.md --path docs/work-packages/20260410_rq_controller_state_geospatial_uploads/prompts/completed/rq_controller_state_geospatial_uploads_execplan_outcome.md --path docs/work-packages/20260410_rq_controller_state_geospatial_uploads/artifacts/2026-04-10_security_review.md --path PROJECT_TRACKER.md` -> `9 files validated, 0 errors, 0 warnings`

## Final Handoff Summary

- Geospatial metadata and upload metadata hardening for roadmap row 5 are implemented with route/schema/default/descriptor parity.
- Upload size limits are now enforced in runtime handlers and reflected in machine-readable contract metadata.
- Frozen inventory/checklist artifacts and guard checks are updated and passing.
- Required reviewer/QA/security gates completed with no unresolved medium/high findings.
