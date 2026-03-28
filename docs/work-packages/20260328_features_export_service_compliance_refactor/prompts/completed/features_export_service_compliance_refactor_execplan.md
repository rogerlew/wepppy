> Outcome (2026-03-28): Completed all four refactor phases; QA medium findings closed, validation gates passed, and run-path parity verified (66/27 layers).

# Features Export Service Compliance Refactor (4-Phase E2E)

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current while work proceeds.

## Purpose / Big Picture

Close the QA \"conditionally compliant\" gap for features-export service quality by finishing the remaining 4 phases end-to-end:
1. legacy source-materialization extraction,
2. orchestration slimming in `_materialize_export_payloads`,
3. dead-wrapper removal and helper-boundary cleanup,
4. strict-required carrier test-gap closure.

No external contract changes are allowed for `execute_features_export(...)`, rq-engine routes, or WEPPcloud controls.

## Progress

- [x] (2026-03-28) Package scaffold created (`package.md`, `tracker.md`, active ExecPlan).
- [x] (2026-03-28) Phase 1 complete: extracted legacy source-materialization flow to `legacy_source_materializer.py`.
- [x] (2026-03-28) Phase 2 complete: extracted carrier source materialization/projection to `carrier_layer_materializer.py` and slimmed `_materialize_export_payloads`.
- [x] (2026-03-28) Phase 3 complete: removed dead wrappers and unused helper code from `service.py`.
- [x] (2026-03-28) Phase 4 complete: added strict-required branch tests and passed full validation matrix.

## Surprises & Discoveries

- `discover_layer_sources` strict policy could be reused for legacy materialization once `skip_vector_relpath` support was added, removing duplicated required-source policy code from `service.py`.
- After collaborator extraction, legacy parquet/unit helper code in `service.py` became dead and was safely removed.
- Carrier-path service translation test required monkeypatching `materialize_carrier_layer_core` directly; this proved a stable boundary for contract validation.

## Decision Log

- Decision: Use one package for all four phases and execute in one contiguous pass.
  Rationale: avoids drift between phases and keeps validation evidence coherent.
  Date/Author: 2026-03-28 / Codex.

## Outcomes & Retrospective

- Package completed end-to-end with all four phases closed.
- Quality/compliance outcomes:
  - service orchestration is cleaner and less duplicated;
  - strict required-source policy is centralized via discovery helper reuse;
  - dead wrappers and dead parquet helpers were removed;
  - missing strict-required carrier branch tests were added.
- Validation outcomes:
  - targeted service strictness tests passed;
  - full features-export backend/route/frontend test matrix passed;
  - changed-file broad exception enforcement passed.
- Run-path smoke outcomes:
  - cold: `manual-wp-service-compliance-cold-20260328045609019671` (`3.378s`)
  - warm: `manual-wp-service-compliance-warm-20260328045612397503` (`0.374s`)
  - artifact layers: 2
  - counts: `66` subcatchments, `27` channels.

## Implementation Plan

### Phase 1 - Legacy Source-Materialization Extraction

- Add `wepppy/nodb/mods/features_export/legacy_source_materializer.py`.
- Move legacy source-merge loop from `_build_layer_frame_from_sources` into collaborator.
- Reuse `discover_layer_sources` strict required-source policy to avoid branch duplication.
- Propagate join-unresolved required failures via `MaterializationContractError` and translate to service `materialization_error`.

### Phase 2 - Orchestration Slimming

- Add collaborator for carrier layer core build path and selected-column projection boundary.
- Simplify `_materialize_export_payloads` so it mostly orchestrates lookups + branch dispatch + final payload assembly.
- Keep all response/manifest payload contracts unchanged.

### Phase 3 - Dead Wrapper Cleanup

- Remove dead wrappers in `service.py` identified by QA:
  - `_column_metadata_by_id`
  - `_identity_column_token`
- Ensure all remaining helper imports and wrappers are actually used.

### Phase 4 - Coverage and Gate Closure

- Add missing tests:
  - `discover_layer_sources` required `file_missing`.
  - `discover_layer_sources` required `unsupported_source_kind`.
  - service-level propagation where carrier-path `MaterializationContractError` is translated to `FeaturesExportServiceError(code=\"materialization_error\")`.
- Run full validation suite and doc-lint.

## Validation Commands

```bash
cd /workdir/wepppy
wctl run-pytest tests/nodb/mods/test_features_export_service.py -k "required_source or discover_layer_sources or materialization_error or ensure_join_key" --maxfail=1
wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1
wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1
wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1
wctl run-npm test -- features_export
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
wctl doc-lint --path docs/work-packages/20260328_features_export_service_compliance_refactor/package.md
wctl doc-lint --path docs/work-packages/20260328_features_export_service_compliance_refactor/tracker.md
wctl doc-lint --path docs/work-packages/20260328_features_export_service_compliance_refactor/prompts/active/features_export_service_compliance_refactor_execplan.md
```
