# Geneva HRU Peak Runoff and Event Erosion Enablement

**Status**: Closed (2026-04-30)  
**Timezone**: UTC

## Overview

This package adds the missing HRU-local peak runoff substrate needed for Geneva event-erosion estimates and exposes that substrate as an HRU Choropleth Map measure in the Geneva Interactive Summary. Geneva already computes per-HRU cumulative excess and materializes `runoff_depth` and `runoff_volume`; this package makes each HRU's event peak runoff explicit, auditable, and queryable without area-splitting watershed peak discharge.

The work preserves Geneva's Wildcat-lineage value proposition: predictable, conceptually traceable event outputs derived from selected rainfall, CN excess, HRU area, and a selected unit-hydrograph assumption. It does not implement full MUSLE erosion rows; it prepares the scientifically necessary peak-flow input and user-facing map layer that follow-on event-erosion work will consume.

## Objectives

- Add Rust Geneva kernel output for HRU-local hydrograph peak estimates from each HRU's own incremental excess series and area.
- Persist the new HRU peak runoff measure in Geneva's existing HRU event-measure artifact path.
- Add `hru_peak_runoff` as an HRU Choropleth Map measure on the Geneva Interactive Summary.
- Preserve the watershed `peak_discharge` summary contract and continue to reject watershed peak discharge as an HRU map measure.
- Add regression coverage proving HRU peak runoff is not computed by area-splitting the watershed peak.

## Scope

### Included

- Rust changes in `/workdir/wepppyo3/geneva_core` to compute per-HRU local hydrograph summary metrics during `geneva_run_batch`.
- PyO3/API serialization changes in `/workdir/wepppyo3/cli_revision/src/geneva` so WEPPpy receives HRU peak rows.
- WEPPpy Geneva collaborator changes under `wepppy/nodb/mods/geneva/` to materialize and query the new HRU measure.
- Query/report/UI changes needed to show `hru_peak_runoff` in the Geneva Interactive Summary HRU Choropleth Map measure selector.
- Tests for Rust, Python contract/materialization, Flask/query route behavior, and JavaScript/UI behavior.
- Documentation updates to `wepppy/nodb/mods/geneva/specification.md` and package artifacts.

### Explicitly Out of Scope

- Full `musle_hru_event_v1` erosion mass or yield computation.
- RUSLE factor aggregation by HRU.
- New sediment-delivery, deposition, gully, channel, or reservoir-routing logic.
- Changing Geneva watershed summary measure semantics; `peak_discharge` remains watershed-only.
- Adding new public routes unless the existing `query/geneva/hru_map_rows` contract proves insufficient.
- Replacing Geneva's selected unit-hydrograph assumptions with WEPP single-storm behavior.

## Stakeholders

- **Primary**: WEPPpy NoDb hydrology stack and Geneva UI/report consumers.
- **Reviewers**: Geneva kernel reviewer, WEPPcloud route/UI reviewer, QA reviewer.
- **Security Reviewer**: Required because this package changes public query payload behavior and UI-facing measure validation.
- **Informed**: RUSLE/event-erosion follow-on package maintainers.

## Success Criteria

- [ ] `geneva_run_batch` Rust response includes deterministic HRU-local peak runoff values for every completed HRU excess row.
- [ ] One-HRU runs produce HRU peak runoff equal to watershed `peak_discharge` within numeric tolerance.
- [ ] Multi-HRU regression proves HRU peak runoff differs from naive watershed-peak area apportionment when HRU excess timing/shape differs.
- [ ] `geneva/hru_event_measure_rows.parquet` includes `measure_id=hru_peak_runoff`, unit `m3_s`, and stable `(storm_id, hru_id, measure_id)` uniqueness.
- [ ] `POST /runs/<runid>/<config>/query/geneva/hru_map_rows` accepts `measure_id=hru_peak_runoff` and returns rows suitable for the HRU choropleth map.
- [ ] The Geneva Interactive Summary HRU Choropleth Map measure selector includes `HRU peak runoff` without adding watershed `peak_discharge` to HRU map options.
- [ ] Required Rust, Python, route, JavaScript, doc, and security validation gates pass or have documented unrelated blockers.

## Dependencies

### Prerequisites

- Geneva storm-shape runtime is implemented and closed: [20260428_geneva_storm_shape_control](../20260428_geneva_storm_shape_control/package.md).
- Current Geneva HRU event-measure artifact exists: `geneva/hru_event_measure_rows.parquet` with `runoff_depth` and `runoff_volume` rows.
- Current spec section: `wepppy/nodb/mods/geneva/specification.md` Section 12.5 defines `qpeak_m3_s` as a required input for future event erosion.
- Rust Geneva core functions already exist:
  - `/workdir/wepppyo3/geneva_core/src/uh.rs` `build_unit_hydrograph`
  - `/workdir/wepppyo3/geneva_core/src/convolution.rs` `convolve_excess_to_hydrograph`
  - `/workdir/wepppyo3/geneva_core/src/cn.rs` `run_batch_cn_excess`

