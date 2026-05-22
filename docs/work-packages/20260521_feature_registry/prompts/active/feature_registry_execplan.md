# ExecPlan: Implement WEPPcloud Feature and Config Registries as Single Authority

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, WEPPcloud lifecycle labels and availability policy come from one authority boundary with two registries:

- `feature_registry` for run feature/mod surfaces.
- `config_registry` for interface launch configs.

Users will see consistent maturity labeling (`stable`, `preview`, `experimental`, `deprecated`, `internal`) and maintainers will update one subsystem instead of multiple hardcoded maps and template blocks.

The behavior is visible by rendering run/header/interface surfaces with registry-driven labels and by observing backend policy decisions rely on registry metadata instead of local literals.

## Progress

- [x] (2026-05-22 02:12 UTC) Work package scaffold created (`package.md`, `tracker.md`) and this active ExecPlan authored.
- [x] (2026-05-22 03:05 UTC) Scope updated to dual-registry MVP in one package (`feature_registry` + `config_registry`).
- [x] (2026-05-22 04:15 UTC) Implement registry contracts and runtime loader.
- [x] (2026-05-22 04:15 UTC) Migrate `project_bp` to feature-registry-backed metadata.
- [x] (2026-05-22 04:15 UTC) Migrate `run_0_bp` + header template consumers to feature-registry-backed metadata and availability.
- [x] (2026-05-22 04:15 UTC) Migrate `weppcloud_site/interfaces` launch surfaces to config-registry-backed metadata and availability.
- [x] (2026-05-22 04:15 UTC) Add maturity badge rendering in targeted user-facing surfaces.
- [x] (2026-05-22 04:15 UTC) Add/update tests and validate parity.
- [x] (2026-05-22 04:15 UTC) Finalize docs and package closure notes.

## Surprises & Discoveries

- Observation: Feature metadata is split across independent authorities (`MOD_DISPLAY_NAMES`, `MOD_UI_DEFINITIONS`, `header_mod_options`, plus `show_*` booleans).
  Evidence: `wepppy/weppcloud/routes/nodb_api/project_bp.py`, `wepppy/weppcloud/routes/run_0/run_0_bp.py`, `wepppy/weppcloud/templates/header/_run_header_fixed.htm`.
- Observation: Interface launch configs are hardcoded in `interfaces.htm` instead of route-provided registry data.
  Evidence: `wepppy/weppcloud/templates/interfaces.htm`.

## Decision Log

- Decision: Implement registry as a backend-owned subsystem under `wepppy/weppcloud/feature_registry/` and make routes/templates consume derived metadata.
  Rationale: Avoids coupling runtime policy to docs sources and removes duplicated hardcoded maps.
  Date/Author: 2026-05-22 / Codex.

- Decision: Keep v1 schema minimal and remove separate `enable_roles`.
  Rationale: UX requirement is visible implies usable; separate enable gating reintroduces tease-only controls and duplication.
  Date/Author: 2026-05-22 / Codex.

- Decision: Keep `feature_registry` and `config_registry` in the same work-package and subsystem.
  Rationale: Shared maturity semantics and visibility policy should ship together to avoid drift and duplicate plumbing.
  Date/Author: 2026-05-22 / Codex.

## Outcomes & Retrospective

Package implementation completed for the scoped MVP dual-registry targets. Remaining optional follow-on is deeper run-page nav/section label extraction from hardcoded literals.

## Context and Orientation

Current duplication this package replaces:

- `wepppy/weppcloud/routes/nodb_api/project_bp.py`
  - `MOD_DISPLAY_NAMES`, `MOD_DEPENDENCIES`, `MOD_DISABLE_GUARDS`, and toggle policy checks.
- `wepppy/weppcloud/routes/run_0/run_0_bp.py`
  - `MOD_UI_DEFINITIONS`, per-mod visibility booleans (`show_*`), and `mod_visibility`.
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
  - hardcoded `header_mod_options` list.
