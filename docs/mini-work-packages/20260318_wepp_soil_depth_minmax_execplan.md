# ExecPlan: Add Dual Soil Depth Clipping (Maximum + Minimum) in WEPP Advanced Options

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users need two explicit soil-depth controls in WEPP advanced options: one to cap deep soils (maximum depth clipping) and one to raise shallow soils to a floor (minimum depth clipping). After this change, users can run WEPP with either or both controls and see predictable behavior: maximum clipping truncates deep profiles, minimum clipping extends shallow profiles, and invalid ranges are rejected with a clear error.

The key requirement is backward compatibility. Existing `clip_soils` and `clip_soils_depth` semantics must remain maximum clipping so prior runs do not change behavior.

## Progress

- [x] (2026-03-18 23:55Z) Authored initial ExecPlan and registered it as the active ad hoc plan in root `AGENTS.md`.
- [x] (2026-03-19 00:02Z) Implemented `Soils` minimum clipping fields (`clip_soils_minimum`, `clip_soils_minimum_depth`) and fixed the config-key defect so `_clip_soils_depth` reads `clip_soils_depth`.
- [x] (2026-03-19 00:04Z) Added `WeppSoilUtil.ensure_minimum_soil_depth(min_depth)` and threaded minimum+maximum clipping through `prep_soil`, `_prep_multi_ofe`, and prep-service task arguments (minimum applied before maximum).
- [x] (2026-03-19 00:05Z) Updated rq-engine WEPP payload parsing to support minimum fields, added explicit canonical 400 validation for invalid min/max ranges, and normalized new booleans across WEPP endpoints.
- [x] (2026-03-19 00:06Z) Updated WEPP advanced soils UI with dual controls in required layout text (`Clip Soils Maximum Depth`, `Soils Maximum Depth`, `Clip Soils Minimum Depth`, `Soils Minimum Depth`).
- [x] (2026-03-19 00:09Z) Added/updated utility, route, and controller tests for minimum clipping behavior, invalid ranges, and payload serialization.
- [x] (2026-03-19 00:14Z) Ran required validation commands (targeted pytest, controller Jest, npm lint, full pytest sweep, stub checker, and required doc-lint checks).
- [x] (2026-03-19 00:18Z) Completed independent `reviewer` pass; no high/medium findings. Resolved low-severity coverage gaps by adding endpoint-range validation coverage and prep-order regression coverage.
- [x] (2026-03-19 00:21Z) Completed independent `qa_reviewer` pass; no high/medium findings. Resolved low-severity QA findings by adding config-key mapping coverage, template render contract checks, and parameterized endpoint validation tests.
- [x] (2026-03-19 00:28Z) Re-ran full validation sweep after review-driven test additions (`wctl run-pytest tests --maxfail=1`, `wctl check-test-stubs`, and required docs lint checks).
- [x] (2026-03-19 00:28Z) Finalized outcomes, evidence, and handoff notes.

## Surprises & Discoveries

- Observation: `Soils.__init__` currently reads `_clip_soils_depth` from the wrong config option key (`clip_soils`), which is a confirmed defect in option loading.
  Evidence: `wepppy/nodb/core/soils.py` uses `self.config_get_float('soils', 'clip_soils', 1000)` for depth.

- Observation: `clip_soils` is currently wired as maximum clipping in utility, prep, route, UI, and tests; changing semantics would break compatibility.
  Evidence: `wepppy/wepp/soils/utils/wepp_soil_util.py::clip_soil_depth`, `wepppy/nodb/core/wepp.py`, `wepppy/microservices/rq_engine/wepp_routes.py`, and `wepppy/weppcloud/controllers_js/__tests__/wepp.test.js`.

- Observation: `run-wepp-watershed` boolean parsing previously omitted `clip_soils`, which could misinterpret non-JSON string booleans (`"false"` -> truthy via `bool("false")`).
  Evidence: `wepppy/microservices/rq_engine/wepp_routes.py` boolean-field sets before this change included `clip_soils` for `run-wepp`/`prep-wepp-watershed` but not for `run-wepp-watershed`.

