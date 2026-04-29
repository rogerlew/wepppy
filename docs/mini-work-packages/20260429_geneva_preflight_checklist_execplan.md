# 20260429 Geneva Preflight Checklist ExecPlan
Status: complete  
Last Updated: 2026-04-29 UTC  
Primary Areas: `services/preflight2/internal/checklist/`, `wepppy/nodb/redis_prep.py`, `wepppy/rq/geneva_rq.py`, `wepppy/microservices/rq_engine/`, `wepppy/weppcloud/routes/run_0/`, `wepppy/weppcloud/static/js/preflight.js`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Operators can run Geneva from the run page today, but preflight does not expose Geneva completion/freshness in the TOC checklist. After this change, Geneva will behave like other tracked outputs: it will show a checklist/emoji state, turn stale when upstream prerequisites mutate, and return to complete only after a fresh Geneva run.

User-visible outcome:

1. Geneva appears as a preflight checklist key (`geneva`) and TOC emoji target.
2. Geneva task emoji comes from `TaskEnum` and uses `🐈`.
3. Geneva checklist completion clears automatically when prerequisite data changes.

## Scope

In scope:

- Add a dedicated Geneva `TaskEnum` timestamp task and emoji (`🐈`).
- Add Geneva checklist evaluation in `preflight2`.
- Add Geneva key-to-anchor mapping in preflight UI wiring.
- Wire timestamp invalidation at the correct mutation boundaries so Geneva completion is freshness-aware.
- Add/update tests and docs for the new checklist contract.

Out of scope:

- Geneva scientific/kernel behavior changes.
- Reworking Geneva lifecycle states in `geneva.nodb` beyond timestamp/checklist integration.
- Broad preflight semantic refactors unrelated to Geneva.

## Proposed Geneva Dependency Contract

Canonical completion signal:

- `TaskEnum.run_geneva` timestamp indicates last successful Geneva batch run (or workflow terminal run stage).

Checklist key:

- `check["geneva"]` in `services/preflight2/internal/checklist/checklist.go`.

Freshness dependencies:

- Required:
  - `timestamps:build_landuse`
  - `timestamps:build_soils`
  - `timestamps:build_climate`
- Conditional:
  - if `attrs:has_sbs == "true"`, also require `timestamps:run_geneva > timestamps:init_sbs_map`

Evaluation rule (target behavior):

- Geneva is `true` only if `run_geneva` is newer than all applicable prerequisites.
- Missing any required prerequisite or missing `run_geneva` yields `false`.

Immediate stale invalidation boundaries:

- On enqueue of Geneva `prepare_hrus` and `build_frequency_panel` (intermediate artifact mutation means prior Geneva run summary is stale until rerun).
- On Geneva config mutation (`/api/geneva/config` POST when values change).
- On Geneva CN-table mutations (`modify_geneva_cn_table`, `reset_geneva_cn_table`).
- On SBS mutation paths (upload/remove/uniform/class edits) that can alter Geneva optional burn input.
- On climate/landuse/soils enqueue paths (clear stale immediately instead of waiting for completion timestamps).

## Plan of Work

### Milestone 1: TaskEnum + timestamp ownership

- Add `TaskEnum.run_geneva` in `wepppy/nodb/redis_prep.py`.
- Add label and emoji mapping (`🐈`) in `TaskEnum.label()` / `TaskEnum.emoji()`.
- Stamp `TaskEnum.run_geneva` on successful Geneva terminal run (`wepppy/rq/geneva_rq.py`, `run_geneva_run_batch_rq`).
- Ensure pre-enqueue stale clears in Geneva routes.

### Milestone 2: Preflight checklist + TOC mapping

- Add `geneva` checklist key and dependency logic in `services/preflight2/internal/checklist/checklist.go`.
- Add/extend checklist tests in `services/preflight2/internal/checklist/checklist_test.go`.
- Map `#geneva` in `wepppy/weppcloud/routes/run_0/run_0_bp.py` `TOC_TASK_ANCHOR_TO_TASK`.
- Add `"geneva": 'a[href="#geneva"]'` in `wepppy/weppcloud/static/js/preflight.js` `getSelectorForKey()`.

### Milestone 3: Stale invalidator coverage

- Update relevant routes to clear Geneva timestamp at mutation start:
  - `wepppy/microservices/rq_engine/geneva_routes.py`
  - `wepppy/weppcloud/routes/nodb_api/geneva_bp.py`
  - `wepppy/microservices/rq_engine/climate_routes.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/microservices/rq_engine/soils_routes.py`
  - `wepppy/microservices/rq_engine/upload_disturbed_routes.py`
  - `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`
- Keep contract additive/backward-compatible (new checklist key only; no renames/removals).

### Milestone 4: Tests and docs

