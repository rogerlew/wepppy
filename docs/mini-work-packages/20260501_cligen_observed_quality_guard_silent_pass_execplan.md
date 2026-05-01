# ExecPlan: CLIGEN Observed Quality-Guard Silent-Pass, UI Exposure, and User Messaging

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and is scoped as an ad hoc mini work package under `docs/mini-work-packages/`.

## Purpose / Big Picture

Observed climate builds can fail when CLIGEN reports convergence-quality markers. Users need clear guidance when this happens, and operators need an optional bypass to keep workflows moving for advanced runs. After this change, Climate NoDb supports a config-backed `silent_pass_observed_quality_guard` flag, the Climate UI exposes it under Advanced options, default behavior is enabled (`true`) with warning visibility, and users can disable the toggle to enforce strict convergence failure.

## Progress

- [x] (2026-05-01 20:12Z) Added CLIGEN observed quality-guard bypass parameter and return signal in `wepppy/climates/cligen/cligen.py`.
- [x] (2026-05-01 20:16Z) Added quality-guard translation helper and message mapping in `wepppy/nodb/core/climate_build_helpers.py`.
- [x] (2026-05-01 20:20Z) Added `Climate.silent_pass_observed_quality_guard` property and config initialization in `wepppy/nodb/core/climate.py` and `wepppy/nodb/core/climate.pyi`.
- [x] (2026-05-01 20:22Z) Added defaults/config entries in `wepppy/nodb/configs/_defaults.toml` and `wepppy/nodb/configs/disturbed9002.cfg`.
- [x] (2026-05-01 20:24Z) Added warning-to-UI status-stream publishing when bypass is enabled in `wepppy/nodb/core/climate.py`.
- [x] (2026-05-01 20:27Z) Added climate route endpoint for toggling silent-pass in `wepppy/weppcloud/routes/nodb_api/climate_bp.py`.
- [x] (2026-05-01 20:29Z) Added Climate Advanced options checkbox + controller wiring in `wepppy/weppcloud/templates/controls/climate_pure.htm` and `wepppy/weppcloud/controllers_js/climate.js`.
- [x] (2026-05-01 20:31Z) Updated end-user documentation in `wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md`.
- [x] (2026-05-01 20:34Z) Updated controller developer docs/event contract in `wepppy/weppcloud/controllers_js/README.md` and `wepppy/weppcloud/controllers_js/AGENTS.md`.
- [x] (2026-05-01 20:45Z) Rebuilt controllers bundle and ran targeted validation suites.
- [x] (2026-05-01 22:10Z) Ensured observed multiple/interpolated build paths propagate quality-guard bypass state and publish warning status in parent orchestrators.
- [x] (2026-05-01 22:20Z) Restricted silent-pass handling to observed climate paths; removed silent-pass plumbing from future-mode build invocation.
- [x] (2026-05-01 23:05Z) Switched default contract to `silent_pass_observed_quality_guard=true` across runtime fallback and config defaults, and updated usersum guidance.
- [x] (2026-05-01 23:20Z) Re-ran targeted climate/no-db/routes tests and doc lint with passing results.
- [x] (2026-05-02 01:05Z) Persisted silent-pass quality-guard warning in Climate NoDb, surfaced it in climate report summary UI, and added regression coverage for helper/router/template behavior.

## Surprises & Discoveries

- Observation: `Climate.runid` is read-only and derived from working directory; tests cannot assign it directly.
  Evidence: `tests/nodb/test_climate_facade_collaborators.py` initially failed with `AttributeError: property 'runid' of 'Climate' object has no setter`; fixed by asserting against `f"{climate.runid}:climate"`.

## Decision Log

- Decision: Set default behavior to bypass (`silent_pass_observed_quality_guard=true`) while publishing warnings, with user opt-out for strict failure mode.
  Rationale: Improve workflow continuity while preserving operator visibility into quality-guard events.
  Date/Author: 2026-05-02 / Codex.

- Decision: Translate quality-guard RuntimeError into a user-facing message: `CLIGEN failed to converge, try selecting different station or setting Adjust MX .5 P Values`.
  Rationale: Raw CLIGEN marker text is not actionable for end users.
  Date/Author: 2026-05-01 / Codex.

- Decision: When bypass is enabled, publish warning text to climate status stream.
  Rationale: Preserve visibility of degraded quality while allowing run continuation.
  Date/Author: 2026-05-01 / Codex.

- Decision: Persist bypass warning text on Climate and render it in the climate report summary.
  Rationale: Status stream notifications are transient; summary persistence ensures users still see the warning after build completion and page reload.
  Date/Author: 2026-05-02 / Codex.