- Observation: independent review gates identified only low-severity test coverage gaps (no correctness regressions), and all identified gaps were resolved in-followup patches.
  Evidence: `reviewer` + `qa_reviewer` outputs flagged endpoint parity coverage, prep-order regression coverage, config-key mapping coverage, and template-render contract coverage; new tests were added in `tests/microservices/test_rq_engine_wepp_routes.py`, `tests/wepp/test_wepp_regressions.py`, `tests/nodb/test_soils_gridded_root_creation.py`, and `tests/weppcloud/routes/test_pure_controls_render.py`.

## Decision Log

- Decision: Keep `clip_soils` + `clip_soils_depth` as maximum clipping and add separate minimum fields.
  Rationale: Prevent silent behavior drift for existing runs and payload clients.
  Date/Author: 2026-03-18 / Codex

- Decision: Implement minimum clipping by extending only the final horizon depth to the configured floor.
  Rationale: Minimal and deterministic implementation; preserves horizon ordering and avoids introducing synthetic extra horizons.
  Date/Author: 2026-03-18 / Codex

- Decision: Enforce explicit validation when both controls are enabled and `minimum_depth > maximum_depth`.
  Rationale: Avoid ambiguous apply order and hidden coercion.
  Date/Author: 2026-03-18 / Codex

- Decision: Include mandatory independent subagent review and QA review gates before completion.
  Rationale: User-requested assurance and regression-risk containment.
  Date/Author: 2026-03-18 / Codex

- Decision: Default `clip_soils_minimum_depth` to `0` when absent.
  Rationale: Additive backward-compatible default that cannot change behavior unless the new minimum toggle is explicitly enabled.
  Date/Author: 2026-03-19 / Codex

- Decision: Normalize `clip_soils` and `clip_soils_minimum` booleans for all three WEPP endpoints, including `run-wepp-watershed`.
  Rationale: Keep coercion behavior consistent across JSON/form callers and avoid string-truthiness edge cases.
  Date/Author: 2026-03-19 / Codex

- Decision: Accept reviewer/QA suggestions to expand regression tests, and consolidate endpoint invalid-range tests with `pytest.mark.parametrize`.
  Rationale: Close low-severity regression gaps while improving maintainability and reducing duplicated assertions.
  Date/Author: 2026-03-19 / Codex

## Outcomes & Retrospective

Completed outcomes (2026-03-19 00:28Z):

- Implemented dual soil-depth clipping controls with backward compatibility preserved: `clip_soils`/`clip_soils_depth` remain maximum clipping semantics, while new `clip_soils_minimum`/`clip_soils_minimum_depth` provide minimum-depth extension.
- Fixed confirmed config-key defect in `Soils.__init__` (`clip_soils_depth` now loads from the correct option key).
- Added minimum-depth utility operation and threaded minimum+maximum behavior through both prep flows, with deterministic apply order (minimum first, then maximum).
- Added explicit canonical 400 response for invalid combined ranges (`minimum > maximum`) and normalized boolean parsing for new/existing clipping booleans across WEPP endpoints.
- Updated advanced UI layout labels and field wiring exactly as requested, plus controller serialization coverage.
- Completed full validation set plus two mandatory independent review gates, including a final full-suite rerun after review-driven coverage additions (`2371 passed, 34 skipped`).

Review gate disposition:

- `reviewer`: no high/medium findings; low findings fully resolved by adding endpoint parity invalid-range tests and prep-order regression coverage.
- `qa_reviewer`: no high/medium findings; low findings fully resolved by adding Soils config-key mapping test, template render contract assertions, and parametric cleanup for route invalid-range tests.

Residual risks:

- No open high/medium risks remain from implementation or review.
- Standard residual risk remains for future drift if unrelated code paths bypass shared route handler logic; mitigated by the added route, utility, and template tests.

## Context and Orientation

This feature spans NoDb state, soil-file transformation, rq-engine request parsing, WEPP UI controls, and tests.

The existing maximum clipping path starts in run payload parsing and lands in the WEPP soil utility:

- `wepppy/microservices/rq_engine/wepp_routes.py` reads `clip_soils` and `clip_soils_depth` into `Soils`.
- `wepppy/nodb/core/soils.py` stores those settings on the Soils singleton.
- `wepppy/nodb/core/wepp.py` and `wepppy/nodb/core/wepp_prep_service.py` apply settings during `.sol` preparation.
- `wepppy/wepp/soils/utils/wepp_soil_util.py::clip_soil_depth(max_depth)` performs truncation.
- `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/clip_soils_depth.htm` renders the current advanced soils controls.
- `wepppy/weppcloud/controllers_js/wepp.js` serializes the form as JSON payload for rq-engine endpoints.
- Tests currently assert `clip_soils` behavior in:
  - `tests/wepp/soils/utils/test_wepp_soil_util.py`
  - `tests/microservices/test_rq_engine_wepp_routes.py`
  - `wepppy/weppcloud/controllers_js/__tests__/wepp.test.js`