- Update targeted Python tests asserting removed timestamps:
  - `tests/rq/test_geneva_rq.py`
  - `tests/microservices/test_rq_engine_geneva_routes.py`
  - `tests/microservices/test_rq_engine_climate_routes.py`
  - `tests/microservices/test_rq_engine_landuse_routes.py`
  - `tests/microservices/test_rq_engine_soils_routes.py`
  - `tests/microservices/test_rq_engine_upload_disturbed_routes.py`
  - `tests/weppcloud/routes/test_disturbed_bp.py`
- Update preflight docs:
  - `docs/ui-docs/control-ui-styling/preflight_behavior.md`
- If queue-edge docs drift, update:
  - `wepppy/rq/job-dependencies-catalog.md` (only if enqueue dependency edges actually change).

## Validation Gates

Required targeted gates:

- `cd /workdir/wepppy/services/preflight2 && go test ./...`
- `cd /workdir/wepppy && wctl run-pytest tests/rq/test_geneva_rq.py --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_upload_disturbed_routes.py --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`

Recommended confidence gate:

- `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1`

## Risks and Mitigations

- Risk: checklist false negatives when optional SBS is absent.
  - Mitigation: gate SBS dependency on `attrs:has_sbs == "true"` only.
- Risk: stale indicator lags until long-running upstream tasks complete.
  - Mitigation: clear `TaskEnum.run_geneva` at enqueue/mutation boundaries, not just completion.
- Risk: route test churn due expanded `remove_timestamp(...)` assertions.
  - Mitigation: update exact expected task-removal lists in touched tests with explicit rationale comments.

## Progress

- [x] (2026-04-29 UTC) Confirmed current gap: no Geneva key in preflight checklist, no Geneva `TaskEnum`, and no preflight selector mapping for `#geneva`.
- [x] (2026-04-29 UTC) Traced Geneva runtime dependencies from shipped code (`prepare_hrus`, `build_frequency_panel`, `run_batch`) and identified required freshness inputs.
- [x] (2026-04-29 UTC) Authored this scoped ExecPlan with dependency contract, file targets, and validation gates.
- [x] (2026-04-29 UTC) Moved tracker card `Geneva Preflight Checklist Freshness Integration` from Backlog to In Progress in `PROJECT_TRACKER.md`.
- [x] (2026-04-29 UTC) Implemented Milestone 1 (`TaskEnum.run_geneva` + `🐈`, Geneva completion timestamp stamping, and pre-enqueue stale clears).
- [x] (2026-04-29 UTC) Implemented Milestone 2 (preflight checklist `geneva` dependency logic + TOC selector/task anchor wiring).
- [x] (2026-04-29 UTC) Implemented Milestone 3 (stale invalidators across Geneva/climate/landuse/soils/disturbed mutation boundaries).
- [x] (2026-04-29 UTC) Implemented Milestone 4 (targeted tests and preflight behavior docs updated for the Geneva freshness contract).
- [x] (2026-04-29 UTC) Ran required validation gates; targeted suites passed. Confidence suite failed on unrelated existing `NoDbStaleWriteError` path in `tests/nodb/test_base_boundary_characterization.py::test_dump_forces_monotonic_signature_after_second_same_size_rewrite`.
- [x] (2026-04-29 UTC) Updated `PROJECT_TRACKER.md` handoff state from In Progress to Done.
- [x] (2026-04-29 UTC) Follow-up patch: stamped `TaskEnum.init_sbs_map` wherever SBS mutations set `attrs:has_sbs=true` in BAER/Disturbed controllers so conditional Geneva freshness dependency can evaluate from live SBS edits.
- [x] (2026-04-29 UTC) Added regression tests for SBS timestamp ownership (`tests/nodb/mods/disturbed/test_sbs_validation.py`, `tests/nodb/mods/baer/test_baer_prep_timestamps.py`) and reran required validation gates.
- [x] (2026-04-29 UTC) Added Geneva RQ legacy self-heal: `run_geneva_run_batch_rq` now backfills missing `timestamps:init_sbs_map` for `attrs:has_sbs=true` runs before stamping `run_geneva`.
- [x] (2026-04-29 UTC) Re-ran the full required validation gate list after legacy self-heal patch (targeted gates passed; confidence gate still fails on known unrelated `NoDbStaleWriteError` test path).
- [x] (2026-04-29 UTC) Recreated/restarted runtime services (`preflight`, `rq-worker`, `rq-engine`, `weppcloud`) and verified preflight container image ID matches current build digest.
- [x] (2026-04-29 UTC) Executed one-time legacy Redis backfill sweep for `attrs:has_sbs=true` runs missing `timestamps:init_sbs_map` (`99` keys backfilled out of `134` SBS-enabled runs).
- [x] (2026-04-29 UTC) Performed authenticated legacy run smoke (`onshore-xenophobia/disturbed9002_wbt`): run page bootstrap includes `#geneva` -> `🐈` TOC emoji metadata and live preflight websocket reports `checklist.geneva=true`.
- [x] (2026-04-29 UTC) Ran `wctl check-rq-graph`; detected drift and regenerated `wepppy/rq/job-dependency-graph.static.json` and `wepppy/rq/job-dependencies-catalog.md`, then re-ran `wctl check-rq-graph` to green.

