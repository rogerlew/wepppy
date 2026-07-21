# PATH-CE v2 Delta Assessment — Jackson's Codebase vs Vendored Implementation

**Date**: 2026-07-20 19:14 UTC
**Evidence class**: Static (read source in both codebases; no code was executed).
**Upstream source**: `/workdir/PATH-cost-effective` @ commit `4e3b4a6` ("Refactor result handling in PATH_CE.py"), github.com/jackson-nakae/PATH-cost-effective
**Vendored target**: `wepppy/nodb/mods/path_ce/` plus `wepppy/rq/path_ce_rq.py`, `wepppy/weppcloud/routes/nodb_api/path_ce_bp.py`, `wepppy/weppcloud/templates/controls/path_cost_effective_pure.htm`, `wepppy/weppcloud/controllers_js/path_ce.js`

## 1. Upstream inventory (what Jackson ships)

| File | LOC | Role |
|---|---:|---|
| `PATH_CE.py` | 253 | Solver: `ce_select_sites_flexible()` binary IP (PuLP), primary minimize-cost + secondary maximize-reduction fallback |
| `PATH_data_prep.py` | 1282 | `build_aggregates()` + `prepare_ce_and_plot_data()` — scenario alignment, contrast grouping, severity mapping, reduction columns |
| `PATH_plot.py` (= `PATH_Plots.py`, identical) | 782 | `find_threshold_ranges()` (binary-search feasibility), `all_thresholds()` (grid sweep), matplotlib/plotly helpers, selection map |
| `PATH_CE_Report_Universal.qmd` | 1780 | Interactive HTML report (Quarto, jupyter kernel): parameters, run results, deck.gl selection map, threshold sweep + slider, download CSVs |
| `PATH_CE_Report_PDF.qmd` | 1080 | Static PDF report (Quarto → LaTeX), same params/caches |
| `render_both_reports.py` | 137 | Renders HTML then PDF with shared params (CLI `-P` + env vars) |
| `create_handoff_bundle.py` | 112 | Offline bundle packager (not needed for integration) |
| `static/js`, `static/css` | — | `interactive-hillslope-map.js`, `interactive-cost-surface.js`, CSS, vendored deck.gl 8.9.31 + papaparse 5.4.1 |

Report parameter contract (QMD front matter + `weppcloud_payload_json`, designed by Jackson for WEPPcloud integration): `landscape`, `sdyd_threshold` (tons/acre), `sddc_threshold` (tons), `treatments[]` (labels), `treatment_cost[]` ($/acre), `treatment_quantity[]` (multipliers), `fixed_cost[]` ($ per treatment), input file paths, spatial layer paths, contrast groups file. Payload keys support both vector style and list-of-objects (`name/cost/quantity/fixed_cost`).

## 2. Input contract → wepppy artifact mapping

Jackson's landscape-prefixed CSVs are flat-file exports of tables wepppy already writes as parquet. Direct mapping (no schema translation needed beyond column aliases his prep already handles):

| Upstream input (`{landscape}_…`) | wepppy artifact | Producer |
|---|---|---|
| `scenarios.hillslope_summaries.csv` | `omni/scenarios.hillslope_summaries.parquet` | `OmniArtifactExportService.compile_hillslope_summaries` (`omni_artifact_export_service.py:605`) |
| `contrasts.out.csv` | `omni/contrasts.out.parquet` | `OmniArtifactExportService.contrasts_report` (`omni_artifact_export_service.py:483`) |
| `hillslopes.parquet` | `watershed/hillslopes.parquet` | `peridot_runner.post_abstract_watershed` (`peridot_runner.py:477`) |
| `subcatchments.WGS.geojson` | `dem/wbt/subcatchments.WGS.geojson` (backend-resolved via `Watershed` properties) | wbt emulator / topaz / taudem |
| `channels.WGS.geojson` | `dem/wbt/channels.WGS.geojson` (backend-resolved) | wbt emulator / topaz / taudem |
| `contrast_id_definitions.psv` | `omni/contrast_id_definitions.psv` | `omni_state_contrast_mixin._write_contrast_id_definitions_psv` (`:715`) |
| outlet totals (payload `outlet_totals`) | `omni/scenarios.out.parquet` (`key/v/units/scenario`) | `OmniArtifactExportService.scenarios_report` (`:425`) |

Caveats:
- `contrasts.out.parquet` carries `contrast_topaz_id` only for `cumulative` selection mode; grouped modes require joining through `contrast_id_definitions.psv`. Jackson's prep supports both paths (`contrast_groups` arg).
- `PATH_data_prep._load_df` already reads parquet; the Universal QMD hard-codes `pd.read_csv` for the outlet contrasts only — a one-line adaptation.

## 3. Behavioral deltas: vendored model is stale

The vendored port predates Jackson's current model and diverges in load-bearing ways:

