# ExecPlan: Implement RUSLE `observed_rap` Surface-Rock Partition Control

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, RUSLE users can set a new control (`rock_fraction_of_rap_bare`) to partition RAP bare ground into exposed mineral soil and protective surface rock for `observed_rap` C-factor builds. This prevents highly armored stony surfaces from being interpreted as fully exposed bare soil. The UI will explicitly tell users to verify rock cover and set this fraction accordingly, while `auto` provides a conservative proxy default from SSURGO `cosurffrags` with top-horizon `cfvo` fallback.

Users can verify behavior by building RUSLE with different rock-fraction values (`0.0`, `auto`, high value), then checking `rusle/manifest.json` for effective value/source and confirming `c_observed_rap`/`a_observed_rap_*` outputs shift directionally as expected.

## Progress

- [x] (2026-05-27 21:42 UTC) Created work-package scaffold (`package.md`, `tracker.md`, and this active ExecPlan).
- [x] (2026-05-27 21:42 UTC) Mapped concrete implementation surfaces across UI, JS controller, rq-engine route/schema, and RUSLE C integration.
- [x] (2026-05-27 21:51 UTC) Completed independent review + findings disposition for package/plan quality; acceptance and validation criteria tightened.
- [x] (2026-05-27 22:20 UTC) Revised `auto` source precedence to `cosurffrags` first with `cfvo` fallback and RAP-bare normalization.
- [ ] Implement UI control + guidance copy for `rock_fraction_of_rap_bare` with `auto` support.
- [ ] Implement payload parsing/allowlist/schema-default updates through rq-engine.
- [ ] Implement `observed_rap` C partition runtime logic and manifest provenance fields.
- [ ] Add/adjust targeted Python and JS regression tests.
- [ ] Run focused validation gates.
- [ ] Run independent review and disposition all high/medium findings.

## Surprises & Discoveries

- Observation: RUSLE control template currently supports `c_mode`, `rap_year`, `k_modes`, and other scalar inputs but does not include any surface-rock partition control.
  Evidence: `wepppy/weppcloud/templates/controls/rusle_pure.htm` current field set.
- Observation: `build-rusle` rq-engine route filters payload through an explicit allowlist, so the new field must be added there even if controller JS sends it.
  Evidence: `wepppy/microservices/rq_engine/rusle_routes.py` `allowed_keys` tuple.

## Decision Log

- Decision: Implement `rock_fraction_of_rap_bare` as an `observed_rap`-scoped control with explicit `auto` option rather than globally applying it to all C modes.
  Rationale: Aligns with specification contract and limits unscoped behavior drift in `scenario_sbs`.
  Date/Author: 2026-05-27 21:42 UTC / Codex.
- Decision: Treat `auto` as a convenience proxy seeded first from SSURGO `cosurffrags`, with top-horizon `cfvo` fallback and mandatory user-facing verification guidance.
  Rationale: Prefers a surface-fragment proxy for `C` while preserving an operational fallback when `cosurffrags` is unavailable.
  Date/Author: 2026-05-27 22:20 UTC / Codex.

## Outcomes & Retrospective

Package initialization is complete. Implementation and validation remain pending.

## Context and Orientation

Feature touchpoints are distributed across four layers:

1. RUSLE run-page UI form: `wepppy/weppcloud/templates/controls/rusle_pure.htm`.
2. Browser controller payload assembly: `wepppy/weppcloud/controllers_js/rusle.js`.
3. rq-engine API envelope and discoverability contract:
   - `wepppy/microservices/rq_engine/rusle_routes.py`
   - `wepppy/microservices/rq_engine/schema_defaults_routes.py`
4. NoDb RUSLE runtime and C-factor artifact production:
   - `wepppy/nodb/mods/rusle/rusle.py`
   - `wepppy/nodb/mods/rusle/c_integration.py`

Primary regression surfaces:

- JS: `wepppy/weppcloud/controllers_js/__tests__/rusle.test.js`
- rq-engine route/schema: `tests/microservices/test_rq_engine_rusle_routes.py` and relevant schema-default tests
- C integration/controller: `tests/nodb/mods/test_rusle_c_integration.py`, `tests/nodb/mods/test_rusle_controller.py`

## Plan of Work

First, add UI controls for the new parameter and explicit guidance text that users should verify local/field rock cover and set the value accordingly. Keep the field visible/relevant only for `observed_rap` workflows.

Second, update `rusle.js` payload generation so `rock_fraction_of_rap_bare` is serialized consistently, with `auto` behavior preserved and mode-appropriate omission/retention rules documented in tests.