Non-obvious term definitions used in this plan:

- “Maximum clipping”: if profile depth exceeds threshold, truncate to threshold.
- “Minimum clipping”: if profile depth is below threshold, extend to threshold.
- “Horizon ordering”: cumulative `solthk` depths must remain monotonic increasing in a soil file.

## Plan of Work

Milestone 1 updates Soils state and defaults. Add two new Soils properties for minimum clipping (`clip_soils_minimum`, `clip_soils_minimum_depth`) while preserving existing maximum fields unchanged. Fix the confirmed config key bug for `_clip_soils_depth` to read from `clip_soils_depth`.

Milestone 2 adds the minimum operation to the soil utility and applies it in prep paths. Add a new method in `WeppSoilUtil` that enforces a minimum cumulative depth by updating the final horizon depth when needed. Thread both minimum and maximum settings through `prep_soil` and the multi-OFE prep path. Apply minimum first, then maximum, but reject invalid ranges early so order does not mask errors.

Milestone 3 updates rq-engine request parsing and validation. Extend `_handle_run_wepp_request` to parse minimum fields and store them in `Soils`. Add explicit validation that returns a canonical 400 error if both enabled and minimum depth is greater than maximum depth. Include new booleans in endpoint boolean-field sets where applicable.

Milestone 4 updates UI layout and labels to match requested layout exactly in the advanced soils card:

    [ ] Clip Soils Maximum Depth
    Soils Maximum Depth [          ] <units>

    [ ] Clip Soils Minimum Depth
    Soils Minimum Depth [          ] <units>

Keep existing field names for maximum controls (`clip_soils`, `clip_soils_depth`) and add new minimum field names (`clip_soils_minimum`, `clip_soils_minimum_depth`).

Milestone 5 extends tests. Add utility tests for minimum depth behavior (no-op above floor, extension below floor, header provenance), route tests for new fields and invalid min/max combinations, and controller tests asserting the new form payload fields are serialized.

Milestone 6 performs full validation and required review gates. Run targeted and broader tests/lint. Then run a risk-focused independent subagent review and a separate QA-focused review. Resolve findings and document all outcomes in this plan.

## Concrete Steps

Run from repository root:

    cd /workdir/wepppy

1. Implement NoDb state and stubs.

   Edit:
   - `wepppy/nodb/core/soils.py`
   - `wepppy/nodb/core/soils.pyi`
   - `stubs/wepppy/nodb/core/soils.pyi`

2. Implement soil utility minimum operation and typing/tests.

   Edit:
   - `wepppy/wepp/soils/utils/wepp_soil_util.py`
   - `wepppy/wepp/soils/utils/wepp_soil_util.pyi`
   - `tests/wepp/soils/utils/test_wepp_soil_util.py`

3. Thread options through prep/orchestration and route parsing.

   Edit:
   - `wepppy/nodb/core/wepp.py`
   - `wepppy/nodb/core/wepp_prep_service.py`
   - `wepppy/microservices/rq_engine/wepp_routes.py`
   - `tests/microservices/test_rq_engine_wepp_routes.py`

4. Update WEPP advanced soils UI and controller tests.

   Edit:
   - `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/clip_soils_depth.htm`
   - `wepppy/weppcloud/controllers_js/__tests__/wepp.test.js`

5. Update UI docs/control inventory for new fields.

   Edit:
   - `docs/ui-docs/control-ui-styling/control-inventory.md`

6. Run targeted validation.

    wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py
    wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py
    wctl run-npm test -- wepp
    wctl run-npm lint

7. Run broader sanity checks.

    wctl run-pytest tests --maxfail=1
    wctl check-test-stubs

8. Run docs checks for changed docs files.

    wctl doc-lint --path docs/mini-work-packages/20260318_wepp_soil_depth_minmax_execplan.md
    wctl doc-lint --path docs/ui-docs/control-ui-styling/control-inventory.md
    wctl doc-lint --path AGENTS.md

