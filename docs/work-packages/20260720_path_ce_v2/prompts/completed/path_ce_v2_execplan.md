# ExecPlan — PATH-CE v2 Resync, Parquet-Native Pipeline, UI + Reports

**Package**: `docs/work-packages/20260720_path_ce_v2/`
**Authoritative upstream**: `/workdir/PATH-cost-effective` @ `4e3b4a6`
**Fidelity**: faithful extraction — preserve upstream behavior; changes limited to the vendoring seam (imports, logging, parquet-native IO, dead-branch removal)
**Prereq**: D1–D5 ratified 2026-07-20 (tracker Decisions): in-worker Quarto, HTML-only, user-provisioned Omni (no auto-provisioning), $/acre serialization with unitizer dual display, sweep always-on with cache reuse (parallelization = follow-up package).

## Constraints

- No CSV interchange: all inputs read from run-dir parquet/psv/geojson listed in `artifacts/2026-07-20_delta_assessment.md` §2.
- No backward compatibility with pre-v2 PATH-CE config or `<wd>/path/` artifacts; migration is "re-run the mod".
- Upstream files map 1:1 to vendored modules; do not re-architect. Drop only: `legacy_gatecreek_format` branch, `create_handoff_bundle.py`, module-level `print`/DEBUG chatter (→ logger).
- NoDb conventions per `wepppy/nodb/AGENTS.md` (locked mutations, `dump_and_unlock`, scoped cache clears in RQ).
- Broad exception boundaries per `docs/standards/broad-exception-boundary-allowlist.md`.
- Status streaming on `{runid}:path_ce` for every long stage (contrasts, sweep, render).

## Phase 0 — Fixture + parity baseline

- Convert Jackson's static gatecreek sample data (`static/gatecreek_threshold_analysis_results*.csv`, docs/static downloads, geojsons) plus a wepppy-produced run's parquet set into a pytest fixture package.
- Record upstream reference outputs (selection sets, total/fixed cost, final Sddc, untreatable sets) for at least two threshold pairs and one filtered case, by running Jackson's `ce_select_sites_flexible` on the fixture in a scratch venv. Label evidence class in the artifact.
- Acceptance: fixture loads under `wctl run-pytest`; reference outputs committed as goldens.

## Phase 1 — Vendor the model core (decision-independent)

- `path_ce_solver.py` ← `PATH_CE.py`: keep dual id/area schema detection, Sddc scalar semantics, `<=1` fallback constraint, untreatable-increase class, result tuple → keep the existing structured `SolverResult` wrapper but populate from the faithful algorithm.
- `data_prep.py` ← `PATH_data_prep.py`: `build_aggregates` + `prepare_ce_and_plot_data`; parquet-native loading; contrast groups from `omni/contrast_id_definitions.psv`; outlet totals from `omni/scenarios.out.parquet`; extended severity code map.
- `threshold_sweep.py` ← `PATH_plot.py`: `find_threshold_ranges`, `all_thresholds`, plot helpers needed by QMDs; cache write/read (parquet + pkl) under `<wd>/path/`.
- Update `presets.py` to the full treatment-vector contract (label, scenario, unit_cost, quantity, fixed_cost) with Jackson's defaults; `data_loader.py` deletion deferred to Phase 2 (still imported by the pre-v2 controller — delete with the controller rework, along with the presets interim shims).
- Draft parameterization ADR (NTU→Sddc, cost units per D4 resolution, defaults, severity map).
- Acceptance: parity tests green against Phase 0 goldens; no NTU-proxy path remains in the vendored modules. **[DONE 2026-07-21: 23 parity tests green in container; ADR-0023 drafted]**

## Phase 2 — Controller + RQ orchestration

- `PathCostEffective` config schema: `sdyd_threshold`, `sddc_threshold`, `slope_range`, `severity_filter`, `treatments[]` (label/scenario/unit_cost `$_per_acre`/quantity/fixed_cost) — normalization + round-trip stability. Sweep is always-on (cache-keyed on config hash); `render_reports` flag for HTML.
- Precondition validation (replaces all Omni auto-provisioning, which is deleted): verify `omni/scenarios.hillslope_summaries.parquet` covers baseline + undisturbed + treatment scenarios, `omni/contrasts.out.parquet` covers each treatment vs control, `omni/contrast_id_definitions.psv` present for grouped modes, `watershed/hillslopes.parquet` and WGS geojsons exist. Per-treatment coverage means each configured treatment scenario appears among completed contrasts — psv ids absent from contrasts.out are legitimate (`landuse_unchanged` skips), not errors. Schema mode (wepp_id vs contrast_id) auto-detected from artifacts, matching upstream auto-detection. Failures produce actionable "run Omni scenarios/contrasts" errors surfaced at both the run endpoint and the UI.
- RQ task stages: validate preconditions → data prep → solve → sweep (bounded, cached) → persist artifacts → render report (Phase 3 service) → results payload.
- Persist under `<wd>/path/`: prepared frame, selection/treatment tables, sweep results, untreatable tables — parquet via existing interchange helpers; catalog refresh as today.
- Acceptance: RQ run on dev stack (against a run with pre-existing Omni artifacts) completes end-to-end minus report render; precondition failure paths verified; artifacts + status stream verified (executional).

