# Roads WEPP Report Parity and Run Results Summary

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, a completed Roads run will produce Roads-scoped report resources that match the canonical WEPP report expectations, without overwriting baseline WEPP outputs. Users will be able to open a Roads Run Results summary and access Roads-augmented report links and files rooted at `wepp/roads/output`.

All implementation examples and validation commands default to this fixture unless explicitly justified:

- run id: `clogging-starch`
- wd: `/wc1/runs/cl/clogging-starch`
- config: `disturbed9002-wbt-mofe.cfg`
- roads input: `/wc1/runs/cl/clogging-starch/roads/UM1_roads_info.geojson`
- DEM: `/wc1/runs/cl/clogging-starch/dem/wbt/relief.tif`

## Progress

- [x] (2026-03-23 20:20Z) Authored package scaffold and activated this ExecPlan.
- [x] (2026-03-23 20:22Z) Mapped current Roads runtime/report gaps: Roads rerun completes, but no Roads-scoped interchange/totalwatsed/water-balance regeneration or Run Results links exist.
- [x] (2026-03-23 20:30Z) Installed active ExecPlan pointer in `AGENTS.md`, registered package in `PROJECT_TRACKER.md`, and validated package docs with `wctl doc-lint` + `tools/check_agents_size.sh AGENTS.md`.
- [x] (2026-03-23 21:15Z) Adopted minimal-regression rollover sequencing and dedicated per-rollover regression subagent review gates.
- [x] (2026-03-24 03:55Z) Completed the active e2e execution prompt with mandatory startup reads, explicit rollout/review gating, and synchronized validation/handoff requirements.
- [x] (2026-03-24 04:14Z) Milestone 1 completed: added strict `output_scope` contract (`baseline|roads`), scoped path resolver helpers, package exports/stubs, and baseline-default regression coverage (`tests/wepp/reports/test_output_scope.py`).
- [x] (2026-03-24 04:14Z) Milestone 2 completed: rolled over `return_periods` route/service/dataset/template flow to scoped outputs; dedicated regression review artifact recorded in `artifacts/return_periods_regression_review.md`; medium/high findings resolved.
- [x] (2026-03-24 04:31Z) Milestone 3 completed: rolled over streamflow + water-balance reports/routes/templates to scoped datasets with strict invalid-scope handling; dedicated regression review artifact recorded in `artifacts/streamflow_watbal_regression_review.md`; medium/high findings resolved.
- [x] (2026-03-24 04:49Z) Milestone 4 completed: rolled over gl-dashboard query payload paths to backend-owned scope maps with strict scope validation in run route; dedicated regression review artifact recorded in `artifacts/gl_dashboard_regression_review.md`; medium/high findings resolved.
- [x] (2026-03-24 04:34Z) Milestone 5 completed: rolled over storm-event-analyzer route/template/query payloads to backend-owned scoped paths with strict invalid-scope handling; dedicated regression review artifact recorded in `artifacts/storm_event_analyzer_regression_review.md`; medium/high findings resolved.
- [x] (2026-03-24 05:02Z) Milestone 6 completed: implemented Roads post-run report-resource regeneration helper in `run_roads_wepp()` and delivered Roads Run Results summary route/template/control links with roads-scoped canonical report links.
- [x] (2026-03-24 05:02Z) Milestone 7 completed: expanded regression coverage for Roads summary/render/resource regeneration and executed fixture-backed `clogging-starch` e2e verification (`run_status=completed`, required resources present).
- [x] (2026-03-24 05:02Z) Milestone 8 completed: cross-cutting code review artifact recorded in `artifacts/code_review_findings.md`; medium/high findings resolved.
- [x] (2026-03-24 05:02Z) Milestone 9 completed: cross-cutting QA review artifact recorded in `artifacts/qa_review_findings.md`; medium/high findings resolved.
- [x] (2026-03-24 05:02Z) Milestone 10 completed: governance/doc sync finished and full validation gates passed.
- [x] (2026-03-24 06:18Z) Follow-up adjustment completed: Roads segment loss export is parquet-only (`wepp/roads/output/interchange/roads_segment_loss_summary.parquet`), with run-results links using browse/download service conversion (`?as_csv=1`) instead of writing any CSV artifact to disk.
- [x] (2026-03-24 07:40Z) Follow-up subagent review remediation completed: fixed roads-scope loss-summary routing (`report_wepp_loss` + loss-report adapters/template scope links), corrected segment-loss summary join precedence to target hillslope IDs, split gl-dashboard channel summary vs yearly-channel paths, and expanded regression coverage for full `wepp_paths` contracts + roads-scope route acceptance/failure cases.
- [x] (2026-03-24 08:26Z) Final subagent review remediation completed: fixed `HillslopeWatbalReport` baseline re-raise contract, gated Roads Run Results links by required resources (single-storm-safe), added missing roads-scope route forwarding coverage (`yearly_watbal`, `streamflow`, `return_periods`), expanded Roads segment-summary branch coverage, and strengthened JS QA coverage (`roads.test.js`, `wepp-data.test.js`).
- [x] (2026-03-24 08:44Z) Final validation gates rerun after final remediation: `wctl run-npm lint`, `wctl run-npm test`, `wctl run-preflight-tests ./internal/checklist`, broad-exception enforcement, full `wctl run-pytest tests --maxfail=1` (`2540 passed, 34 skipped`), and package doc-lint suite all passed.