1. **Water-quality constraint basis.** Vendored solver (`path_ce_solver.py:71-99`) uses `NTU post-fire` / `NTU reduction *` columns as the Sddc proxy (documented caveat in mod README). Jackson's current solver uses real outlet sediment discharge: `Sddc post-fire` (scalar outlet total from row 0) and `Sddc reduction *` columns from contrasts. This is a formula/semantics change → parameterization ADR required.
2. **Secondary (fallback) model site constraint.** Vendored `_run_secondary_model` forces `sum(x[t][i]) == 1` (every site must be treated). Jackson's is `<= 1` with an explicit comment that the fallback must preserve leaving sites untreated. Vendored behavior is a bug relative to current upstream.
3. **Identifier/aggregation schema.** Vendored operates per-`wepp_id` only. Jackson's auto-detects `wepp_id`/`area` vs `contrast_id`/`area_sum`, supporting stream-order/user-defined contrast groups aggregated by `build_aggregates`.
4. **Untreatable-increase classification.** Jackson's returns a third class — hillslopes where every treatment strictly increases Sdyd — styled separately in reports. Absent from vendored port.
5. **Data prep depth.** Jackson's `build_aggregates` handles: contrast-group expansion (psv/tsv/DataFrame), undisturbed-scenario contrast_id backfill, runoff-weighted NTU aggregation, outlet-totals override, slope/severity eligibility substitution (ineligible treated rows fall back to sbs_map metrics), extended disturbed landuse-severity code sets (e.g., 105015-class keys). Vendored `data_loader.py` is a simple per-scenario merge with none of this.
6. **Threshold sweep + reports.** Entirely new capabilities: `find_threshold_ranges` (binary search on feasibility), `all_thresholds` (bounded grid sweep, up to ~75×75 solves, cached as csv/pkl), interactive HTML report (deck.gl map, cost surface, slider linked to sweep), PDF report, download CSV bundle.
7. **Cost model.** Vendored: single `unit_cost` per mulch preset ($/ha via unitizer), `quantity=1.0`, `fixed_cost=0` hard-coded. Jackson: per-treatment `cost` ($/acre) × `quantity` multiplier (0.5/1/2) + per-treatment `fixed_cost` activated by a binary. UI must expose all four vectors.

## 4. Orchestration gap: contrasts are now required

Current `run_path_cost_effective_rq` provisions Omni **scenarios** only (undisturbed + 3 mulches) — never contrasts. With NTU-proxy removed, the Sddc constraint requires `omni/contrasts.out.parquet` for each mulch scenario vs `sbs_map` control. The RQ task must additionally provision/run Omni contrasts (mode configurable; cumulative per-hillslope is N_hillslopes × 3 WEPP runs — cost scales with watershed size; grouped modes are cheaper). This is the largest new orchestration surface and needs a default-mode decision.

## 5. Infrastructure gaps (report rendering + serving)

- **Quarto CLI: not installed** in any image. `docker/requirements-uv.txt` already has pulp, geopandas, folium, ipykernel, nbconvert/nbclient/nbformat; missing: `plotly`, `papermill` (not strictly needed if Quarto drives execution), `highspy` (optional solver backend). PDF additionally needs a LaTeX toolchain (TinyTeX, ~350-500 MB image cost) unless the PDF QMD is reworked for typst or deferred.
- **Existing design stub**: `docs/dev-notes/qmd-reports-feature.spec.md` sketches a hardened sidecar container for *untrusted* QMD execution. PATH-CE's QMDs are vendored first-party code executing in the worker's existing trust domain, so in-worker rendering is defensible; the sidecar remains an option if Roger prefers isolation.
- **Inline HTML serving: no existing route.** The browse microservice (`wepppy/microservices/browse/flow.py:_render_file_response`) renders `.html` as source text; `/download/` forces attachment. Serving the generated report as a live page requires a new inline route. Security note: run dirs can contain user-supplied files, so inline HTML must be restricted to the report subtree and/or served with CSP sandbox headers — this is the package's main new attack surface (triage: high).
- **CDN dependencies**: the HTML report loads plotly and deck.gl from CDNs at view time (papaparse/deck.gl also vendored under `static/js/vendor`). Decide whether to vendor plotly locally for deployment robustness.

## 6. Verification items (carry into exec plan)

- **Area/cost unit consistency**: solver multiplies `area` (ha, from m²×1e-4) by `treatment_cost` ($/acre) × quantity. Either upstream has a ha-vs-acre inconsistency or costs are implicitly $/ha despite labels. Resolve with Jackson before freezing the UI unit contract; add a unit parity test. (ADR material.)
- **`Sddc post-fire` scalar semantics**: solver reads `.iloc[0]` — assumes outlet-total broadcast to all rows; confirm data prep guarantees this after filtering.
- **Threshold sweep cost**: grid sweep is thousands of LP solves; needs bounded ranges (upstream binary-search does this), progress reporting through the status channel, and cache reuse (`*_threshold_analysis_results_generated.pkl/csv`) so re-renders don't recompute.
- **Landuse severity map**: upstream uses two different severity code sets (extended set in `build_aggregates`, base set in legacy compat). Vendored `DEFAULT_SEVERITY_MAP` uses the base set. Adopt the extended set; confirm coverage for disturbed landuse keys in current wepppy builds.
- **`prepare_ce_and_plot_data(legacy_gatecreek_format=True)` path**: dead weight for us (per Roger: no backward compatibility). Drop on vendoring.
- **RQ status/interrupt conventions**: sweep + render phases must publish to `{runid}:path_ce` and respect the standard job lifecycle.

## 7. Recommended integration shape

Vendor Jackson's three Python modules faithfully (rename into the mod, print→logger, parquet-native `_load_df`, drop legacy-format branch) so future upstream syncs diff cleanly — the current rework is expensive precisely because the first port rewrote structure. Keep `PathCostEffective` NoDb controller as the orchestration/config shell; extend config to the full parameter contract; RQ task gains contrasts provisioning, sweep, and report-render stages; reports render via Quarto in-worker into `<wd>/path/report/` with a payload JSON (Jackson's `weppcloud_payload_json` hook) pointing at run parquet artifacts.
