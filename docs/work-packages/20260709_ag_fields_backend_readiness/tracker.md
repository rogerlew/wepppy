# Tracker - AgFields Backend Readiness

> Living document tracking progress, decisions, risks, validation, and handoffs for AgFields backend readiness (routes, RQ tasks, controller contract gaps, `wepp_bin` bug fix).

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-09 21:53 UTC
**Closed**: 2026-07-09 22:55 UTC
**Current phase**: Complete
**Last updated**: 2026-07-09 22:55 UTC
**Next milestone**: Successor AgFields runs-page UI package
**Security impact**: `high` — the package adds authenticated upload routes and queue wiring, both high-impact surfaces under `docs/work-packages/README.md`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/2026-07-09_security_review.md`

## Task Board

### Ready / Backlog
None.

### In Progress
None.

### Blocked
None.

### Done
- [x] Package scaffold created with package brief, tracker, active ExecPlan, spec-verification artifact, and root tracker registration (2026-07-09 21:47 UTC).
- [x] Milestone 1: repaired explicit `wepp_bin` propagation and added executor plus generated-run regression coverage (2026-07-09 21:57 UTC).
- [x] Milestone 2: implemented controller staleness, plant-file, mapping, validation, and readiness contracts with targeted regression coverage (2026-07-09 22:07 UTC).
- [x] Milestone 3: added guarded RQ jobs, terminal payloads, triggers, and chain-order/failure tests (2026-07-09 22:19 UTC).
- [x] Milestone 4: added and registered all run-scoped rq-engine routes with 22 contract/auth/upload tests (2026-07-09 22:19 UTC).
- [x] Milestone 5: completed targeted integration, queue graph, stub, broad-exception, OpenAPI, docs, and live Redis job-tree validation (2026-07-09 22:52 UTC).
- [x] Milestone 6: completed documentation, security review, lifecycle closure, and ExecPlan archival (2026-07-09 22:55 UTC).

## Timeline

- **2026-07-09 21:47 UTC** - Package scaffolded from the UI spec's backend prerequisites (`ui_control_layout.md` §10) after Codex spec-verification review; findings dispositioned into the spec and captured as an artifact.
- **2026-07-09 21:57 UTC** - Milestone 1 completed; targeted regression suite passed (`2 passed`).
- **2026-07-09 22:07 UTC** - Milestone 2 completed; `tests/nodb/mods/` passed (`748 passed, 23 skipped`).
- **2026-07-09 22:19 UTC** - Milestones 3 and 4 completed; RQ tests passed (`4 passed`), route tests passed (`22 passed`), and queue dependency artifacts were regenerated and verified.
- **2026-07-09 22:47 UTC** - Full-suite integration found one related OpenAPI budget failure (`129,217 > 118,500`); budget raised narrowly to 130,000 and documented in the canonical agent API contract and ADR-0015.
- **2026-07-09 22:52 UTC** - Final targeted AgFields set passed (`52 passed`); OpenAPI, queue graph, stubs, broad-exception, docs, and live job-tree gates passed.
- **2026-07-09 22:55 UTC** - Full-suite retry stopped on an unrelated batch-runner baseline failure after 2,070 passing tests; the failure reproduced alone and no implicated file is changed by this package. Package closed with the limitation recorded.

## Decisions Log

### 2026-07-09: Preserve persisted and generated data contracts additively
**Context**: The package adds NoDb state, HTTP payloads, and a canonical writer for the existing `rotation_lookup.tsv` artifact.

**Decision**: Keep the TSV columns `crop_name`, `database`, and `rotation_id` unchanged; add new NoDb keys without renaming or removing existing keys; treat missing new keys in historical runs as clean defaults; expose new route fields additively. Regression coverage must prove TSV round-trip through `CropRotationManager`, NoDb defaults for prepackage state, and generated `wepp/ag_fields/runs/*` propagation through the repaired sub-field runner.

### 2026-07-09: Reclassify security impact as high
**Context**: The package scaffold marked the work `low`, but `docs/work-packages/README.md` classifies uploads and queue wiring as `high` by default.

**Decision**: Require a dedicated security artifact and close all medium/high findings before package closure.

### 2026-07-09: Split backend readiness from UI implementation
**Context**: The UI spec depends on backend surface that does not exist (routes, RQ tasks) and on contract fixes (staleness, plant-file semantics, `wepp_bin` bug). Bundling backend and UI in one package would couple a large template/controller effort to backend churn.

**Decision**: This package delivers only spec §9/§10 backend work; the UI template/controller ships in a successor package against a stable surface.

### 2026-07-09: Treat the UI spec as the requirements document
**Context**: Requirements could be duplicated into this package and drift.

**Decision**: `wepppy/nodb/mods/ag_fields/ui_control_layout.md` §9 and §10 are authoritative; this package's docs reference rather than restate them. Spec changes during implementation must be made in the spec file first.

## Validation

Planned gates (record command outputs here as work proceeds):

- `wctl run-pytest tests/nodb/mods/` (AgFields controller tests, including new regression coverage)
- Targeted route/RQ tests added under `tests/`
- `python tools/check_broad_exceptions.py --enforce-changed`

Recorded evidence:

- `wctl run-pytest tests/nodb/mods/test_ag_fields_wepp_runner.py` -> `2 passed, 2 warnings in 8.44s`.
- `wctl run-pytest tests/nodb/mods/` -> `748 passed, 23 skipped, 17 warnings in 27.57s`.
- `wctl run-pytest tests/rq/test_ag_fields_rq.py` -> `4 passed, 4 warnings in 8.11s`.
- `wctl run-pytest tests/microservices/test_rq_engine_ag_fields_routes.py` -> `22 passed, 5 warnings in 12.70s`.
- `wctl check-rq-graph` -> `RQ dependency graph artifacts are up to date`.
- Final focused AgFields controller/RQ/route set -> `52 passed, 9 warnings in 15.86s`.
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py` -> `10 passed, 5 warnings in 12.78s`.
- `wctl run-stubtest wepppy.rq.ag_fields_rq` -> success.
- `wctl check-test-stubs` -> all stubs complete.
- `python tools/check_broad_exceptions.py --enforce-changed` with new production files included through intent-to-add -> pass; current new-file findings `0`, net changed-file delta `-4`.
- Live Redis job-tree check -> all three new task entrypoints resolved as one queued root; temporary jobs were deleted.
- `wctl run-pytest tests --maxfail=1` -> stopped at `tests/nodb/test_batch_runner.py::test_run_batch_project_does_not_delete_workspace_when_rmtree_disabled` after `2070 passed, 41 skipped, 35 warnings in 300.01s`; the failure reproduced alone and is outside this package's changed files.

Compatibility and downstream regression plan:

- Persisted NoDb additions are optional on read and default safely for historical runs.
- `rotation_lookup.tsv` keeps its existing three-column schema and remains readable by `CropRotationManager`.
- Route responses add fields only; they do not rename or remove established run/job response keys.
- Tests will exercise structured mapping save/read, staleness across re-upload/rebuild, and a generated sub-field run file reaching `run_hillslope` with the configured WEPP binary.

## Handoffs

- Successor package: AgFields runs-page UI implementation (template, controller JS, runs-page wiring, modal) — unblocked by this package.
- Feature registry maturity bump happens in the successor package when the control ships.
- No seeded `/wc1/runs/*/ag_fields.nodb` project was available for a real WEPP binary end-to-end run; generated-artifact coverage verifies the repaired runner boundary.
- Package blockers: none.