## Surprises & Discoveries

- Observation: `Roads.run_roads_wepp()` currently ends after watershed rerun and does not regenerate interchange resources for Roads output scope.
  Evidence: `wepppy/nodb/mods/roads/roads.py` runtime flow around `watershed_rerun_completed` and `last_run_summary`.

- Observation: Canonical WEPP report adapters are hardcoded to `wepp/output/interchange/*`, so Roads outputs at `wepp/roads/output/*` are not consumable without scope plumbing.
  Evidence: hardcoded constants in `wepppy/wepp/reports/loss_outlet_report.py`, `loss_hill_report.py`, `loss_channel_report.py`, `total_watbal.py`, `return_periods.py`, `average_annuals_by_landuse.py`, `sediment_characteristics.py`, `frq_flood.py`, `hillslope_watbal.py`, and `channel_watbal.py`.

- Observation: Roads report template currently renders raw JSON and has no canonical Run Results links.
  Evidence: `wepppy/weppcloud/templates/reports/roads/summary.htm`.

- Observation: Return-period calculations/staging rely on cache/staging assumptions that are not currently scope-aware.
  Evidence: regression-risk assessment notes from dedicated review agents; cache/staging paths are baseline-centric and can contaminate Roads reads/writes unless keyed by `output_scope`.

- Observation: GL dashboard and storm event analyzer integrations have transitive path coupling to baseline interchange datasets.
  Evidence: regression-risk assessment notes from dedicated review agents; path assumptions extend beyond single route handlers and include payload assembly/query helper layers.

- Observation: `ReturnPeriodDataset` scope validation initially occurred after run-context resolution, which could raise `FileNotFoundError` before contract-level scope errors.
  Evidence: failing regression test `test_return_period_dataset_rejects_invalid_output_scope` prior to fix; corrected by validating `output_scope` before resolving context.

- Observation: Some Roads fixture runs do not emit optional watershed/hillslope text sources (`soil_pw0.txt`, `chan.out`, `chnwb.txt`) needed by optional interchange conversions.
  Evidence: `clogging-starch` e2e failures during Milestone 7 when optional conversions were forced; fixed by explicit source-availability gating and required-resource verification focused on mandatory Roads outputs.

- Observation: Persisting dedicated CSV files for Roads segment summaries is unnecessary and duplicates browse/download conversion capability.
  Evidence: browse microservice `download_with_subpath` already supports parquet-to-CSV conversion with `?as_csv=1`.

- Observation: In real fixture data (`/wc1/runs/cl/clogging-starch`), Roads `loss_pw0.hill.parquet` keys map to `target_hillslope_wepp_id`, while `H.wat.parquet` keys map to segment run IDs (`900001+`).
  Evidence: direct DuckDB inspection of fixture manifest + roads interchange outputs (`target join hits=24`, `segment join hits=0` for `loss_pw0.hill.parquet`).

- Observation: Combined pytest invocation across selected suites can fail due transient `pyproj` stub contamination between modules.
  Evidence: reproducible import error (`cannot import name 'CRS' from 'pyproj'`) when batching mixed suites; isolated suite runs pass consistently.

## Decision Log

