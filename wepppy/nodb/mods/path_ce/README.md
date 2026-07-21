# PATH Cost-Effective (PathCE) NoDb Module

> Select the most cost-effective set of post-fire hillslope treatments that meets
> user-defined sediment-yield and outlet-discharge thresholds, by binary integer
> programming over Omni scenario/contrast outputs. Vendored from Jackson Nakae's
> PATH-cost-effective (upstream commit `4e3b4a6`), parquet-native, with an
> interactive Quarto HTML report.

> **See also:** `../../AGENTS.md` for NoDb conventions;
> `docs/adrs/ADR-0023-path-ce-v2-parameterization.md` for the parameterization
> contract; `docs/work-packages/20260720_path_ce_v2/` for provenance, reference
> goldens, review dispositions, and the security review.

## Model

The primary model minimizes treatment cost subject to: at most one treatment per
hillslope (or contrast group); per-hillslope sediment-yield reduction
requirements derived from `sdyd_threshold`; and a watershed outlet
sediment-discharge constraint derived from `sddc_threshold` against Omni outlet
contrast deltas. When the primary model is infeasible, a secondary model
maximizes total discharge reduction under the same per-hillslope constraints
(reported as `primary_status = 0`). Hillslopes whose yield increases under every
treatment are force-excluded and reported as a distinct untreatable class.

Faithfulness: `path_ce_solver.ce_select_sites_flexible`, `data_prep`, and
`threshold_sweep` are faithful extractions of upstream — keep them diffable when
syncing; wepppy-specific behavior lives in the seams (`prepare_solver_inputs`,
`run_path_cost_effective_solver`, module docstrings enumerate the deltas). The
solver seam converts the hectare-valued area column to acres so costs are
`area (ac) × unit_cost ($/ac) × quantity (tons/ac)`, and realigns treatment
vectors to the frame's reduction-column order (the core pairs positionally).

## Module map

- `path_ce_solver.py` — faithful core + wepppy seam wrapper (`SolverResult`).
- `data_prep.py` — faithful aggregation/preparation; consumes run artifacts in
  place; grouped (psv) and cumulative (contrast_topaz_id) schema modes.
- `threshold_sweep.py` — feasibility-range binary search + bounded threshold
  grid sweep (powers the report's sliders and cost surface); plot helpers.
- `presets.py` — treatment-vector contract and defaults; labels derive from
  scenario names (`mulch_15_sbs_map` → `0.5 tons/acre`) and mismatches are
  rejected — labels key the prepared-frame columns.
- `preconditions.py` — validates user-provisioned Omni artifacts (D3: PATH never
  provisions); actionable errors name what to run. psv contrast ids absent from
  `contrasts.out.parquet` are legitimate (`landuse_unchanged` skips); coverage
  means each configured treatment has completed `sbs_map`-control contrasts.
- `path_cost_effective.py` — `PathCostEffective` NoDb controller: config
  normalization, stage methods (validate → prepare_data → solve → run_sweep →
  render), results/status persistence, sweep cache (config + frame hash keyed).
- `report_service.py` — stages and renders the Quarto HTML report in-worker
  (pinned Quarto CLI in the image; payload delivered via env var), publishes to
  `<wd>/path/report/` with a near-atomic rename swap.
- `report/` — vendored QMD (anchor-splicing builder in the work package keeps
  upstream sections byte-identical; WEPPPY-SEAM markers) + static JS/CSS
  (deck.gl/papaparse vendored; plotly.js staged from the Python package).

## Configuration (`path_ce.nodb`)

`sdyd_threshold` (tonnes/acre — matches the prepared-data unit),
`sddc_threshold` (tonne/yr — matches the Omni outlet artifact unit),
`slope_range` (degrees, either bound nullable), `severity_filter`
(High/Moderate/Low subset or null; group-mode caveat in ADR-0023 §5),
`treatments` (list of label/scenario/unit_cost `$/acre`/quantity/fixed_cost).
Normalization is strict: non-finite, negative, mismatched-label, duplicate, or
unknown-scenario payloads are rejected. The HTML report always renders (the
retired `render_reports` flag is dropped from stale payloads on normalization).

## Preconditions (user-provisioned, D3)

Before running PATH-CE the run must carry: Omni scenario summaries covering
`sbs_map`, `undisturbed`, and every configured treatment scenario; Omni outlet
contrasts (treatment vs `sbs_map` control) for every configured treatment;
`omni/contrast_id_definitions.psv` for grouped runs; `omni/scenarios.out.parquet`;
`watershed/hillslopes.parquet`. WGS geojson exports are required only for the
report (missing → run completes, report skipped with a recorded reason).

## Pipeline and artifacts

The RQ task (`wepppy.rq.path_ce_rq`, channel `{runid}:path_ce`) runs the
controller stages against one config snapshot. Artifacts under `<wd>/path/`:
prepared frame + aggregation tables (`path_ce_*.parquet`), `selection.parquet`
(per-site treatment + acre-based cost), `hillslope_sdyd.parquet`,
`untreatable.parquet`, `untreatable_increase.parquet`, `sweep.parquet`
(per-cell results incl. JSON-encoded selections and error column) +
`sweep_manifest.json`, and `report/` (self-contained HTML tree + download CSVs).

## Report serving

The browse microservice serves `<wd>/path/report/` inline at
`runs/{runid}/{config}/report/path_ce/` with a sandbox CSP (opaque origin — no
cookies or credentialed API reach), inline media-type allowlist, and strict
subtree/symlink containment. See the package security review for the full
surface analysis.

## Testing

`tests/nodb/mods/path_ce/` (solver/data-prep parity against upstream goldens,
seam contracts, controller stages, preconditions, report service, plus a real
Quarto render integration test gated on the CLI), `tests/rq/test_path_ce_rq.py`,
`tests/weppcloud/routes/test_path_ce_bp.py`,
`tests/microservices/test_browse_report_routes.py`. Fixtures and goldens live in
`tests/data/path_ce/`; regeneration scripts and provenance in the work package.

## Known upstream flags (reported to Jackson)

Upstream multiplies $/acre rates against hectare areas (wepppy corrects at the
seam); "tons" labels denote metric tonnes in the artifacts; the prepared-data
yield unit is the mixed tonne/acre; upstream's report QMD had a vestigial
ipywidgets import, an infeasible-fallback type bug, and dead per-treatment
extraction in the 3D surface cell (all corrected in the vendored copy).
