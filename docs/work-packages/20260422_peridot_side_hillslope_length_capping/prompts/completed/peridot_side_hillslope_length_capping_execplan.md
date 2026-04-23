# Peridot Side-Hillslope Length Capping and Length-Provenance Output

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, side hillslopes (`topaz_id % 10 in {2,3}`) will no longer be allowed to inflate solely because their receiving channel segment is short. Instead, side-hillslope length will be capped by edge/source flowpath evidence while preserving hillslope area by recomputing width. The resulting `watershed/hillslopes.parquet` rows will explicitly record which length-estimation mode was used, so analysts can audit runoff/erosion interpretation and detect cap-triggered hillslopes.

## Progress

- [x] (2026-04-23 01:27 UTC) ExecPlan authored and linked from work package tracker.
- [x] (2026-04-23 01:41 UTC) Implemented non-representative side-hillslope capping (`min(area/channel, median_edge_source)`) with area-preserving width recomputation.
- [x] (2026-04-23 01:42 UTC) Implemented representative side-hillslope capping using source-cell flowpath medians.
- [x] (2026-04-23 01:43 UTC) Added additive hillslope output provenance columns and updated watershed manifest/schema surfaces.
- [x] (2026-04-23 01:44 UTC) Added regression coverage for cap activation, non-activation/fallback, area preservation, and side-mode parity across abstraction paths.
- [x] (2026-04-23 01:47 UTC) Updated package tracker with implementation evidence, captured validation artifact, and passed docs lint on package + contract docs.

## Surprises & Discoveries

- Observation: Width recomputation can be applied uniformly as `width = area / L_final`; when uncapped (`L_final = area/channel_length`) this collapses back to `width = channel_length`.
  Evidence: Selection helper tests assert uncapped case returns `width == channel_length` (within floating-point tolerance) while preserving `width * length == area`.

- Observation: Representative abstraction did not expose edge-flowpath medians directly, so side-hillslope `L_edge` required explicit source-cell D8 tracing within each side hillslope.
  Evidence: Added `source_flowpath_length(...)` and `source_median_flowpath_length(...)` in `wbt_watershed_abstraction.rs`; representative mode tests now validate capped/non-capped side semantics.

## Decision Log

- Decision: Scope this change to side hillslopes (`%10 in {2,3}`) and keep top/source (`%10 == 1`) behavior unchanged.
  Rationale: The reported instability is side-hillslope inflation from short channel segments; limiting scope reduces unintended hydrologic regressions.
  Date/Author: 2026-04-23 / Codex.

- Decision: Additive output contract only; do not rename/remove existing hillslope columns.
  Rationale: Existing downstream consumers rely on `length` and `width`; provenance should be layered on top.
  Date/Author: 2026-04-23 / Codex.

- Decision: Use stable mode vocabulary with side/top distinction and fallback transparency.
  Rationale: Analysts need auditable semantics. Implemented side modes `side_edge_median_capped`, `side_area_over_channel`, `side_area_over_channel_no_edge`; top modes remain path-specific (`top_edge_median`, `top_representative_flowpath`).
  Date/Author: 2026-04-23 / Codex.

- Decision: Emit candidate-value columns as nullable numerics (`length_area_over_channel`, `length_edge_median`) in addition to mode.
  Rationale: The mode alone indicates branch choice, but candidate values improve diagnostics and permit post hoc QA on cap activation thresholds.
  Date/Author: 2026-04-23 / Codex.

## Outcomes & Retrospective

Implementation outcome: Side hillslopes now cap `length` by edge/source evidence in both abstraction modes while preserving area via width recomputation. Top/source behavior remains unchanged by design.

Validation outcome: Targeted Peridot tests pass for side cap activation, no-cap fallback, area preservation, and representative/non-representative side-mode parity. Manifest/schema tests confirm additive provenance fields are present.