Third, propagate the field through rq-engine by extending the `build-rusle` allowlist and schema-default request metadata.

Fourth, implement runtime behavior in RUSLE C integration and controller plumbing, including:

- observed RAP bare partition formula from specification,
- `auto` default resolution from run-scoped SSURGO `cosurffrags` when available,
- `cfvo` fallback behavior when `cosurffrags` is unavailable,
- fallback behavior when neither proxy is available,
- explicit manifest provenance fields (`effective value`, `source`).

Finally, add targeted regressions and run validation gates, then perform a post-implementation independent review and disposition findings.

## Concrete Steps

Work from `/home/workdir/wepppy`.

1. Edit UI template and JS controller:
   - `wepppy/weppcloud/templates/controls/rusle_pure.htm`
   - `wepppy/weppcloud/controllers_js/rusle.js`
   - `wepppy/weppcloud/controllers_js/__tests__/rusle.test.js`
2. Edit rq-engine route/schema contracts:
   - `wepppy/microservices/rq_engine/rusle_routes.py`
   - `wepppy/microservices/rq_engine/schema_defaults_routes.py`
   - route/schema tests in `tests/microservices/`
3. Edit RUSLE runtime integration:
   - `wepppy/nodb/mods/rusle/rusle.py`
   - `wepppy/nodb/mods/rusle/c_integration.py`
   - targeted tests in `tests/nodb/mods/`
4. Run focused validation and doc lint.
5. Dispatch independent review and write findings disposition artifact.

## Validation and Acceptance

Acceptance behavior:

- UI shows `rock_fraction_of_rap_bare` and explicit guidance that users should verify rock cover and set fraction accordingly.
- `observed_rap` build payload includes the field; non-observed modes do not mis-handle RAP-only inputs.
- rq-engine `build-rusle` accepts and forwards the field in filtered payload.
- rq-engine schema-default metadata includes the new field and default contract.
- Runtime C computation uses partitioned bare-ground contract from specification.
- `rusle/manifest.json` includes effective partition value and source (`user`/`auto`), and for `auto` records whether source was `cosurffrags`, `cfvo`, or `fallback_0`.
- Input contract accepts only numeric `[0,1]` or literal `auto`; invalid values (`<0`, `>1`, non-numeric non-`auto`) follow canonical RQ error payload behavior.
- Targeted Python + JS tests pass.

Acceptance test matrix to implement:

- `rock_fraction_of_rap_bare = 0.0` (user): uses exact user value; manifest source=`user`.
- `rock_fraction_of_rap_bare = 1.0` (user): uses exact user value; manifest source=`user`.
- `rock_fraction_of_rap_bare = auto` with `cosurffrags`: derives total-surface proxy from `sfragcov`, normalizes by RAP bare context, and records manifest source=`auto:cosurffrags`.
- `rock_fraction_of_rap_bare = auto` with missing `cosurffrags` but available `cfvo`: uses `cfvo` proxy with the same RAP-bare normalization, source=`auto:cfvo`.
- `rock_fraction_of_rap_bare = auto` without `cosurffrags` and `cfvo`: uses fallback `0.0`; source=`auto:fallback_0`; manifest includes fallback reason.
- Invalid values (`<0`, `>1`, non-numeric non-`auto`): rejected using canonical RQ response contract.

Planned validation commands:

- `wctl run-pytest tests/nodb/mods/test_rusle_c_integration.py tests/nodb/mods/test_rusle_controller.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_rusle_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- `wctl run-npm test -- controllers_js/__tests__/rusle.test.js`
- `wctl doc-lint --path docs/work-packages/20260527_rusle_c_surface_rock_partition --path PROJECT_TRACKER.md --path wepppy/nodb/mods/rusle/specification.md`

## Idempotence and Recovery

The rollout is additive and should remain backward-compatible for clients that do not send the new field. If proxy resolution is unavailable, behavior must degrade deterministically to explicit fallback semantics documented in manifest metadata. If regressions are found, disable only the new field handling path while preserving pre-existing `observed_rap` behavior.

## Artifacts and Notes

- Package root: `docs/work-packages/20260527_rusle_c_surface_rock_partition/`
- Findings disposition artifact target:
  `docs/work-packages/20260527_rusle_c_surface_rock_partition/artifacts/20260527_findings_disposition.md`

## Interfaces and Dependencies

No new external libraries are required. The package extends existing RUSLE control and API payload contracts with one new field and associated manifest metadata. Parameterization governance is anchored to `docs/adrs/ADR-0003-rusle-observed-rap-surface-rock-partition.md`.
