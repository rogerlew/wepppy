# Disturbed BD Override + Rosetta WC/FC Recompute in WEPP Advanced Options

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, WEPP development users can optionally provide disturbed lookup `bd` overrides and, when needed, opt into Rosetta-based moisture recomputation for disturbed-generated soils. Default behavior remains unchanged unless both conditions are true: a numeric `bd` override exists and the new advanced-options checkbox is enabled.

## Progress

- [x] (2026-04-01 00:00Z) Reviewed disturbed lookup schema/upgrade flow, disturbed soil mutation paths, WEPP advanced options template/controller serialization, rq-engine payload persistence, and Soils NoDb fields.
- [x] (2026-04-01 00:00Z) Created work-package scaffold and authored package/tracker/active ExecPlan.
- [x] (2026-04-01 00:00Z) Freeze bd numeric bounds policy: enforce `0.6-2.2 g/cm^3` for disturbed override (developer-oriented margin).
- [x] (2026-04-01 07:45Z) Milestone 1: Added `bd` column to canonical disturbed lookup CSV and preserved additive schema-upgrade behavior for existing lookup files.
- [x] (2026-04-01 07:58Z) Milestone 2: Added Soils NoDb persisted toggle for Rosetta wc/fc recomputation on disturbed bd override.
- [x] (2026-04-01 08:06Z) Milestone 3: Added WEPP Advanced Options themable checkbox (default false) and wired controller/rq-engine serialization.
- [x] (2026-04-01 08:29Z) Milestone 4: Implemented disturbed top-horizon bd override + Rosetta recomputation gate in disturbed soil generation paths.
- [x] (2026-04-01 08:59Z) Milestone 5: Added/extended targeted tests for disturbed lookup/schema, disturbed mutation behavior, Soils/rq-engine persistence, and WEPP advanced-options rendering/serialization.
- [x] (2026-04-01 09:35Z) Milestone 6: Ran independent code and QA reviews, resolved findings, reran validations.
- [x] (2026-04-01 10:20Z) Milestone 7: Closed package docs (tracker + package + move plan to completed).

## Surprises & Discoveries

- Observation: Disturbed lookup schema upgrade is already additive and header-driven by the canonical default CSV.
  Evidence: `wepppy/nodb/mods/disturbed/disturbed.py::upgrade_disturbed_land_soil_lookup` appends missing fields and normalizes existing rows.

- Observation: Disturbed mutation currently forwards lookup replacements into `WeppSoilUtil.to_7778disturbed`/`to_over9000`, but there is no dedicated `bd` handling or Rosetta recomputation switch tied to lookup overrides.
  Evidence: `wepppy/nodb/mods/disturbed/disturbed.py::modify_soil` and `::modify_mofe_soils`; `wepppy/wepp/soils/utils/wepp_soil_util.py::to_over9000`.

- Observation: WEPP advanced options already use shared pure macros (`ui.checkbox_field`) in the soil options include, which is the correct themable path.
  Evidence: `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/clip_soils_depth.htm`.

- Observation: Public runtime API updates in soils/soil-util required synchronized `.pyi` updates to satisfy stub contracts.
  Evidence: reviewer finding and follow-up fixes in `wepppy/wepp/soils/utils/wepp_soil_util.pyi` and `wepppy/nodb/core/soils.pyi`; `wctl run-stubtest ...` now passes.

- Observation: `to_over9000` signature extension had positional compatibility risk if new parameter preceded `version`.
  Evidence: reviewer finding; fixed by placing `recompute_wp_fc_using_rosetta_on_bd_override` after `version`.

- Observation: Soils persistence test needed Redis NoDb cache bypass to ensure deterministic on-disk round-trip behavior.
  Evidence: `tests/nodb/test_soils_gridded_root_creation.py::test_rosetta_bd_toggle_round_trips_through_soils_nodb` monkeypatches `wepppy.nodb.base.redis_nodb_cache_client = None`.

## Decision Log

- Decision: Persist the new checkbox in `Soils` (`soils.nodb`) and set it from rq-engine WEPP request parsing, not client-local state.
  Rationale: The user explicitly requires serialization to `soils.nodb`, and the existing WEPP options persistence pattern already lives in `wepp_routes.py` + `Soils` properties.
  Date/Author: 2026-04-01 / Codex.

- Decision: Keep default behavior unchanged (`false` toggle) and gate Rosetta recomputation behind both toggle state and numeric `bd` override presence.
  Rationale: Minimizes regression risk and satisfies strict opt-in semantics.
  Date/Author: 2026-04-01 / Codex.