Known gap: This execution did not rerun a full project-scale watershed for the specific `topaz_id=11132` screenshot case, so package closure relies on deterministic unit/integration coverage rather than a new run artifact snapshot.

## Context and Orientation

The current side-hillslope length logic is in Peridot:

- `/workdir/peridot/src/watershed_abstraction/flowpath_collection.rs`
  - `FlowpathCollection::abstract_subcatchment`
  - Side hillslopes currently use `width = chn_summary.length` then `length = area / width`.
  - Top hillslopes (`%10 == 1`) currently use edge/source median length.

- `/workdir/peridot/src/wbt/wbt_watershed_abstraction.rs`
  - `build_representative_hillslope`
  - Side hillslopes currently also use `length = area / channel.length`.

- `/workdir/peridot/src/watershed_abstraction/flowpath_collection.rs`
  - `get_edge_flowpaths2` and `flowpaths_median_length` provide edge/source median mechanics.

- `/workdir/peridot/src/watershed_abstraction/flowpath_collection.rs`
  - parquet metadata writers (`write_metadata_to_parquet` and related schema builders) currently do not include a length-mode column.

- `/workdir/peridot/src/watershed_abstraction/watershed_manifest.rs`
  - Output schema summaries should be updated when columns are added.

- `/workdir/wepppy/docs/schemas/output-scope-contract.md`
  - WEPPpy-side contract documentation should capture the new additive hillslope provenance field semantics.

## Plan of Work

Milestone 1 implements a deterministic length-selection helper for side hillslopes in the non-representative path. For side hillslopes, compute two candidates:

- `L_area = area / channel_length`
- `L_edge = median length of edge/source flowpaths`

Then select:

- `L_final = L_edge` only when `L_edge` is valid and `L_edge < L_area`
- otherwise `L_final = L_area`

Set width from area consistency:

- `W_final = area / L_final` in all cases.
- when no cap applies (`L_final = L_area`), this remains equivalent to `W_final = channel_length`.

Milestone 2 applies equivalent side-hillslope selection in representative mode. Use source-cell flowpath lengths as the `L_edge` basis (without changing top/source hillslope logic). Preserve representative-mode purpose while ensuring side lengths are capped by observed source/edge lengths.

Milestone 3 extends hillslope metadata output with additive provenance field(s). Minimum requirement is a mode column (for example `length_estimate_mode`) that records values such as `area_over_channel`, `edge_median_capped`, and `top_edge_median` (or equivalent stable vocabulary). Keep existing `length` column semantics as final selected length.

Milestone 4 adds tests and contract docs. Add fixture-backed tests for:

- cap-activation side case (`L_edge < L_area`)
- no-cap side case (`L_edge >= L_area` or unavailable)
- area preservation (`width * length` equals computed area within tolerance)
- representative path parity of mode semantics.

Update manifest schema summaries and WEPPpy output-scope docs with the new mode column and meanings.

## Concrete Steps

Working directory: `/workdir/peridot` for implementation, `/workdir/wepppy` for package/docs updates.

1. Implement side-length selection helper and wire non-representative path.

    cd /workdir/peridot
    rg -n "abstract_subcatchment|get_edge_flowpaths2|flowpaths_median_length" src/watershed_abstraction/flowpath_collection.rs

2. Implement representative-path side cap wiring.

    cd /workdir/peridot
    rg -n "build_representative_hillslope|select_representative_flowpath|build_source_cells" src/wbt/wbt_watershed_abstraction.rs

3. Add provenance field(s) to hillslopes metadata parquet schema/writers and manifest schema summary.

    cd /workdir/peridot
    rg -n "hillslope_schema|write_metadata_to_parquet|Field::new\(\"length\"" src/watershed_abstraction

4. Add tests for mode selection and area invariants.

    cd /workdir/peridot
    cargo test --test hillslope_slope_scalar -- --nocapture
    cargo test --test watershed_parquet_manifest -- --nocapture
    cargo test -- --nocapture side_hillslope

