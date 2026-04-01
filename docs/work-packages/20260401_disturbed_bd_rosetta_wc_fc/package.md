# Disturbed BD Override and Rosetta WC/FC Recompute

**Status**: ✅ Complete (2026-04-01)

## Overview
This package adds an optional bulk-density (`bd`) override to disturbed landsoil lookup workflows and introduces a WEPP Advanced Options control that can trigger Rosetta-based moisture-parameter recomputation when that override is used. The goal is to support WEPP development calibration without changing default behavior for runs that do not opt in.

## Objectives
- Add a `bd` column to the disturbed lookup schema after `avke`, with empty values by default in the canonical CSV.
- Apply `bd` as a top-horizon bulk-density override only when the lookup value is defined and numeric.
- Treat `wc` as WEPP `wp` (wilting point) and recompute `wp`/`fc` for top horizon only when Rosetta recomputation is enabled.
- Add a themable WEPP Advanced Options checkbox (default `false`) labeled: `Estimate wc and fc using Rosetta when soils have bd override`.
- Persist the checkbox state to `soils.nodb` and honor it in disturbed soil-modification paths.
- When enabled and when `bd` override is active, recompute moisture fields via Rosetta during disturbed soil generation.
- Deliver regression tests and mandatory independent code-review + QA-review artifacts.

## Scope
This package covers disturbed lookup schema/data, disturbed soil mutation behavior, WEPP advanced-options UI wiring, rq-engine payload handling, soils NoDb persistence, and test/documentation updates required for those changes.

### Included
- Lookup schema + data update in `wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv`.
- Disturbed lookup schema-upgrade compatibility for existing run-scoped lookup files.
- Disturbed soil mutation behavior updates in single-OFE and MOFE paths.
- Rosetta recomputation wiring gated by an explicit Soils flag.
- WEPP Advanced Options UI checkbox and serialization path.
- `soils.nodb` persistence for the new checkbox setting.
- Unit/integration/microservice/frontend-template test coverage updates.
- Code review and QA review passes with artifact capture.

### Explicitly Out of Scope
- Changing default soil behavior when no `bd` override is present.
- Broad redesign of WEPP Advanced Options layout beyond adding the requested control.
- Non-disturbed soil pipelines that do not traverse disturbed lookup replacement logic.
- Any changes to unrelated disturbed lookup parameters.

## Stakeholders
- **Primary**: WEPP development users calibrating disturbed soil behavior.
- **Reviewers**: NoDb disturbed/soils maintainers, rq-engine maintainers, WEPPcloud controls maintainers.
- **Informed**: QA maintainers and users relying on disturbed lookup editor and WEPP advanced options.

## Success Criteria
- [x] Canonical disturbed lookup CSV header includes `bd` immediately after `avke`, and all rows are blank for `bd` by default.
- [x] Disturbed lookup schema upgrade remains additive and does not break existing run-scoped lookup files.
- [x] Disturbed soil generation applies `bd` only when value is numeric; empty `bd` is no-op and malformed non-numeric `bd` hard-fails.
- [x] Disturbed soil generation enforces developer-oriented numeric bounds `0.6-2.2 g/cm^3`.
- [x] Top-horizon bulk density is overridden in disturbed-generated soils when `bd` is valid.
- [x] New WEPP Advanced Options checkbox renders with existing themable control macros and defaults to unchecked.
- [x] Checkbox value is persisted in `soils.nodb` and flows through rq-engine WEPP request handling.
- [x] With checkbox enabled and numeric `bd` override active, disturbed soil generation recomputes top-horizon `wp/fc` via Rosetta.
- [x] Focused tests pass for disturbed lookup/schema, disturbed soil mutation, rq-engine payload persistence, and UI render/controller payload serialization.
- [x] Independent `reviewer` and `qa_reviewer` passes are completed; medium/high findings are resolved.