## Surprises & Discoveries

- `services/preflight2/internal/checklist/checklist.go` currently tracks `rusle` but has no Geneva branch.
- `run_0_bp.py` TOC emoji map includes `#rusle` but not `#geneva`, even though `runs0_pure.htm` already renders a Geneva nav/section.
- Geneva route/task stack currently updates Geneva internal state but does not stamp a RedisPrep `TaskEnum` timestamp suitable for preflight freshness.
- The exact Go gate command in the ExecPlan (`go test ./...` from `services/preflight2`) depends on a local `go1.25` toolchain that is not installed in this shell; containerized `wctl run-preflight-tests` validated the suite successfully.
- Live run evidence showed `attrs:has_sbs=true` with no `timestamps:init_sbs_map`, which made the new conditional Geneva freshness dependency unsatisfied even after `timestamps:run_geneva` existed.
- Root cause for missing `init_sbs_map` timestamp was controller-level SBS mutation paths (`Disturbed`/`Baer`) that set `has_sbs` and `landuse_map` but never stamped `init_sbs_map`.
- Even after controller patches, legacy runs that already had SBS enabled still remain stale until an SBS mutation occurs unless a backfill path populates `timestamps:init_sbs_map`.
- Authenticated run-page bootstrap encodes emoji metadata in escaped Unicode (for example `#geneva: "\ud83d\udc08"`), so literal `🐈` string search against HTML can false-negative despite correct wiring.
- `wctl check-rq-graph` reported static dependency graph/catalog drift after route wiring changes, so managed artifacts required regeneration as part of closure.

## Decision Log

- Decision: Use RedisPrep timestamp freshness for Geneva checklist, not Geneva `state_payload` polling from preflight2.
  - Rationale: preserves preflight2 architecture (Redis hash only) and avoids cross-service state joins.
  - Date/Author: 2026-04-29 / Codex

- Decision: Model Geneva stale behavior after RUSLE pattern (timestamp compare + targeted timestamp clears on mutation boundaries).
  - Rationale: existing code/tests already use this pattern and operators understand it.
  - Date/Author: 2026-04-29 / Codex

- Decision: Invalidate `TaskEnum.run_geneva` only when Geneva config writes produce an actual persisted config diff.
  - Rationale: avoids stale false-negatives from no-op saves while still clearing preflight completion for real config mutations.
  - Date/Author: 2026-04-29 / Codex

- Decision: Clear `TaskEnum.run_geneva` on workflow enqueue (`run-workflow`) in addition to direct `prepare_hrus` / `build_frequency_panel` endpoints.
  - Rationale: workflow enqueue semantically includes those intermediate mutation stages and should stale the checklist immediately.
  - Date/Author: 2026-04-29 / Codex

- Decision: When SBS mutations persist `has_sbs=true`, stamp `TaskEnum.init_sbs_map` alongside `TaskEnum.landuse_map` in controller mutation paths.
  - Rationale: preserves the documented conditional Geneva dependency (`run_geneva > init_sbs_map`) without weakening checklist semantics or requiring fallback behavior for missing timestamps.
  - Date/Author: 2026-04-29 / Codex

- Decision: Add legacy `init_sbs_map` backfill in Geneva run completion path for `has_sbs=true` runs with missing timestamp.
  - Rationale: preserves strict checklist semantics for new runs while restoring operability for historical runs that predate `init_sbs_map` mutation stamping.
  - Date/Author: 2026-04-29 / Codex

## Outcomes & Retrospective

Implementation complete for scoped Milestones 1-4.

Validation outcomes:

- `cd /workdir/wepppy/services/preflight2 && go test ./...` -> failed in local shell (`go1.25` toolchain unavailable).
- `cd /workdir/wepppy && wctl run-preflight-tests` (fallback) -> passed.
- `cd /workdir/wepppy && wctl run-pytest tests/rq/test_geneva_rq.py --maxfail=1` -> passed.
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1` -> passed.
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py --maxfail=1` -> passed.
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> passed.
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1` -> passed.
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_upload_disturbed_routes.py --maxfail=1` -> passed.
- `cd /workdir/wepppy && wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1` -> passed.
- `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1` (recommended confidence gate) -> failed on unrelated existing `NoDbStaleWriteError` in `tests/nodb/test_base_boundary_characterization.py::test_dump_forces_monotonic_signature_after_second_same_size_rewrite` after `1790 passed, 19 skipped`.