5. Update WEPPpy output-contract docs and lint changed docs.

    cd /workdir/wepppy
    wctl doc-lint --path docs/work-packages/20260422_peridot_side_hillslope_length_capping
    wctl doc-lint --path docs/schemas/output-scope-contract.md

Executed command results (2026-04-23 UTC):

- `cd /workdir/peridot && cargo test --test hillslope_slope_scalar -- --nocapture` -> passed (`2 passed; 0 failed`)
- `cd /workdir/peridot && cargo test representative_hillslope_length_modes_follow_selection_contract -- --nocapture` -> passed (`1 passed; 0 failed`)
- `cd /workdir/peridot && cargo test --test watershed_parquet_manifest -- --nocapture` -> passed (`3 passed; 0 failed`)
- `cd /workdir/peridot && cargo test side_length_selection -- --nocapture` -> passed (`3 passed; 0 failed`)
- `cd /workdir/wepppy && wctl doc-lint --path docs/work-packages/20260422_peridot_side_hillslope_length_capping` -> passed (`4 files validated, 0 errors, 0 warnings`)
- `cd /workdir/wepppy && wctl doc-lint --path docs/schemas/output-scope-contract.md` -> passed (`1 files validated, 0 errors, 0 warnings`)
- `cd /workdir/wepppy && wctl doc-lint --path docs/dev-notes/data_tables_standardization.spec.md` -> passed (`1 files validated, 0 errors, 0 warnings`)

## Validation and Acceptance

Acceptance is met when all of the following are true:

- A deterministic side-hillslope length cap exists in both abstraction paths and is limited to `topaz_id % 10 in {2,3}`.
- Top/source hillslope logic remains unchanged by tests and code inspection.
- `length` remains final selected value, and area-preserving width behavior is verified for capped rows.
- `watershed/hillslopes.parquet` contains additive length-provenance field(s) with documented mode vocabulary.
- Peridot targeted tests pass for changed behaviors.
- WEPPpy output-contract docs explicitly describe the new additive field(s).

When possible, include a diagnostic artifact for a known inflated side hillslope showing before/after `length`, `width`, and selected mode.

## Idempotence and Recovery

All edits are additive and local to Peridot hillslope abstraction plus docs. If a milestone partially fails, rerun tests after each file group. Keep mode vocabulary stable once introduced; if renamed during development, update schema docs and tests in the same commit. Do not remove existing columns or alter unrelated top-hillslope logic.

## Artifacts and Notes

Store validation notes in this package:

- `docs/work-packages/20260422_peridot_side_hillslope_length_capping/artifacts/validation_summary.md`
- `docs/work-packages/20260422_peridot_side_hillslope_length_capping/artifacts/reviewer_findings.md` (if review pass is run)

Capture at least one table/snippet with:

- `topaz_id`
- `area_m2`
- `length_before`
- `length_after`
- `width_after`
- `length_estimate_mode`

## Interfaces and Dependencies

Required final interfaces/contract expectations:

- Peridot side-hillslope selection logic must expose a stable mode value written to hillslope tabular metadata.
- `length` and `width` remain present and represent final selected geometry.
- Added metadata fields are backward compatible (additive only).
- Documentation references:
  - `/workdir/peridot/src/watershed_abstraction/watershed_manifest.rs`
  - `/workdir/wepppy/docs/schemas/output-scope-contract.md`

## Revision Notes

- 2026-04-23 / Codex: Initial ExecPlan authored from user-requested side-hillslope cap design and provenance-tracking requirement.
- 2026-04-23 / Codex: Updated plan to reflect implemented side-cap logic (both abstraction paths), additive provenance fields, targeted validation evidence, and final design decisions.
- 2026-04-23 / Codex: Synced completion state with tracker/doc-lint reruns and added explicit mode/value semantics in WEPPpy data-table contract notes.