## Phase 3 — Report rendering (HTML-only per D2)

- Vendor `PATH_CE_Report_Universal.qmd` and `static/` assets into the mod (`report/` subpackage); adapt: payload-JSON-only input resolution (drop landscape prefix auto-detect), parquet reads, outputs to `<wd>/path/report/`, sweep-cache reuse from Phase 2 artifacts. PDF QMD is not vendored (follow-up package).
- Render service: build payload JSON from controller config + run artifact paths; invoke in-worker Quarto CLI (D1); capture logs; nonzero exit → job failure with stacktrace surfaced.
- Docker: Quarto CLI pinned version + `plotly` in `docker/requirements-uv.txt` (`highspy` optional). Verify image builds and kernel resolution (QMD `jupyter:` kernel name must match installed kernel — replace `path_report_flex_venv` with the image kernel).
- Decide/execute CDN handling: vendor plotly/deck.gl locally alongside report or accept CDN (note in ADR-adjacent docs).
- Acceptance: report renders on dev stack from a real run's artifacts; HTML opens with working interactive map + slider (executional, manual browser check). **[DONE 2026-07-21: RQ job `dac5a67a` rendered from austere-inaction artifacts; headless Playwright check green (map + sliders + 3D surface, zero console errors) — Roger's in-browser look still recommended. CDN decision: main doc fully local; folium iframe still CDN-loaded (Phase 4 CSP item).]**

## Phase 4 — Serving + UI rework

- Browse microservice: inline HTML/asset serving restricted to `path/report/` subtree; CSP sandbox headers; traversal tests. Follow `docs/prompt_templates/security_review_template.md` surfaces.
- Blueprint: config GET/POST for expanded schema; report/download link discovery endpoint or bootstrap-state exposure (follow dss_export/features_export pattern).
- Control template + `path_ce.js`: thresholds (unitizer English/SI), slope range, severity multi-select, editable treatment table (four vectors; unit costs unitized $/acre⇄$/ha), run button, progress, precondition messaging, results summary, links to HTML report (new inline route) and download CSVs.
- `controllers_js/README.md` reference update; run_0 wiring already present (`show_path_ce`).
- Acceptance: `wctl run-npm lint && wctl run-npm test` green; manual round-trip of every parameter; report opens from run page.

## Phase 5 — Validation + closeout

- End-to-end: validation run `austere-inaction` (disturbed9002_wbt; all three mulch contrasts provisioned — see `artifacts/2026-07-20_validation_run_austere.md`) through PATH-CE v2 job → report links (executional; record evidence in tracker). Feasible primary window on this fixture: `sddc_threshold ≥ 48.2`.
- Parity spot-check vs upstream on the same inputs (document deltas, tolerance).
- Security review artifact (inline serving, render pipeline, upload-adjacent paths); close medium/high findings.
- Mod README rewrite (inputs, config, artifacts, report contract); ADR finalized; `PROJECT_TRACKER.md` and tracker updates; move this plan to `prompts/completed/` with outcome.

## Validation commands

- `wctl run-pytest tests/nodb/mods/path_ce -x` (or equivalent target once fixtures land)
- `wctl run-npm lint && wctl run-npm test`
- `tools/check_broad_exceptions.py --enforce-changed`
- Image build + `wctl up -d` smoke for Quarto stage

## Reporting discipline

Every status/closeout note labels evidence class (Static vs Ran) per `CLAUDE.md` Truthfulness section; delegated Codex runs are attributed.

---

## Outcome (2026-07-21, closeout)

All five phases executed with executional acceptance on the dev stack; four
independent Codex reviews (40 findings total) dispositioned with none ignored.
Full evidence trail in `../../tracker.md` and `../../artifacts/`. Remaining
owner items at closeout: manual authenticated UI round-trip + in-browser report
check; acknowledgment of the three accepted-risk rows in
`../../artifacts/2026-07-21_security_review.md`; commit.