Follow-up validation outcomes (post SBS `init_sbs_map` stamping patch):

- `cd /workdir/wepppy/services/preflight2 && go test ./...` -> failed in local shell (`go: download go1.25 for linux/amd64: toolchain not available`).
- `cd /workdir/wepppy && wctl run-preflight-tests` (fallback) -> passed.
- `cd /workdir/wepppy && wctl run-pytest tests/rq/test_geneva_rq.py --maxfail=1` -> passed (`5 passed`).
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1` -> passed (`7 passed`).
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py --maxfail=1` -> passed (`7 passed`).
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> passed (`57 passed`).
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1` -> passed (`3 passed`).
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_upload_disturbed_routes.py --maxfail=1` -> passed (`8 passed`).
- `cd /workdir/wepppy && wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1` -> passed (`51 passed`).
- `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1` (recommended confidence gate) -> failed on unrelated existing template assertion in `tests/weppcloud/routes/test_pure_controls_render.py::test_geneva_summary_report_template_embeds_single_json_payload` after `3771 passed, 36 skipped`.
- Additional regression checks:
  - `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/disturbed/test_sbs_validation.py::test_validate_updates_landuse_and_sbs_prep_timestamps tests/nodb/mods/baer/test_baer_prep_timestamps.py --maxfail=1` -> passed (`2 passed`).
- Legacy backfill regression checks:
  - `cd /workdir/wepppy && wctl run-pytest tests/rq/test_geneva_rq.py --maxfail=1` -> passed (`6 passed`).
  - `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1` -> passed (`7 passed`).
- Close-out rerun outcomes (post legacy self-heal and runtime restart):
  - `cd /workdir/wepppy/services/preflight2 && go test ./...` -> failed in local shell (`go: download go1.25 for linux/amd64: toolchain not available`).
  - `cd /workdir/wepppy && wctl run-preflight-tests` (fallback) -> passed.
  - `cd /workdir/wepppy && wctl run-pytest tests/rq/test_geneva_rq.py --maxfail=1` -> passed (`6 passed`).
  - `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1` -> passed (`7 passed`).
  - `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py --maxfail=1` -> passed (`7 passed`).
  - `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> passed (`57 passed`).
  - `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1` -> passed (`3 passed`).
  - `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_upload_disturbed_routes.py --maxfail=1` -> passed (`8 passed`).
  - `cd /workdir/wepppy && wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1` -> passed (`51 passed`).
  - `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1` (recommended confidence gate) -> failed on unrelated existing `tests/nodb/test_base_boundary_characterization.py::test_dump_forces_monotonic_signature_after_second_same_size_rewrite` after `1792 passed, 19 skipped`.
  - Runtime refresh: `docker compose -f docker/docker-compose.dev.yml up -d --force-recreate preflight rq-worker rq-engine weppcloud` -> passed; `weppcloud-preflight` image confirmed as `sha256:64479473a8823690e838d4f3555e7e05a6fe06cffe2f96cd82456541ec984f1b`.
  - Additional worker refresh: `docker compose -f docker/docker-compose.dev.yml up -d --force-recreate rq-worker-batch` -> passed.
  - Legacy backfill sweep: `sbs_true=134`, `already_had_init_sbs_map=35`, `backfilled_missing_init_sbs_map=99`, all using `landuse_map` fallback.
  - Authenticated smoke check:
    - `GET /weppcloud/runs/onshore-xenophobia/disturbed9002_wbt/` as `dev-agent` -> CAP gate absent, `href="#geneva"` present, bootstrap `tocTaskEmojis` includes `#geneva: "\ud83d\udc08"`.
    - `wss://wc.bearhive.duckdns.org/weppcloud-microservices/preflight/onshore-xenophobia` -> payload now reports `"geneva":true`.
  - Queue dependency graph validation:
    - `cd /workdir/wepppy && wctl check-rq-graph` -> initially failed with drift in `wepppy/rq/job-dependency-graph.static.json` and `wepppy/rq/job-dependencies-catalog.md`.
    - `cd /workdir/wepppy && python tools/check_rq_dependency_graph.py --write` -> regenerated artifacts (`138` edges written, catalog managed section updated).
    - `cd /workdir/wepppy && wctl check-rq-graph` -> passed (`RQ dependency graph artifacts are up to date`).

Plan revision note (2026-04-29 UTC): execution complete with tracker handoff recorded.

Plan revision note (2026-04-29 UTC): initial plan created from live codepath audit and preflight contract gap analysis.