- Decision: Treat code review and QA review as mandatory closure criteria with artifact capture in package `artifacts/`.
  Rationale: Explicit user requirement.
  Date/Author: 2026-04-01 / Codex.

- Decision: Treat any non-empty non-numeric disturbed `bd` text as hard error (including `"none"`), while preserving only `None`/blank as valid no-op.
  Rationale: Aligns with explicit strict-validation requirement and avoids silent data-quality masking.
  Date/Author: 2026-04-01 / Codex.

- Decision: Preserve `to_over9000` positional compatibility by keeping `version` before the new optional recompute flag.
  Rationale: Prevents regressions for positional external callers while still supporting new behavior via keyword argument.
  Date/Author: 2026-04-01 / Codex.

## Outcomes & Retrospective

Outcome (2026-04-01): Completed all scoped implementation milestones and closure gates.

What shipped:
- Added `bd` column (after `avke`) to canonical disturbed lookup CSV with blank defaults.
- Preserved additive lookup upgrade behavior and added schema-order/default tests.
- Added Soils persisted toggle `rosetta_wc_fc_from_disturbed_bd_override`.
- Added WEPP Advanced Options checkbox with exact requested label and macro-based themable rendering.
- Wired rq-engine parsing/persistence for `run-wepp`, `run-wepp-watershed`, and `prep-wepp-watershed`.
- Implemented strict disturbed `bd` parse/bounds validation (`0.6-2.2 g/cm^3`), top-horizon-only `bd` override, and optional top-horizon Rosetta `wp/fc` recomputation.

Review outcomes:
- Reviewer: 1 high + 1 medium findings, both resolved.
- QA reviewer: 3 medium findings, all resolved.
- Artifacts captured at:
  - `docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/artifacts/code_review_findings.md`
  - `docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/artifacts/qa_review_findings.md`

Validation outcomes:
- Focused targeted suite: `138 passed`.
- Post-finding targeted rerun: `154 passed`.
- Route pair rerun: `23 passed`.
- Full suite: `2952 passed, 36 skipped`.
- Frontend: `wctl run-npm lint` pass, `wctl run-npm test -- wepp` pass.
- Stubs: `wctl check-test-stubs` pass, both targeted stubtests pass.

## Context and Orientation

This feature crosses five layers:

1. Disturbed lookup schema and CSV data:
   - `wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv`
   - `wepppy/nodb/mods/disturbed/disturbed.py` (lookup read/write/upgrade)

2. Disturbed soil mutation execution:
   - `Disturbed.modify_soil` and `Disturbed.modify_mofe_soils` in `wepppy/nodb/mods/disturbed/disturbed.py`
   - `WeppSoilUtil.to_7778disturbed` and `WeppSoilUtil.to_over9000` in `wepppy/wepp/soils/utils/wepp_soil_util.py`

3. WEPP Advanced Options UI + serialization:
   - `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/clip_soils_depth.htm`
   - `wepppy/weppcloud/controllers_js/wepp.js`

4. rq-engine payload handling:
   - `wepppy/microservices/rq_engine/wepp_routes.py`

5. Soils NoDb persistence:
   - `wepppy/nodb/core/soils.py`

Terms used in this plan:
- `bd`: bulk density override read from disturbed lookup; applies to the top horizon in disturbed-generated soils.
- Blank `bd` values are valid and mean "no override".
- Malformed numeric `bd` strings (for example `10.0.0`) are hard errors.
- Numeric `bd` overrides must be within `0.6-2.2 g/cm^3`.
- `wc/fc`: request language for moisture recomputation. Confirmed mapping is WEPP horizon `wp` (wilting point water content) and `fc` (field capacity), with recomputation limited to top horizon only.
- `Rosetta recomputation`: deriving moisture parameters from texture + bulk density using Rosetta during disturbed soil generation.

## Plan of Work

Milestone 1 updates the canonical disturbed lookup CSV header to include `bd` after `avke` (with blank values) and ensures existing run-scoped lookup files migrate additively without data loss. This milestone should be independently verifiable by schema-upgrade tests.

Milestone 2 adds a new persisted boolean field on `Soils` for the requested Rosetta behavior. The field defaults to `false`, is loaded from config/serialized state, and is available to disturbed mutation paths.

Milestone 3 adds a themable checkbox in WEPP Advanced Options (soil options section) with exact label text from request and default unchecked behavior. The checkbox must flow through form serialization and rq-engine parsing into the new Soils field.