9. Independent subagent review gate (risk-focused correctness/regressions).

    Use a `reviewer` agent to review the complete diff and list severity-ordered findings with file/line references.

10. Independent QA review gate (maintainability + test quality).

    Use a `qa_reviewer` agent to review test adequacy, readability, naming, and maintainability risks.

11. Address findings, rerun affected tests, and update this ExecPlan sections (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`).

## Validation and Acceptance

Acceptance is complete when all behaviors below are true and verified:

- Legacy compatibility:
  - With only `clip_soils=true` and `clip_soils_depth=1000`, soils are clipped to maximum depth exactly as before.

- New minimum behavior:
  - With `clip_soils_minimum=true` and `clip_soils_minimum_depth=200`, profiles shallower than 200 mm are extended to 200 mm; deeper profiles are unchanged.

- Combined behavior:
  - With both toggles on and `minimum_depth <= maximum_depth`, both rules apply predictably.
  - With both toggles on and `minimum_depth > maximum_depth`, route returns canonical 400 error with a clear message.

- UI behavior:
  - Advanced soils panel shows separate maximum and minimum controls with requested labels and units.

- Tests and tooling:
  - All targeted tests pass.
  - Broader sanity checks pass (or any unavoidable failures are documented with rationale and unaffected scope evidence).

## Idempotence and Recovery

All edits are additive or local modifications and can be re-run safely.

If a checkpoint fails:

- Revert only the affected files.
- Re-run the targeted test subset for that milestone.
- Re-apply the smallest change needed.

For route validation logic, prefer explicit 400 responses over silent coercion.

## Artifacts and Notes

Capture concise evidence snippets during implementation:

- Route validation failure example for invalid min/max: `tests/microservices/test_rq_engine_wepp_routes.py::test_wepp_endpoints_reject_invalid_minimum_maximum_depth_range` verifies canonical 400 + code `invalid_soil_depth_range` across all three WEPP endpoints.
- Utility minimum extension/no-op evidence: `tests/wepp/soils/utils/test_wepp_soil_util.py::test_ensure_minimum_soil_depth_extends_last_horizon` and `::test_ensure_minimum_soil_depth_noop_when_depth_already_sufficient`.
- UI payload serialization evidence: `wepppy/weppcloud/controllers_js/__tests__/wepp.test.js` asserts serialized payload contains `clip_soils_minimum` and `clip_soils_minimum_depth`.
- Reviewer findings summary: low-only coverage gaps; resolved by adding endpoint parity + prep-order coverage (`tests/wepp/test_wepp_regressions.py::test_prep_soil_applies_minimum_before_maximum_clip`).
- QA findings summary: low-only contract/test maintainability gaps; resolved by adding config-key coverage (`tests/nodb/test_soils_gridded_root_creation.py::test_init_reads_depth_config_keys_with_expected_names`), rendered template contract coverage (`tests/weppcloud/routes/test_pure_controls_render.py::test_clip_soils_advanced_template_renders_dual_depth_controls`), and route test parameterization.

## Interfaces and Dependencies

New/updated interfaces expected:

- `Soils` properties:
  - `clip_soils_minimum: bool`
  - `clip_soils_minimum_depth: float`

- `WeppSoilUtil` new method:
  - `ensure_minimum_soil_depth(min_depth: float) -> None`

- `prep_soil(...)` argument tuple updated to include minimum toggle/depth.

- rq-engine WEPP run payload supports:
  - `clip_soils_minimum` (bool)
  - `clip_soils_minimum_depth` (int/float mm)

Review gates are mandatory:

- Independent `reviewer` subagent pass after implementation/tests.
- Independent `qa_reviewer` pass after reviewer findings are resolved.

## Revision Note

Initial plan created to implement dual maximum/minimum soil depth controls with explicit compatibility preservation and mandatory subagent/QA review gates.
Updated 2026-03-19 00:14Z to reflect completed implementation milestones, validation evidence status, new discoveries/decisions, and remaining review-gate work.
Updated 2026-03-19 00:21Z to record independent review findings, resolutions, final validation state, and completed retrospective outcomes.
Updated 2026-03-19 00:28Z to capture the final post-review full-suite rerun results and final handoff state.