- Decision: Keep Roads report assets isolated under `wepp/roads/output` and never overwrite baseline `wepp/output` files.
  Rationale: Prevents baseline-report drift and preserves clean Roads-vs-baseline traceability.
  Date/Author: 2026-03-23 / Codex.

- Decision: Add explicit output-scope resolution (`baseline` vs `roads`) instead of accepting arbitrary path inputs.
  Rationale: Preserves security and avoids path-traversal or accidental cross-run file access.
  Date/Author: 2026-03-23 / Codex.

- Decision: Treat code review and QA review as first-class milestones with mandatory closure of medium/high findings.
  Rationale: Report-scope changes are cross-cutting and regression-prone; independent passes are required before closure.
  Date/Author: 2026-03-23 / Codex.

- Decision: Execute report rollovers in a minimal-regression sequence (`return_periods` -> `streamflow + water balance` -> `gl-dashboard` -> `storm event analyzer`) instead of one broad path swap.
  Rationale: Keeps blast radius bounded per component, makes rollback narrower, and surfaces coupling defects earlier.
  Date/Author: 2026-03-23 / Codex.

- Decision: Require a dedicated regression-focused subagent review artifact after each rollover milestone before moving to the next rollover.
  Rationale: Enforces objective risk checks at each boundary and prevents latent medium/high findings from propagating.
  Date/Author: 2026-03-23 / Codex.

- Decision: Persist Roads segment-loss summaries as parquet only and expose CSV via browse/download conversion on request.
  Rationale: Avoids duplicate on-disk artifacts and keeps a single canonical segment-loss dataset.
  Date/Author: 2026-03-24 / Codex.

- Decision: Segment-loss summary joins must prefer `target_hillslope_wepp_id` against `loss_pw0.hill.parquet` with explicit secondary fallback to `segment_run_id`.
  Rationale: Real Roads fixture runs key hillslope-loss outputs by targeted hillslope IDs, not segment run IDs; fallback maintains resilience if segment-keyed loss artifacts appear in other contexts.
  Date/Author: 2026-03-24 / Codex.

- Decision: Roads Run Results link availability is constrained by required-resource relpaths rather than run-state-only checks.
  Rationale: Prevents single-storm-ready runs from exposing links that require non-existent non-single-storm datasets.
  Date/Author: 2026-03-24 / Codex.

## Outcomes & Retrospective

Implementation complete. Milestones 1-10 remain closed, follow-up subagent review findings (including final subagent code/QA findings) are remediated, required review artifacts are current, and there are zero open medium/high findings.

## Context and Orientation

Roads execution already produces segment and watershed outputs under `wepp/roads/{segments,runs,output}`. Canonical WEPP report routes and adapters currently consume datasets and files rooted at `wepp/output` and `wepp/output/interchange`. This package must bridge that gap for Roads outputs by regenerating required resources under `wepp/roads/output/interchange` and adding a scoped report path so canonical report logic can render against Roads data.

Key files:

- Roads run pipeline: `wepppy/nodb/mods/roads/roads.py`
- Roads API/report routes: `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- Roads control/report templates: `wepppy/weppcloud/templates/controls/roads_pure.htm`, `wepppy/weppcloud/templates/reports/roads/summary.htm`
- Canonical WEPP report routes: `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`
- WEPP post-run helpers: `wepppy/nodb/wepp_nodb_post_utils.py`
- Interchange builders: `wepppy/wepp/interchange/*.py`
- Canonical WEPP report adapters: `wepppy/wepp/reports/*.py`
- UI style authority: `docs/ui-docs/ui-style-guide.md`

Report-resource targets for Roads scope (non-single-storm):

- `wepp/roads/output/interchange/H.pass.parquet`
- `wepp/roads/output/interchange/H.wat.parquet`
- `wepp/roads/output/interchange/loss_pw0.out.parquet`
- `wepp/roads/output/interchange/loss_pw0.hill.parquet`
- `wepp/roads/output/interchange/loss_pw0.chn.parquet`
- `wepp/roads/output/interchange/ebe_pw0.parquet`
- `wepp/roads/output/interchange/chnwb.parquet`
- `wepp/roads/output/interchange/totalwatsed3.parquet`
- `wepp/roads/output/interchange/README.md`

## Plan of Work

Milestone 1 establishes guardrails before any consumer rollover. Implement a strict output-scope resolver contract (`baseline|roads`, default `baseline`, explicit 400 on invalid scope) and ensure all scope-aware helpers use backend-owned path maps only. Add cache/staging isolation guards keyed by scope to prevent cross-scope reads/writes.

Milestones 2-5 execute one rollover component at a time to minimize regression risk:

- Milestone 2 (`return_periods`): migrate adapters/routes to scope-aware paths and scoped staging/caching behavior.
- Milestone 3 (`streamflow + water balance`): migrate related report loaders/parsers to scope-aware paths and scoped cache roots.
- Milestone 4 (`gl-dashboard`): remove literal baseline path coupling from dashboard payload builders/query helper inputs.
- Milestone 5 (`storm event analyzer`): apply scope resolver through analyzer route and transitive loader chain.

After each rollover milestone (2-5), dispatch a dedicated `reviewer` subagent focused on that component's regression surface. Record findings in component artifacts and resolve all medium/high findings before starting the next rollover milestone:

- `artifacts/return_periods_regression_review.md`
- `artifacts/streamflow_watbal_regression_review.md`
- `artifacts/gl_dashboard_regression_review.md`
- `artifacts/storm_event_analyzer_regression_review.md`

Milestone 6 implements Roads post-run report-resource regeneration and Roads Run Results summary UX. In `Roads.run_roads_wepp()`, after watershed rerun success, call an internal helper (for example `_regenerate_roads_report_resources`) that runs hillslope interchange, totalwatsed3 generation, watershed interchange, and interchange README generation for `wepp/roads/output`. Log every step to `roads.log`, verify required outputs, and fail explicitly when required resources are missing. Persist resource readiness and relpaths in `last_run_summary`. Add Roads summary route/template/control links per UI style guide.

Milestone 7 expands tests and fixture checks. Add targeted unit/integration tests for scope resolution, each rollover component, Roads report route rendering, and link correctness. Include fixture-backed verification on `clogging-starch` confirming required files and Roads report endpoints.

Milestones 8-9 run independent cross-cutting reviews:

- Milestone 8: `reviewer` subagent for end-to-end correctness/regression (`artifacts/code_review_findings.md`).
- Milestone 9: `qa_reviewer` (plus `test_guardian` if needed) for coverage/gate quality (`artifacts/qa_review_findings.md`).

Resolve all medium/high findings before closure.

Milestone 10 closes governance/docs and final validation. Update package tracker and ExecPlan living sections, run full gates, and capture exact command outcomes in handoff.

## File-Level Edit Map

Primary implementation targets in `/workdir/wepppy`:

- `wepppy/nodb/mods/roads/roads.py`
- `wepppy/weppcloud/routes/nodb_api/roads_bp.py`
- `wepppy/weppcloud/templates/reports/roads/summary.htm`
- `wepppy/weppcloud/templates/controls/roads_pure.htm`
- `wepppy/weppcloud/controllers_js/roads.js` (if Roads control adds dynamic results-state link)
- `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` (if scope-enabled canonical handlers are centralized)
- `wepppy/wepp/reports/*.py` modules that require output-scope support
- `tests/nodb/mods/test_roads_controller.py`
- `tests/weppcloud/routes/test_roads_bp.py`
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `tests/wepp/reports/*` (new/updated output-scope tests)
- package docs: `docs/work-packages/20260323_roads_wepp_reports_regen/*`

## Concrete Steps

Run commands from `/workdir/wepppy` unless noted.

1. Confirm fixture prerequisites:

    cd /workdir/wepppy
    test -d /wc1/runs/cl/clogging-starch
    test -f /wc1/runs/cl/clogging-starch/roads/UM1_roads_info.geojson
    test -f /wc1/runs/cl/clogging-starch/dem/wbt/relief.tif

2. Implement Milestone 1 guardrails (`output_scope` contract + scoped cache/path isolation) and run focused tests:

    wctl run-pytest tests/wepp/reports -k output_scope --maxfail=1
    wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1

3. Implement Milestone 2 (`return_periods`) and run component tests:

    wctl run-pytest tests/wepp/reports -k return_period --maxfail=1

4. Dispatch dedicated Milestone 2 regression review subagent (`reviewer`), save findings to `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/return_periods_regression_review.md`, resolve all medium/high findings, and only then proceed.

5. Implement Milestone 3 (`streamflow + water balance`) and run component tests:

    wctl run-pytest tests/wepp/reports -k "streamflow or watbal" --maxfail=1

6. Dispatch dedicated Milestone 3 regression review subagent (`reviewer`), save findings to `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/streamflow_watbal_regression_review.md`, resolve all medium/high findings, and only then proceed.

7. Implement Milestone 4 (`gl-dashboard`) and run component tests:

    wctl run-pytest tests/weppcloud -k gl_dashboard --maxfail=1

8. Dispatch dedicated Milestone 4 regression review subagent (`reviewer`), save findings to `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/gl_dashboard_regression_review.md`, resolve all medium/high findings, and only then proceed.

9. Implement Milestone 5 (`storm event analyzer`) and run component tests:

    wctl run-pytest tests/weppcloud -k "storm_event or analyzer" --maxfail=1

10. Dispatch dedicated Milestone 5 regression review subagent (`reviewer`), save findings to `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/storm_event_analyzer_regression_review.md`, resolve all medium/high findings, and only then proceed.

11. Implement Milestone 6 (Roads post-run regeneration + Roads Run Results summary) and run route/template/report tests:

    wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-pytest tests/wepp/reports --maxfail=1
    wctl run-npm test -- roads

12. Fixture verification on `clogging-starch`:

    wctl exec weppcloud python - <<'PY'
    from pathlib import Path
    from wepppy.nodb.mods.roads import Roads

    wd = "/wc1/runs/cl/clogging-starch"
    roads = Roads.tryGetInstance(wd) or Roads(wd, "disturbed9002-wbt-mofe.cfg")
    prep = roads.prepare_segments()
    run = roads.run_roads_wepp()
    required = [
        "wepp/roads/output/interchange/H.pass.parquet",
        "wepp/roads/output/interchange/loss_pw0.out.parquet",
        "wepp/roads/output/interchange/totalwatsed3.parquet",
    ]
    missing = [p for p in required if not Path(wd, p).exists()]
    print({"prepare_status": prep.get("status"), "run_status": run.get("status"), "missing": missing})
    PY

13. Independent cross-cutting code review milestone:

    - Spawn `reviewer` subagent on changed files.
    - Save findings to `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/code_review_findings.md`.
    - Resolve all medium/high findings before proceeding.

14. Independent cross-cutting QA review milestone:

    - Spawn `qa_reviewer` (and `test_guardian` if needed) on changed files/tests.
    - Save findings to `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/qa_review_findings.md`.
    - Resolve all medium/high findings before final gates.

15. Final gates:

    wctl run-npm lint
    wctl run-npm test
    wctl run-preflight-tests ./internal/checklist
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/package.md
    wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/tracker.md
    wctl doc-lint --path docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_execplan.md

## Validation and Acceptance

Acceptance is complete when:

- Roads run completion produces required resources under `wepp/roads/output/interchange`.
- Roads query/report summary includes resource-readiness metadata and stable relpaths.
- Roads Run Results summary renders and contains working links for Roads-scoped canonical report access.
- Baseline WEPP report behavior remains unchanged for non-Roads scope.
- Component rollovers (`return_periods`, `streamflow + water balance`, `gl-dashboard`, `storm event analyzer`) each have dedicated regression-review artifacts with all medium/high findings resolved before next rollover.
- Code review + QA review artifacts exist and all medium/high findings are resolved.
- Full validation gates pass with recorded command outputs.

## Idempotence and Recovery

- Re-running `prepare_segments` + `run_roads_wepp` should overwrite only Roads-scoped artifacts under `wepp/roads/*`.
- No step may overwrite baseline `wepp/output/*`.
- If a milestone introduces route/report regression, revert only scoped changes and keep Roads run artifacts untouched.
- On fixture recovery, remove only `wepp/roads/segments`, `wepp/roads/runs`, and `wepp/roads/output` to reset Roads scope.

## Artifacts and Notes

Implementation session must keep these package files current:

- `docs/work-packages/20260323_roads_wepp_reports_regen/tracker.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/prompts/active/roads_wepp_reports_regen_execplan.md`

Review artifacts required:

- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/return_periods_regression_review.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/streamflow_watbal_regression_review.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/gl_dashboard_regression_review.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/storm_event_analyzer_regression_review.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/code_review_findings.md`
- `docs/work-packages/20260323_roads_wepp_reports_regen/artifacts/qa_review_findings.md`