- `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
  - hardcoded nav/section conditions for feature surfaces.
- `wepppy/weppcloud/templates/interfaces.htm`
  - hardcoded config launch cards/buttons (including `disturbed9002`, `disturbed9002_wbt`, `reveg`).

Contract target:

- `wepppy/weppcloud/feature_registry/specification.md`
- `wepppy/weppcloud/routes/usersum/weppcloud/user-guide.md` (`Feature Maturity Labels`)

Tests likely touched:

- `tests/weppcloud/routes/test_project_bp.py`
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `wepppy/weppcloud/controllers_js/__tests__/project.test.js`

## Plan of Work

Milestone 1 introduces the dual-registry subsystem and shared validation contract:

- `feature_registry.yaml` for features.
- `config_registry.yaml` for interfaces/configs.
- shared schema + runtime helpers.

Milestone 2 migrates feature consumers (`project_bp.py`, `run_0_bp.py`, run/header templates) to registry metadata while preserving behavior.

Milestone 3 migrates interface launch consumers (`weppcloud_site.py`, `interfaces.htm`) to config-registry-driven rendering and maturity labels.

Milestone 4 updates docs/tests, removes remaining duplicated literals on targeted surfaces, and closes with validation evidence.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement registry subsystem files:
   - `wepppy/weppcloud/feature_registry/feature_registry.yaml`
   - `wepppy/weppcloud/feature_registry/config_registry.yaml`
   - `wepppy/weppcloud/feature_registry/schema.py`
   - `wepppy/weppcloud/feature_registry/runtime.py`
   - `wepppy/weppcloud/feature_registry/__init__.py`

2. Add focused registry validation tests for dual registries.

3. Replace `project_bp.py` feature label/dependency lookups with registry queries while preserving API responses.

4. Replace `run_0_bp.py` `MOD_UI_DEFINITIONS` and `mod_visibility` derivation with feature-registry metadata where possible.

5. Update header/run templates to iterate over feature-registry-provided features instead of hardcoded lists for targeted surfaces.

6. Update `weppcloud_site.py` + `interfaces.htm` to render launch options from config registry instead of hardcoded config cards/buttons.

7. Add maturity badge rendering in targeted surfaces (header mods, run navigation/section labels, interfaces launch cards).

8. Run validation gates and record outputs in tracker.

## Validation and Acceptance

Acceptance requires all of the following:

- Dual registries validate and load deterministically.
- Existing mod toggle endpoints continue functioning with feature-registry metadata.
- Header mod menu and run-page feature sections render expected features/order with maturity labels.
- Interface launch surfaces render expected config entries/order with maturity labels.
- Maturity label assignments align with the `Feature Maturity Labels` definitions in user guide.
- No regression in existing route/template behavior outside explicit lifecycle-label improvements.
- Visible entries are usable unless run/project surface is readonly.

Validation commands:

- `wctl run-pytest tests/weppcloud/routes/test_project_bp.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py --maxfail=1` (if usersum docs surfaces are touched)
- `wctl run-npm test` (for touched controller/UI behavior)
- `wctl run-npm lint` (if frontend sources change)
- `wctl doc-lint --path docs/work-packages/20260521_feature_registry --path PROJECT_TRACKER.md --path wepppy/weppcloud/feature_registry/specification.md`

## Idempotence and Recovery

Implementation should be parity-first and additive:

- Introduce registries and dual-read from old constants during migration if needed.
- Remove old constants only after parity tests pass.
- Keep changes sliceable so partial migration can be reverted without losing registry data.

If behavior diverges, temporarily restore prior consumer map in the affected file and re-run targeted tests before continuing migration.

## Artifacts and Notes

- Work package root:
  - `docs/work-packages/20260521_feature_registry/`
- Primary contract source:
  - `wepppy/weppcloud/feature_registry/specification.md`

## Interfaces and Dependencies

Define stable interfaces for consumers:

- registry loader functions for feature entries and config entries
- query function by `id` for each registry
- consumer helpers for:
  - user-facing label
  - maturity metadata
  - role/backend visibility checks
  - feature prerequisites
  - config deprecation replacement hints

Consumer files should rely on these helpers instead of embedding new hardcoded maps.

Non-goals for this ExecPlan:

- do not add separate `enable_roles` or extra taxonomy beyond MVP schema.
