# ExecPlan: Implement RAP-Independent Surface-Rock Partition for `scenario_sbs`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, `scenario_sbs` users can represent protective surface rock directly in RUSLE `C` using `rock_fraction_of_sbs_bare` without any RAP dependency. This prevents SBS lookup bare fractions from being interpreted as fully exposed erodible soil on armored hillslopes.

Users can verify behavior by running `scenario_sbs` builds with `rock_fraction_of_sbs_bare = 0.0`, `auto`, and a high field-informed value, then confirming directional changes in `c_scenario_sbs.tif` and `a_scenario_sbs_*` plus provenance entries in `rusle/manifest.json`.

## Progress

- [x] (2026-05-27 23:09 UTC) Scoped package and created work-package scaffold.
- [x] (2026-05-27 23:09 UTC) Updated RUSLE specification with SBS rock-partition contract and user-control requirements.
- [ ] Implement runtime/controller/UI/API changes for `rock_fraction_of_sbs_bare`.
- [ ] Add targeted Python + JS regressions for SBS rock control and mode-specific payload behavior.
- [ ] Run focused validation suites and capture outcomes in tracker artifacts.
- [ ] Dispatch independent review and disposition all high/medium findings.

## Surprises & Discoveries

- Observation: Existing work package `20260527_rusle_c_surface_rock_partition` intentionally scoped rock partition to `observed_rap` and leaves `scenario_sbs` unchanged.
  Evidence: `docs/work-packages/20260527_rusle_c_surface_rock_partition/package.md` out-of-scope section.
- Observation: `scenario_sbs` currently relies on static lookup-derived `C` behavior with no explicit rock-partition control.
  Evidence: `wepppy/nodb/mods/rusle/specification.md` prior `scenario_sbs` contract sections.

## Decision Log

- Decision: Implement a distinct `scenario_sbs` control (`rock_fraction_of_sbs_bare`) instead of reusing RAP controls.
  Rationale: Keeps SBS usable without RAP retrieval/year state and matches user direction.
  Date/Author: 2026-05-27 23:09 UTC / Codex.
- Decision: Reuse `cosurffrags -> cfvo -> 0.0` proxy precedence for `auto`, but normalize into SBS lookup-bare control space.
  Rationale: Preserves existing proxy hierarchy while respecting SBS control semantics.
  Date/Author: 2026-05-27 23:09 UTC / Codex.

## Outcomes & Retrospective

Implementation not started in this ExecPlan yet. Scoping and specification updates are complete.

## Context and Orientation

Implementation touches the same four surfaces as other RUSLE control changes:

1. UI form markup: `wepppy/weppcloud/templates/controls/rusle_pure.htm`.
2. Browser controller payload builder: `wepppy/weppcloud/controllers_js/rusle.js`.
3. rq-engine build/API contract:
   - `wepppy/microservices/rq_engine/rusle_routes.py`
   - `wepppy/microservices/rq_engine/schema_defaults_routes.py`
4. RUSLE runtime:
   - `wepppy/nodb/mods/rusle/rusle.py`
   - `wepppy/nodb/mods/rusle/c_integration.py`

Primary tests:

- `tests/nodb/mods/test_rusle_c_integration.py`
- `tests/nodb/mods/test_rusle_controller.py`
- `tests/microservices/test_rq_engine_rusle_routes.py`
- `tests/microservices/test_rq_engine_schema_defaults_routes.py`
- `wepppy/weppcloud/controllers_js/__tests__/rusle.test.js`

## Plan of Work

First, add `rock_fraction_of_sbs_bare` to controller parsing/state and C integration runtime with strict input validation (`auto` or numeric `[0,1]`).

Second, implement SBS-mode C partitioning from lookup bare:

- derive `bare_lookup = 1 - fg_lookup`
- compute `bare_exposed = bare_lookup * (1 - r_sbs_bare)`
- compute `fg_effective_pct = 100 * (1 - bare_exposed)`
- compute `C = exp(-0.04 * fg_effective_pct)`

Third, wire UI/rq-engine payload and defaults metadata, including mode-specific control visibility and guidance text.

Fourth, implement `auto` default resolution with `cosurffrags` primary and `cfvo` fallback, normalized by `bare_lookup_mean_0_1` for SBS control-space conversion.

Finally, add focused regressions, run validation gates, and perform independent review + disposition.

## Concrete Steps

Work from `/home/workdir/wepppy`.

1. Update runtime/controller:
   - `wepppy/nodb/mods/rusle/rusle.py`
   - `wepppy/nodb/mods/rusle/c_integration.py`
2. Update UI/API contract surfaces:
   - `wepppy/weppcloud/templates/controls/rusle_pure.htm`
   - `wepppy/weppcloud/controllers_js/rusle.js`
   - `wepppy/microservices/rq_engine/rusle_routes.py`
   - `wepppy/microservices/rq_engine/schema_defaults_routes.py`
3. Update targeted tests listed above.
4. Run targeted validation commands and record outputs in tracker notes.

## Validation and Acceptance

Acceptance behavior:

- `scenario_sbs` accepts `rock_fraction_of_sbs_bare` (`auto` or numeric `[0,1]`).
- `scenario_sbs` C computation follows lookup-bare partition math before exponential mapping.
- `scenario_sbs` rock control remains RAP-independent.
- `auto` source precedence and fallback contract (`cosurffrags -> cfvo -> 0.0`) is honored and provenance is recorded.
- UI guidance explicitly tells users to verify field/local rock cover and set fraction accordingly.
- Targeted tests pass.

Planned validation commands:

- `wctl run-pytest tests/nodb/mods/test_rusle_c_integration.py tests/nodb/mods/test_rusle_controller.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_rusle_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- `wctl run-npm test -- controllers_js/__tests__/rusle.test.js`
- `wctl doc-lint --path wepppy/nodb/mods/rusle/specification.md --path docs/work-packages/20260527_rusle_sbs_surface_rock_partition --path PROJECT_TRACKER.md`

## Idempotence and Recovery

This rollout is additive. If regressions are found, rollback by disabling only SBS rock-partition option handling while preserving existing SBS lookup and observed RAP behavior.

## Artifacts and Notes

- Package root: `docs/work-packages/20260527_rusle_sbs_surface_rock_partition/`
- Review/disposition artifact targets:
  - `docs/work-packages/20260527_rusle_sbs_surface_rock_partition/artifacts/20260527_independent_review.md`
  - `docs/work-packages/20260527_rusle_sbs_surface_rock_partition/artifacts/20260527_findings_disposition.md`

## Interfaces and Dependencies

No new external dependencies are required. The package extends existing RUSLE control contracts and reuses established SSURGO proxy sourcing conventions. Parameterization governance is recorded in `docs/adrs/ADR-0004-rusle-scenario-sbs-surface-rock-partition.md`.