- Decision: Apply `silent_pass_observed_quality_guard` only to observed climate build modes.
  Rationale: The option name and user contract are observed-specific; future-mode behavior should remain independent.
  Date/Author: 2026-05-01 / Codex.

## Outcomes & Retrospective

The feature set is implemented end-to-end across CLIGEN execution, NoDb orchestration, run configuration, climate API/controller wiring, UI advanced options, and usersum documentation. The observed multiple/interpolated workflows now publish warning status when bypass occurs, future-mode invocation no longer consumes the observed-only silent-pass flag, and bypass warnings now persist to the climate report summary. Targeted Python and JS tests pass, and docs lint passes for the updated end-user climate options page.

Residual follow-up (optional): if operators want this new advanced toggle called out in other user-facing indices or release notes, add those references in a separate docs-only change.

## Context and Orientation

Observed climate builds are orchestrated by `wepppy/nodb/core/climate.py` and helper routines in `wepppy/nodb/core/climate_build_helpers.py`, which call into CLIGEN (`wepppy/climates/cligen/cligen.py`). Climate UI actions are managed by `wepppy/weppcloud/controllers_js/climate.js` and routed through `wepppy/weppcloud/routes/nodb_api/climate_bp.py`, with controls rendered in `wepppy/weppcloud/templates/controls/climate_pure.htm`. End-user climate option guidance lives in usersum at `wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md`.

## Plan of Work

Implement a narrow, additive control flag that leaves existing behavior unchanged unless explicitly enabled. Ensure all observed-build paths receive the flag, preserve current RuntimeError contract where required, and expose the toggle in the existing Advanced options panel. Add explicit user messaging and tests for both fail and bypass behavior.

## Concrete Steps

From `/workdir/wepppy`:

1. Update CLIGEN observed-run method signature and quality-guard handling.
2. Thread silent-pass flag through NoDb climate helpers and facade properties.
3. Add config defaults and disturbed profile value.
4. Add climate API task route + Climate controller action + Advanced options checkbox.
5. Update usersum climate options docs.
6. Rebuild JS bundle:
   - `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`
7. Validate:
   - `wctl run-pytest tests/weppcloud/routes/test_climate_bp.py tests/nodb/test_climate_build_helpers.py tests/nodb/test_climate_facade_collaborators.py tests/climate/test_cligen_run_observed_retries.py --maxfail=1`
   - `wctl run-npm test -- climate`
   - `wctl doc-lint --path wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md`

## Validation and Acceptance

Acceptance criteria:

- Observed CLIGEN quality-guard failures show the user-facing convergence error when silent-pass is disabled.
- Silent-pass can be toggled from Climate Advanced options and persists through Climate NoDb setter.
- When silent-pass is enabled and quality guard is tripped, climate build continues and warning text is surfaced in the climate report summary and published to the climate status channel.
- Config defaults to silent-pass enabled unless explicitly disabled.
- Targeted Python tests, JS controller tests, and end-user doc lint pass.

## Idempotence and Recovery

All edits are additive and safe to reapply. Rebuilding controllers bundle and rerunning tests are idempotent. If a regression appears, disable silent-pass (`false`) to restore strict pre-change behavior immediately.

## Artifacts and Notes

Primary changed surfaces:

- `wepppy/climates/cligen/cligen.py`
- `wepppy/nodb/core/climate.py`
- `wepppy/nodb/core/climate_build_helpers.py`
- `wepppy/weppcloud/routes/nodb_api/climate_bp.py`
- `wepppy/weppcloud/controllers_js/climate.js`
- `wepppy/weppcloud/templates/controls/climate_pure.htm`
- `wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md`

## Interfaces and Dependencies

No new external dependencies were added. The implementation reuses existing StatusStream plumbing (`StatusMessenger`) and existing climate route/controller conventions.

Revision note (2026-05-01 20:45Z, Codex): Created and completed this mini work-package ExecPlan as the user-requested work-package artifact for the silent-pass quality-guard change set.
Revision note (2026-05-02 00:00Z, Codex): Updated default-state contract to `silent_pass_observed_quality_guard=true` and aligned acceptance text with the observed-mode warning-first behavior.
Revision note (2026-05-02 00:20Z, Codex): Closed out with observed-mode-only enforcement, multi/interpolated warning propagation coverage, and final validation evidence.
Revision note (2026-05-02 01:05Z, Codex): Added persisted summary-warning behavior for silent-pass quality-guard bypass and updated tests/docs accordingly.
