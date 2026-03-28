# Features Export Service Compliance Refactor (Phases 1-4)

**Status**: Closed 2026-03-28

## Overview
This package executes the QA-driven follow-up refactor for `wepppy/nodb/mods/features_export/service.py` to move from "conditionally compliant" to fully compliant service quality posture. Work is constrained to the existing production path (no feature flag, no alternate path) and targets maintainability, policy consistency, and branch coverage closure.

## Objectives
- Reduce `service.py` orchestration complexity by extracting clear collaborator responsibilities.
- Remove policy duplication between legacy and carrier source materialization paths.
- Eliminate dead private wrappers and reduce maintenance drift surface.
- Close carrier strict-required branch-test gaps identified by QA.
- Preserve external contracts and existing run-path behavior.

## Scope

### Included
- `wepppy/nodb/mods/features_export/service.py` refactor.
- New collaborator modules under `wepppy/nodb/mods/features_export/` for legacy/carrier materialization decomposition.
- Test additions in `tests/nodb/mods/test_features_export_service.py` for missing strictness branches.
- Package docs + ExecPlan + tracker + review artifacts.

### Out of Scope
- New features, format additions, or API contract changes.
- Front-end feature work beyond regression verification.
- Planner redesign beyond targeted extraction needed for this package.

## Success Criteria
- [x] `_materialize_export_payloads` and legacy source build path are decomposed with clear boundaries.
- [x] Required-source policy duplication is removed or centralized.
- [x] Dead private wrappers identified by QA are removed.
- [x] Carrier strict-required branch tests added (`file_missing`, `unsupported_source_kind`, service propagation).
- [x] Required validation commands pass.
- [x] Package tracker/ExecPlan/review artifacts are complete with no unresolved medium/high findings.

## Validation Targets
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py -k "required_source or discover_layer_sources or materialization_error or ensure_join_key" --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1`
- `wctl run-npm test -- features_export`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- `wctl doc-lint --path docs/work-packages/20260328_features_export_service_compliance_refactor/package.md`
- `wctl doc-lint --path docs/work-packages/20260328_features_export_service_compliance_refactor/tracker.md`
- `wctl doc-lint --path docs/work-packages/20260328_features_export_service_compliance_refactor/prompts/completed/features_export_service_compliance_refactor_execplan.md`

## Deliverables
- Completed 4-phase refactor implementation.
- Validation evidence in tracker.
- Review artifacts:
  - `artifacts/20260328_code_review.md`
  - `artifacts/20260328_qa_review.md`

## Completion Summary (2026-03-28)
- Added collaborators:
  - `wepppy/nodb/mods/features_export/legacy_source_materializer.py`
  - `wepppy/nodb/mods/features_export/carrier_layer_materializer.py`
- Refactored `service.py`:
  - legacy source loop extracted to collaborator and now reuses strict required-source discovery policy;
  - carrier core build path delegated to collaborator for cleaner orchestration;
  - dead wrappers removed (`_column_metadata_by_id`, `_identity_column_token`);
  - dead parquet helpers removed from `service.py` after extraction.
- Extended tests with missing carrier strict-required branches and service-level materialization error translation.
- Validation gates passed (pytest, route tests, JS tests, broad-exception enforcement).
- Run-path smoke verified behavior parity:
  - cold job `manual-wp-service-compliance-cold-20260328045609019671` (`3.378s`, `cache_hit=false`)
  - warm job `manual-wp-service-compliance-warm-20260328045612397503` (`0.374s`, `cache_hit=true`)
  - artifact `export/features/artifacts/6f6fddc846554054a01eebcad52f0f51/features_export.gpkg`
  - layer counts:
    - `clogging_starch_sbs_map_subcatchments`: `66`
    - `clogging_starch_chan_map_channels`: `27`
