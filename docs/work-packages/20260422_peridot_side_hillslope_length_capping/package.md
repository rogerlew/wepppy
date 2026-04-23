# Peridot Side-Hillslope Length Capping + Provenance Mode

**Status**: Closed (2026-04-23)
**Timezone**: UTC

## Overview
A side hillslope (`topaz_id=11132`) in a 10 m project is currently estimated at `1192.9 m` because the receiving channel segment is only ~30 m. The current side-hillslope formula (`length = area / channel_length`) can therefore inflate hillslope length when channel segmentation is short, which directly perturbs runoff and erosion interpretation.

This package introduces a conservative cap for side hillslopes: use `min(area/channel_length, median_edge_source_length)` and recompute width to preserve area, while recording the length-estimation provenance in output tabular artifacts.

## Objectives
- Reduce side-hillslope length inflation caused by short receiving-channel segments.
- Preserve area invariants by updating width whenever capped length is selected.
- Add explicit length-estimation provenance fields to `watershed/hillslopes.parquet`.
- Keep established top/source hillslope logic intact unless explicitly changed.
- Add regression coverage for cap behavior, fallback behavior, and schema/output contract changes.

## Scope
This package is limited to Peridot hillslope abstraction behavior and output schema/manifest documentation updates required to make the new behavior explicit and auditable.

### Included
- Side-hillslope (`topaz_id % 10 in {2,3}`) length selection update in normal and representative abstractions.
- Width recomputation to preserve `area = width * length` when capped length is selected.
- New hillslope metadata fields for length provenance (mode + candidate values) in parquet outputs.
- Watershed manifest/schema updates and WEPPpy-facing contract documentation updates.
- Tests for side-hillslope cap activation, non-activation, and area preservation.

### Explicitly Out of Scope
- Changing top/source hillslope (`topaz_id % 10 == 1`) length logic.
- Changing hillslope slope scalar logic (`zonal_median_slope`) or channel slope behavior.
- Reworking channel tracing geometry/order algorithms in this package.
- Bulk historical-run backfill/reprocessing workflow design.

## Stakeholders
- **Primary**: WEPPcloud operators and analysts interpreting runoff/erosion from hillslope outputs.
- **Reviewers**: Peridot maintainers and WEPPpy watershed-integration maintainers.
- **Security Reviewer**: Not required for planned scope.
- **Informed**: Roads and disturbed-workflow users relying on hillslope length realism.

## Success Criteria
- [x] Side hillslopes (`%10 in {2,3}`) select `min(area/channel_length, median_edge_source_length)` when edge-median is valid.
- [x] Width is recomputed from area and selected length so `abs(width*length - area)` remains within floating-point tolerance.
- [x] Top/source hillslopes (`%10 == 1`) remain behaviorally unchanged.
- [x] `watershed/hillslopes.parquet` includes explicit length provenance fields (mode and candidate values).
- [x] Output schema docs/manifests reflect the new columns and semantics.
- [x] Targeted Peridot tests pass for the new length-selection contract and invariants.

## Dependencies

### Prerequisites
- Current Peridot abstraction code in `/workdir/peridot` (normal + representative paths).
- Existing watershed output schema docs in `wepppy/docs/schemas/`.
- Test fixtures covering side hillslopes with short receiving channels.

### Blocks
- Follow-on interpretation/reporting work that assumes stable side-hillslope lengths should wait for this package closeout.

## Related Packages
- **Related**: [20260321_peridot_watershed_parquet_manifest](../20260321_peridot_watershed_parquet_manifest/package.md)
- **Related**: [20260403_roads_map_drilldown](../20260403_roads_map_drilldown/package.md)
- **Follow-up**: Optional package for historical-run diagnostics/backfill policy once new fields are live.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium (hydrologic interpretation sensitivity and schema consumers).

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: This package changes numeric derivation logic and tabular schema for run outputs; no auth/session/secrets/route/queue attack-surface changes are planned.
- **Security review artifact**: `N/A`

## Compatibility and Regression Plan
This package introduces an additive watershed-output contract change. Existing columns remain unchanged; new provenance columns are additive and nullable-safe where required.

Backward compatibility strategy:
- Keep existing `length` and `width` keys/columns.
- Add new provenance fields without renaming/removing existing fields.
- Preserve top hillslope behavior and side-hillslope behavior when edge median is unavailable.

Regression strategy:
- Add deterministic fixture tests where `median_edge_source < area/channel` so cap activates.
- Add counterpart tests where cap should not activate.
- Assert area conservation and finite/non-negative length/width outputs.
- Verify manifest/schema outputs include new columns and definitions.

## References
- `/workdir/peridot/src/watershed_abstraction/flowpath_collection.rs` - current side/top hillslope length logic.
- `/workdir/peridot/src/wbt/wbt_watershed_abstraction.rs` - representative hillslope build path.
- `/workdir/peridot/src/watershed_abstraction/watershed_manifest.rs` - tabular schema summaries.
- `/workdir/peridot/tests/hillslope_slope_scalar.rs` - current hillslope scalar behavior tests.
- `docs/schemas/output-scope-contract.md` - WEPPpy output-contract documentation target.
- `docs/prompt_templates/codex_exec_plans.md` - ExecPlan authoring standard.

## Deliverables
- Updated Peridot length-selection implementation for side hillslopes in both abstraction modes.
- Updated hillslope metadata writers with additive provenance fields.
- Updated schema/manifest docs in Peridot and WEPPpy.
- New/updated tests proving cap logic and area-preservation invariants.
- Work-package tracker and ExecPlan records with decisions, surprises, and validation evidence.

## Follow-up Work
- Move MOFE slope segmentation off Python `SlopeFile.segmented_multiple_ofe` into `wepppyo3` for better runtime behavior and easier low-level optimization.
- Refactor `WatershedOperationsMixin._build_multiple_ofe` to canonical `createProcessPoolExecutor` orchestration (spawn-first with bounded fallback semantics).
- Deprecate legacy slope-file segmentation path after the new `wepppyo3` implementation is validated.

## Closure Notes

**Closed**: 2026-04-23

**Summary**: Implemented side-hillslope length capping in both Peridot abstraction paths (`non-representative` and `representative`) using `L_final = min(L_area, L_edge)` for side hillslopes, preserved top/source behavior, and added additive length provenance metadata columns to hillslope outputs. Updated watershed schema/manifest and WEPPpy output-contract docs, and validated the behavior with targeted regression tests covering cap activation, fallback/no-edge behavior, area preservation, and side-mode parity.

**Lessons Learned**: Constraining the behavioral change to side hillslopes kept hydrologic regression risk manageable while still addressing unrealistic length inflation. Adding explicit mode/candidate provenance fields made the contract auditable and reduced ambiguity for downstream runoff/erosion interpretation.

**Archive Status**: Package retained under `docs/work-packages/20260422_peridot_side_hillslope_length_capping/`; ExecPlan moved to `prompts/completed/` with an outcome note, and validation evidence retained in `artifacts/validation_summary.md`.
