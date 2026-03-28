# Features Export Service Quality Refactor (Phased E2E)

**Status**: Closed 2026-03-28

## Overview
`wepppy/nodb/mods/features_export/service.py` currently carries too much responsibility for one module and still contains quality-contract risks identified during QA review (broad exception boundary and hidden fallback behavior). This package executes a phased, end-to-end refactor that preserves WP-8 key-first behavior while bringing the service path into compliance with repository quality standards.

## Objectives
- Eliminate standards violations in `features_export` service paths (no broad exception swallow, no hidden fallback contracts).
- Preserve current functional behavior for default baseline exports and route contracts.
- Reduce complexity by extracting focused collaborators from `service.py` without changing public service API contracts.
- Clarify and document required-source/join-key behavior in specification and tests.
- Produce complete validation and run-path evidence, including baseline layer counts and runtime checks.

## Scope
This package is refactor and contract-hardening work for the features export service stack.

### Included
- `wepppy/nodb/mods/features_export/service.py` quality and contract hardening.
- New/updated collaborator modules under `wepppy/nodb/mods/features_export/` for decomposed responsibilities.
- Regression and contract tests in `tests/nodb/mods/` and `tests/microservices/`.
- Docs updates to features export specification and package execution artifacts.
- Run-path evidence collection for default baseline export behavior.

### Explicitly Out of Scope
- New export formats or new product-facing features.
- UI redesign beyond contract-preserving adjustments required by backend contract changes.
- Broad architecture changes outside features export module boundaries.

## Stakeholders
- **Primary**: NoDb/features export maintainers.
- **Reviewers**: RQ-engine maintainers, WEPPcloud route maintainers, QA maintainers.
- **Informed**: Operations maintainers monitoring export runtime and cache behavior.

## Success Criteria
- [x] No broad exception swallow or hidden fallback contract paths remain in touched `features_export` service code.
- [x] Join-key and required-source behavior is explicit, tested, and reflected in docs.
- [x] `service.py` responsibilities are decomposed into collaborators with stable service API behavior.
- [x] Required validation suites pass.
- [x] Run-path acceptance confirms default baseline export still materializes 2 layers with counts `66` and `27` for `clogging-starch/disturbed9002-wbt-mofe`.
- [x] Cold-cache and warm-cache runtimes are captured and compared against WP-8 baseline.
- [x] Code review and QA review artifacts are completed with no unresolved medium/high findings.

## Dependencies

### Prerequisites
- `docs/mini-work-packages/20260327_features_export_key_first_materialization_execplan.md` (WP-8 implementation + evidence).
- `docs/mini-work-packages/20260327_features_export_reconciliation_execplan.md` (contract reconciliation history).
- Current `features_export` specification and tests.

### Blocks
- Follow-on features export enhancements that depend on a stable, maintainable service layer.

## Related Packages
- **Depends on**: `docs/mini-work-packages/20260327_features_export_key_first_materialization_execplan.md`
- **Related**: `docs/mini-work-packages/20260327_features_export_reconciliation_execplan.md`
- **Follow-up**: Potential package for planner-side complexity reduction if needed after service extraction.

## Timeline Estimate
- **Expected duration**: 4-8 focused sessions.
- **Complexity**: High.
- **Risk level**: Medium-High.

## References
- `wepppy/nodb/mods/features_export/service.py` - primary refactor target.
- `wepppy/nodb/mods/features_export/specification.md` - behavior contract and documentation source.
- `tests/nodb/mods/test_features_export_service.py` - service regression and contract tests.
- `tests/microservices/test_rq_engine_features_export_routes.py` - rq-engine contract tests.
- `docs/standards/nodb-facade-collaborator-pattern.md` - collaborator extraction standard.
- `AGENTS.md` and `wepppy/nodb/AGENTS.md` - quality and exception handling guardrails.

## Deliverables
- Package scaffold (`package.md`, `tracker.md`, active ExecPlan).
- Implemented phase 1-4 code changes across features export service and collaborators.
- Updated tests for contract and regression coverage.
- Updated `wepppy/nodb/mods/features_export/specification.md` when contract clarifications are finalized.
- Review artifacts:
  - `artifacts/20260327_code_review.md`
  - `artifacts/20260327_qa_review.md`
- Final evidence notes for baseline counts and cold/warm runtime comparison.

## Completion Summary (2026-03-28)
- Delivered Phase 1-4 end-to-end with strict required-source enforcement and explicit join-key failure semantics on service and carrier paths.
- Reduced `service.py` responsibility surface via collaborator extraction:
  - `wepppy/nodb/mods/features_export/column_selection.py`
  - `wepppy/nodb/mods/features_export/cache_rehydration.py`
- Validation gates passed across NoDb planner/service/exporters, rq-engine features-export routes, WEPPcloud route controls, JS controller tests, broad-exception enforcement, and doc lint.
- Run-path acceptance evidence confirmed:
  - cold: `manual-wp8-cold-20260328043304050246` (`2.541s`, `cache_hit=false`)
  - warm: `manual-wp8-warm-20260328043306591594` (`0.996s`, `cache_hit=true`)
  - artifact: `export/features/artifacts/cbaa1b76752641b980ee1a3f119e3456/features_export.gpkg`
  - manifests:
    - `export/features/jobs/manual-wp8-cold-20260328043304050246/manifest.json`
    - `export/features/jobs/manual-wp8-warm-20260328043306591594/manifest.json`
  - feature counts:
    - `clogging_starch_sbs_map_subcatchments`: `66`
    - `clogging_starch_chan_map_channels`: `27`

## Follow-up Work
- Optional planner/exporter decomposition package if post-refactor observability still shows red-band hotspots.
- Optional broader features_export module complexity pass (service + planner + controller JS) after this package stabilizes.