Milestone 4 implements disturbed bd override logic and gated Rosetta recomputation in soil generation. `bd` override is applied only when numeric. Rosetta recomputation runs only when the Soils toggle is true and a numeric bd override exists, and it is limited to top horizon to model pre-vs-post wildfire effects.

Milestone 5 adds tests at every affected layer:
- disturbed lookup schema contract,
- disturbed single-OFE and MOFE mutation behavior,
- soil utility behavior for bd + Rosetta branch,
- rq-engine payload persistence,
- WEPP template/controller serialization.

Milestone 6 runs mandatory code and QA review passes, captures findings in artifacts, resolves medium/high issues, and reruns validations.

Milestone 7 closes the package by updating tracker/package docs and moving the ExecPlan to `prompts/completed/` with outcome notes.

## Concrete Steps

From repository root `/workdir/wepppy`:

1. Implement Milestone 1-4 code changes in disturbed lookup/schema, Soils persistence, WEPP UI/controller, rq-engine routes, and soil utility mutation logic.

2. Run focused tests while iterating:

    wctl run-pytest tests/nodb/mods/disturbed/test_lookup_contract.py --maxfail=1
    wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py tests/nodb/mods/disturbed/test_modify_soils_mofe.py --maxfail=1
    wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_soils_routes.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1

3. Run frontend checks for controller/template integration:

    wctl run-npm lint
    wctl run-npm test -- wepp

4. Run mandatory independent review passes and capture artifacts:

    - reviewer pass -> `docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/artifacts/code_review_findings.md`
    - qa_reviewer pass -> `docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/artifacts/qa_review_findings.md`

5. Resolve findings, rerun targeted tests, then run pre-handoff suite:

    wctl run-pytest tests --maxfail=1

6. Lint updated docs:

    wctl doc-lint --path docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc
    wctl doc-lint --path PROJECT_TRACKER.md

## Validation and Acceptance

Acceptance requires all of the following:

- Disturbed lookup CSV header includes `bd` directly after `avke`, with empty row values by default.
- Existing run-scoped lookup files auto-upgrade additively to include `bd` without losing edited values.
- Disturbed-generated soils apply top-horizon `bd` override only when lookup value is numeric.
- New WEPP advanced checkbox renders with shared themed checkbox control, default unchecked, and uses exact requested label text.
- Checkbox state persists to `soils.nodb` and is reloaded correctly.
- With checkbox enabled and numeric bd override present, disturbed soil generation recomputes moisture parameters via Rosetta.
- With checkbox disabled (or missing/invalid bd override), existing behavior is preserved.
- Mandatory review artifacts exist and medium/high findings are closed.

## Idempotence and Recovery

- CSV schema update is additive and rerunnable; upgrade path should be safe on repeated loads.
- Soils NoDb new field defaults safely to `false`, preserving backward compatibility for existing serialized state.
- UI/rq-engine wiring is additive; rollback is file-scoped if needed.
- If Rosetta recomputation contract is revised mid-implementation, update Decision Log and tests first, then code.

## Artifacts and Notes

- Package brief: `docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/package.md`
- Tracker: `docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/tracker.md`
- Review artifacts target paths:
  - `docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/artifacts/code_review_findings.md`
  - `docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc/artifacts/qa_review_findings.md`

## Interfaces and Dependencies

Target interfaces at completion:

- `wepppy/nodb/core/soils.py`
  - New persisted boolean property on `Soils` for Rosetta recomputation with disturbed bd overrides.
  - Default value: `False`.

- `wepppy/microservices/rq_engine/wepp_routes.py`
  - Parse new checkbox boolean field from WEPP form payload.
  - Persist field on `Soils` instance alongside existing soil options.

- `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/clip_soils_depth.htm`
  - Add themable checkbox control using `ui.checkbox_field(...)`.

- `wepppy/nodb/mods/disturbed/disturbed.py`
  - Ensure lookup schema includes `bd`.
  - Pass toggle state + replacements into soil mutation conversion paths.

- `wepppy/wepp/soils/utils/wepp_soil_util.py`
  - Apply numeric `bd` override to top horizon.
  - Add gated Rosetta recomputation branch for moisture parameters when requested.

Guidance decisions needed before coding final behavior:
- Confirm strict failure behavior when Rosetta cannot compute.

---
Revision Note (2026-04-01, Codex): Initial active ExecPlan authored during package creation.