## Outcome Summary
- Implemented disturbed `bd` override support with strict parse/bounds validation and top-horizon-only mutation.
- Added persisted Soils toggle + WEPP advanced options checkbox + rq-engine wiring for Rosetta `wp/fc` recomputation gating.
- Completed mandatory review artifacts and resolved findings (stub contract parity, signature compatibility, strict non-numeric validation, persistence + 7778 coverage).
- Validation highlights:
  - `wctl run-pytest tests --maxfail=1` -> `2952 passed, 36 skipped`
  - `wctl run-npm lint` -> pass
  - `wctl run-npm test -- wepp` -> pass
  - `wctl run-stubtest wepppy.wepp.soils.utils.wepp_soil_util` -> pass
  - `wctl run-stubtest wepppy.nodb.core.soils` -> pass

## Dependencies

### Prerequisites
- Existing disturbed lookup schema-upgrade path in `wepppy/nodb/mods/disturbed/disturbed.py`.
- Existing WEPP Advanced Options rendering and request serialization flow:
  - `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/clip_soils_depth.htm`
  - `wepppy/weppcloud/controllers_js/wepp.js`
  - `wepppy/microservices/rq_engine/wepp_routes.py`
- Existing Soils NoDb persistence model in `wepppy/nodb/core/soils.py`.

### Blocks
- Follow-on documentation updates to user-facing disturbed lookup guidance pages, if requested by product/science stakeholders after implementation.

## Related Packages
- **Depends on**: [20260325_disturbed_lookup_hardening](../20260325_disturbed_lookup_hardening/package.md)
- **Related**: [20260330_disturbed_panel_modal](../20260330_disturbed_panel_modal/package.md)
- **Follow-up**: Potential package to generalize Rosetta recomputation toggles for non-disturbed soil edits.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions
- **Complexity**: Medium
- **Risk level**: Medium-High (cross-cutting behavior + scientific parameter side effects)

## References
- `wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv` - canonical disturbed lookup table to add `bd` column.
- `wepppy/nodb/mods/disturbed/disturbed.py` - lookup schema upgrade and disturbed soil mutation paths.
- `wepppy/wepp/soils/utils/wepp_soil_util.py` - disturbed soil conversion utilities and horizon parameter handling.
- `wepppy/nodb/core/soils.py` - `soils.nodb` persisted settings.
- `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/clip_soils_depth.htm` - current Soil Options UI include.
- `wepppy/microservices/rq_engine/wepp_routes.py` - WEPP run/prep payload parsing and Soils settings persistence.
- `tests/nodb/mods/disturbed/test_lookup_contract.py` - lookup schema and migration contract tests.
- `tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py` and `tests/nodb/mods/disturbed/test_modify_soils_mofe.py` - disturbed mutation behavior tests.
- `tests/microservices/test_rq_engine_wepp_routes.py` - payload persistence behavior tests.
- `tests/weppcloud/routes/test_pure_controls_render.py` - advanced options template render contract tests.

## Deliverables
- Work-package tracker + completed ExecPlan with milestone-level execution detail.
- Code changes implementing CSV/schema/UI/persistence/disturbed-Rosetta behavior.
- Regression test additions/updates across affected modules.
- Review artifacts:
  - `docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/artifacts/code_review_findings.md`
  - `docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/artifacts/qa_review_findings.md`

## Guidance Needed for End-to-End Execution
- Confirmed (2026-04-01): `wc` maps to wilting-point + field-capacity recomputation (`wp` + `fc`).
- Confirmed (2026-04-01): recomputation scope is top horizon only, aligned to pre-vs-post wildfire soil parameterization intent.
- Confirmed (2026-04-01): empty `bd` cells are valid (treated as no override).
- Confirmed (2026-04-01): non-numeric `bd` content (for example `10.0.0`) is a hard error.
- Numeric bounds precedent identified (2026-04-01):
  - WEPPpy soils docs recommend `0.8-2.0 g/cm^3` as realistic Rosetta input range.
  - WEPP-Forest `scon.for` clamps computed consolidated bulk density to `1000-1800 kg/m^3` (`1.0-1.8 g/cm^3`).
- Confirmed policy (2026-04-01): enforce developer-oriented disturbed `bd` override bounds `0.6-2.2 g/cm^3` (margin on both ends).

## Follow-up Work
- Add/refresh user-facing usersum guidance for disturbed `bd` override and Rosetta recomputation semantics once behavior is finalized.