### Blocks

- Full Geneva/RUSLE `musle_hru_event_v1` event-erosion package.
- Any UI that maps event erosion yield from `hru_event_erosion_rows.parquet`.

## Related Packages

- **Depends on**: [20260428_geneva_storm_shape_control](../20260428_geneva_storm_shape_control/package.md)
- **Related**: `wepppy/nodb/mods/geneva/work-packages/wp-08_routes_tasks_rq_wiring_query_report_api.md`
- **Related**: `wepppy/nodb/mods/geneva/work-packages/wp-11_geneva_ui_rq_engine_state_integration.md`
- **Follow-up**: Geneva/RUSLE `musle_hru_event_v1` event erosion rows and choropleth layer.

## Timeline Estimate

- **Expected duration**: 3-5 focused sessions
- **Complexity**: Medium
- **Risk level**: Medium-High

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The package changes public query measure validation, route payload behavior, and UI-facing data selection. It should not weaken run access checks, expose arbitrary file/path reads, or create unsafe query-engine behavior.
- **Security review artifact**: `docs/work-packages/20260429_geneva_hru_peak_event_erosion/artifacts/<date>_security_review.md`

Use `docs/prompt_templates/security_review_template.md` for the security artifact format and by-surface checks.

## Hardening and Callus Softening

This is a feature-enablement package, not an incident/remediation package.

- **Failure signature(s)**: N/A
- **Related prior hardening efforts**: N/A
- **Health signals**: New HRU peak rows are deterministic, same-grid map joins remain stable, and existing `runoff_depth`/`runoff_volume` HRU map behavior is unchanged.
- **Danger signals**: HRU peak values match area-apportioned watershed peak in all multi-HRU fixtures; `peak_discharge` becomes accepted for HRU map rows; route auth/error contracts drift.
- **Observation window**: Package validation plus first follow-on event-erosion implementation.
- **Temporary calluses introduced**: None planned.
- **Callus softening hypothesis**: N/A

## References

- `wepppy/nodb/mods/geneva/specification.md` - Geneva current contract; Section 12.4 HRU map rows and Section 12.5 future event-erosion design.
- `wepppy/nodb/mods/geneva/collaborators/hru_event_measure_service.py` - current HRU event-measure materialization/query surface.
- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py` - current per-storm batch persistence and kernel response handling.
- `wepppy/nodb/mods/geneva/schemas/query_schema.py` - current HRU map measure validation.
- `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py` - current summary/filter payload measure options.
- `wepppy/weppcloud/routes/nodb_api/geneva_bp.py` - current Flask query routes.
- `wepppy/weppcloud/templates/reports/geneva/summary.htm` - Geneva Interactive Summary report template.
- `wepppy/weppcloud/controllers_js/geneva_summary_report.js` - Geneva Interactive Summary JavaScript.
- `/workdir/wepppyo3/geneva_core/src/cn.rs` - Rust CN run-batch implementation.
- `/workdir/wepppyo3/geneva_core/src/convolution.rs` - Rust hydrograph convolution implementation.
- `/workdir/wepppyo3/cli_revision/src/geneva/mod.rs` - PyO3 Geneva API bridge.

## Deliverables

- Work-package scaffold and execution prompt:
  - `docs/work-packages/20260429_geneva_hru_peak_event_erosion/package.md`
  - `docs/work-packages/20260429_geneva_hru_peak_event_erosion/tracker.md`
  - `docs/work-packages/20260429_geneva_hru_peak_event_erosion/prompts/completed/geneva_hru_peak_event_erosion_execplan.md`
- Runtime deliverables after implementation:
  - HRU-local peak runoff in Rust `geneva_run_batch` response.
  - `hru_peak_runoff` rows in `geneva/hru_event_measure_rows.parquet`.
  - HRU Choropleth Map measure option in Geneva Interactive Summary.
  - Updated specification and tests.
  - Security review artifact and validation summary artifact.

## Closure Notes

- Closed on 2026-04-30 (UTC) after completing Rust, PyO3, WEPPpy materialization, query validation, route/UI integration, and documentation updates.
- Required review artifacts:
  - `artifacts/20260430_code_review.md`
  - `artifacts/20260430_qa_review.md`
  - `artifacts/20260430_security_review.md`
- Required validation artifact:
  - `artifacts/20260430_validation_summary.md`
- Validation completed with one known unrelated frontend lint baseline (`wepppy/weppcloud/controllers_js/__tests__/landuse_map_inline.test.js`) documented in the validation summary.

## Follow-up Work

- Implement full `musle_hru_event_v1` event-erosion rows using `hru_peak_runoff`, RUSLE factor aggregation, and source-hash invalidation.
- Add erosion mass/yield map measures only after the event-erosion artifact contract is implemented and validated.
