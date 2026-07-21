"""Build the vendored PATH-CE report QMD from Jackson's upstream QMD.

Splices wepppy seam blocks into upstream 4e3b4a6 PATH_CE_Report_Universal.qmd
using exact, uniqueness-checked text anchors, so every kept section stays
byte-identical and the vendored file diffs cleanly against upstream. Seams
(all marked WEPPPY-SEAM):

- frontmatter: python3 kernel; payload-json param only
- head loader: local vendored plotly/deck.gl instead of CDN
- imports: wepppy vendored modules instead of PATH_* locals
- section 1: payload-only resolution; prepared frame loaded from the job
  artifact (no re-prep); parquet list-columns stringified; area alias shown in
  acres; script-safe JSON helper; channels-optional links
- section 2: solve via the wepppy seam wrapper on a frame without the display
  `area` alias (the wrapper auto-detects `area` and would double-convert),
  with configured slope/severity filters applied; sweep loaded from the job's
  sweep.parquet with the exact configured-threshold result appended for the
  interactive map (the grid is integer-quantized)
- 3D surface: scalar-only grid collection (upstream's per-treatment geometry
  extraction was dead code and rejected treatment subsets); exact-run marker
  instead of nearest-grid snapping; embedded via to_json + Plotly-wait shim

Usage: python build_vendored_qmd.py <upstream_qmd> <out_qmd>
"""

import hashlib
import sys

UPSTREAM = sys.argv[1]
OUT = sys.argv[2]

UPSTREAM_SHA256 = "3a038480f513114674dd40b0f34868e3710db49750e40302aff25421f895c7b2"

src_bytes = open(UPSTREAM, "rb").read()
digest = hashlib.sha256(src_bytes).hexdigest()
if digest != UPSTREAM_SHA256:
    raise SystemExit(
        f"upstream QMD hash mismatch: expected {UPSTREAM_SHA256}, got {digest}; "
        f"update the pin only after re-reviewing the seams against the new upstream"
    )
src = src_bytes.decode("utf-8")


def extract(
    start_anchor: str,
    end_anchor: str,
    include_end: bool = True,
    occurrences: int = 1,
) -> str:
    """Extract [start, end) from upstream, taking the FIRST start occurrence.

    ``occurrences`` pins how many times the start anchor appears in upstream
    so an upstream change that adds/removes occurrences fails loudly.
    """
    count = src.count(start_anchor)
    assert count == occurrences, (
        f"anchor occurrence drift for {start_anchor[:60]!r}: expected {occurrences}, found {count}"
    )
    i = src.index(start_anchor)
    j = src.index(end_anchor, i)
    if include_end:
        j += len(end_anchor)
    return src[i:j]


def patched(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"patch target not unique: {old[:60]!r}"
    return text.replace(old, new, 1)


FRONTMATTER = """---
title: "PATH Report"
subtitle: "Auto‑generated summary of PATH outputs with interactive maps"
format:
  html:
    toc: true
    toc-location: left
    number-sections: false
    code-fold: show
    theme: cosmo
    embed-resources: true
    grid:
      sidebar-width: 220px
      body-width: 950px
      margin-width: 50px
jupyter: python3
# WEPPPY-SEAM: parameters come exclusively from the payload JSON written by
# the render service (wepppy.nodb.mods.path_ce.report_service).
params:
  weppcloud_payload_json: null
---
"""

HEAD_LOADER = """```{=html}
<script>
  // WEPPPY-SEAM: load vendored Plotly and deck.gl (no CDN; staged by the
  // render service) without RequireJS interference.
  (function() {
    const savedDefine = window.define;
    delete window.define;

    function restoreDefine() {
      if (savedDefine) { window.define = savedDefine; }
    }

    let pending = 2;
    function done() {
      pending -= 1;
      if (pending <= 0) { restoreDefine(); }
    }

    const plotlyScript = document.createElement('script');
    plotlyScript.src = 'static/js/vendor/plotly.min.js';
    plotlyScript.onload = done;
    plotlyScript.onerror = done;

    const deckScript = document.createElement('script');
    deckScript.src = 'static/js/vendor/deck.gl-8.9.31.min.js';
    deckScript.onload = done;
    deckScript.onerror = done;

    document.head.appendChild(plotlyScript);
    document.head.appendChild(deckScript);
  })();
</script>
```
"""

IMPORTS_CELL = """```{python}
#| echo: false
import os
import json
import math
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import shape
from pathlib import Path
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from IPython.display import Markdown, display, clear_output, HTML
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import plotly.graph_objs as go
import ast

# WEPPPY-SEAM: vendored modules (upstream imported PATH_CE/PATH_plot/PATH_data_prep)
from wepppy.nodb.mods.path_ce.path_ce_solver import (
    ACRES_PER_HECTARE,
    PathCESolverError,
    run_path_cost_effective_solver,
)
from wepppy.nodb.mods.path_ce.threshold_sweep import plot_sddc_vs_cost, plot_sdyd_vs_cost
```
"""

# upstream verbatim fragments -------------------------------------------------
prose = extract("> PATH is a decision-support tool", "**Static PDF Version:**", include_end=False).rstrip()
params_guard = extract(
    "# Ensure params exists even if Quarto didn't inject it",
    "    params = {}",
)
# _parse_json_like is defined twice upstream (params helpers + a local copy
# inside the folium cell, which lives in the kept tail); take the first.
helpers = extract(
    "def _parse_json_like(value):", "def _find_qmd_path", include_end=False, occurrences=2
).rstrip()
aliases_block = extract(
    "# Backward-compatible aliases for report sections",
    "print(f\"Report schema: {'hillslope groups (contrast-based)' if has_grouping else 'individual hillslopes (wepp-based)'}\")",
)
links_block = extract(
    "# Create clickable links for file parameters",
    "channels_link = f'<a href=\"static/{Path(channels_geojson).name}\" download>{Path(channels_geojson).name}</a>'",
)
downloads_table_block = extract(
    'download_dir = Path("static/downloads")',
    "display(HTML(parameter_df.to_html(escape=False)))",
)
interactive_block = extract(
    "# Config used by Section 3 interactive module (JS)",
    'display(HTML(f"<script>window.PATH_REPORT_CONFIG = {json.dumps(interactive_config)};</script>"))',
)
assignments_block = extract(
    "# Build treatment assignment table",
    "assign_df = pd.DataFrame(assignments)",
)
tail = src[src.index("### 2.1 Interactive Map of Selected Hillslopes"):]

# seam patches inside verbatim fragments --------------------------------------

# area alias in acres for tooltips/downloads; the solve uses a frame without
# this alias (see solve cell) so the wrapper's ha->ac conversion runs once
aliases_block = patched(
    aliases_block,
    'final_df["area"] = final_df["area_sum"]',
    'final_df["area"] = pd.to_numeric(final_df["area_sum"], errors="coerce") * ACRES_PER_HECTARE  # WEPPPY-SEAM: display acres',
)

# channels layer is optional; upstream link building raised on None
links_block = patched(
    links_block,
    "channels_link = f'<a href=\"static/{Path(channels_geojson).name}\" download>{Path(channels_geojson).name}</a>'",
    "channels_link = (\n"
    "  f'<a href=\"static/{Path(channels_geojson).name}\" download>{Path(channels_geojson).name}</a>'\n"
    "  if channels_geojson else \"Unavailable\"\n"
    ")  # WEPPPY-SEAM: channels optional",
)

downloads_table_block = patched(
    downloads_table_block,
    "      None,\n      None,\n    treatments_display,",
    "      slope_filter_display,\n      bs_filter_display,\n    treatments_display,",
)

# script-context-safe JSON (run-derived data lands inside <script>)
interactive_block = patched(
    interactive_block,
    'display(HTML(f"<script>window.PATH_REPORT_CONFIG = {json.dumps(interactive_config)};</script>"))',
    'display(HTML(f"<script>window.PATH_REPORT_CONFIG = {_script_json(interactive_config)};</script>"))',
)

# 3D surface: upstream extracted per-treatment geometries (dead code for the
# surface; raised on <3 treatments); collect scalars only
_frames_start = "frames_data = []"
_frames_end = "sdyd_unique = sorted(set([frame['sdyd_thr'] for frame in frames_data]))"
assert tail.count(_frames_start) == 1 and tail.count(_frames_end) == 1
tail = (
    tail[: tail.index(_frames_start)]
    + """# WEPPPY-SEAM: upstream extracted per-treatment geometries here; they were
# unused by the cost surface and raised on treatment subsets. Collect only
# the scalar grid values.
frames_data = []
for i in range(len(results_df)):
    frames_data.append({
        'sdyd_thr': results_df['sdyd_threshold'][i],
        'sddc_thr': results_df['sddc_threshold'][i],
        'total_cost': results_df['total_cost'][i],
    })

"""
    + tail[tail.index(_frames_end):]
)

# 3D marker: exact configured thresholds + actual run cost, not nearest cell
_marker_old = extract(
    "sdyd_thr = sdyd_threshold",
    "sddc_thr = sddc_unique[j]",
)
tail = patched(
    tail,
    _marker_old,
    """# WEPPPY-SEAM: mark the exact configured thresholds and actual run cost
# instead of snapping to the nearest integer grid cell (which can differ
# by orders of magnitude for fractional thresholds).
sdyd_thr = sdyd_threshold
sddc_thr = sddc_threshold
_marker_cost = float(total_cost)""",
)
tail = patched(
    tail,
    "z=[cost_grid[i, j]],",
    "z=[_marker_cost],",
)

tail = patched(
    tail,
    "display(fig)",
    """# WEPPPY-SEAM: embed against the locally loaded Plotly (head loader) so the
# report renders offline and version-matched; the head loader is async, so
# defer newPlot until window.Plotly exists.
_surface_json = fig.to_json().replace("</", "<\\\\/")
display(HTML(
  '<div id="path-cost-surface" style="min-height:640px"></div>'
  '<script>(function(){var spec=' + _surface_json + ';'
  'function draw(){if(window.Plotly){Plotly.newPlot("path-cost-surface",spec.data,spec.layout,{responsive:true});}'
  'else{setTimeout(draw,200);}}draw();})();</script>'
))""",
)

# interactive map: pass active treatment labels (JS renders legend/tooltips
# dynamically; upstream hardcoded the three default tiers)
tail = patched(
    tail,
    "        selectionIdField: cfg.selectionIdField,",
    "        selectionIdField: cfg.selectionIdField,\n        treatmentLabels: cfg.treatmentLabels,",
)

PARAMS_CELL = f"""## 1. Parameters
The following Parameters were used for this PATH run:
```{{python}}
#| echo: false
{params_guard}

{helpers}

def _script_json(obj):
  \"\"\"WEPPPY-SEAM: JSON safe for embedding in a <script> context.\"\"\"
  return (
    json.dumps(obj)
    .replace("</", "<\\\\/")
    .replace("\\u2028", "\\\\u2028")
    .replace("\\u2029", "\\\\u2029")
  )

# WEPPPY-SEAM: payload-only parameter resolution. The render service writes a
# payload JSON with thresholds, treatment vectors, filters, and artifact paths;
# the upstream landscape/frontmatter/env cascade is removed.
_payload_path = params.get("weppcloud_payload_json") or os.getenv("PATH_REPORT_INPUT_JSON")
if not _payload_path or not Path(str(_payload_path)).exists():
  raise ValueError(
    "weppcloud_payload_json is required (written by the PATH-CE render service)."
  )
with open(_payload_path, "r", encoding="utf-8") as f:
  payload = json.load(f)

sdyd_threshold = _to_float_required(_payload_get(payload, "sdyd_threshold"), "sdyd_threshold")
sddc_threshold = _to_float_required(_payload_get(payload, "sddc_threshold"), "sddc_threshold")

treatments = _to_str_list(_payload_get(payload, "treatments"), [])
treatment_cost = _to_num_list(_payload_get(payload, "treatment_cost"), [])
treatment_quantity = _to_num_list(_payload_get(payload, "treatment_quantity"), [])
fixed_cost = _to_num_list(_payload_get(payload, "fixed_cost"), [])
if not treatments or not (
  len(treatments) == len(treatment_cost) == len(treatment_quantity) == len(fixed_cost)
):
  raise ValueError("Payload must provide equal-length treatment vectors.")

_slope_range = _payload_get(payload, "slope_range") or [None, None]
_severity_filter = _payload_get(payload, "severity_filter")
slope_filter_display = (
  f"{{_slope_range[0]}}–{{_slope_range[1]}} deg"
  if any(v is not None for v in _slope_range) else "None"
)
bs_filter_display = ", ".join(_severity_filter) if _severity_filter else "None"

# WEPPPY-SEAM: configured eligibility filters must also apply to the report's
# re-solve so its numbers match the job artifacts.
_slope_for_solver = None
if any(v is not None for v in _slope_range):
  _slope_for_solver = (
    _slope_range[0] if _slope_range[0] is not None else float("-inf"),
    _slope_range[1] if _slope_range[1] is not None else float("inf"),
  )

_input_files = _payload_get(payload, "input_files") or {{}}
_spatial_files = _payload_get(payload, "spatial_files") or {{}}
prepared_frame_path = _input_files.get("prepared_frame")
sweep_parquet_path = _input_files.get("sweep")
subcatchments_geojson = _spatial_files.get("subcatchments_geojson")
channels_geojson = _spatial_files.get("channels_geojson")
interactive_hillslopes_geojson = subcatchments_geojson
interactive_channels_geojson = channels_geojson or ""

if not prepared_frame_path or not Path(str(prepared_frame_path)).exists():
  raise ValueError(f"Prepared frame artifact not found: {{prepared_frame_path!r}}")

final_df = pd.read_parquet(prepared_frame_path)

# WEPPPY-SEAM: parquet preserves list-typed columns; stringify them to mirror
# the CSV round-trip upstream relied on (folium/json serialization and
# _parse_json_like both expect the string form).
for _col in ("topaz_ids", "topaz_ids_all"):
  if _col in final_df.columns:
    final_df[_col] = final_df[_col].apply(
      lambda v: str(list(v)) if isinstance(v, (list, np.ndarray)) else v
    )

{aliases_block}

{links_block}

{downloads_table_block}

{interactive_block}
```
"""

SOLVE_SWEEP_CELL = f"""## 2. Run Results

```{{python}}
#| echo: false
import io
from contextlib import redirect_stdout, redirect_stderr

# WEPPPY-SEAM: solve through the wepppy seam wrapper (acre cost basis +
# label-based treatment alignment; ADR-0023) so the report's numbers match the
# job's persisted artifacts. The display `area` alias (acres) is dropped from
# the solve frame — the wrapper detects `area` first and would double-convert.
_solve_frame = (
  final_df.drop(columns=["area"])
  if ("area" in final_df.columns and "area_sum" in final_df.columns)
  else final_df
)
with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
  try:
    _solver_result = run_path_cost_effective_solver(
        _solve_frame,
        treatments,
        treatment_cost,
        treatment_quantity,
        fixed_cost,
        sdyd_threshold=sdyd_threshold,
        sddc_threshold=sddc_threshold,
        slope_range=_slope_for_solver,
        bs_threshold=_severity_filter,
    )
  except PathCESolverError:
    _solver_result = None

if _solver_result is None:
  # Continue report generation even when current thresholds are infeasible.
  _clean = final_df.copy()
  for col in [c for c in _clean.columns if "Sddc" in c or "Sdyd" in c]:
    _clean[col] = pd.to_numeric(_clean[col], errors="coerce").fillna(0)
  ids = _clean[id_column].tolist()
  baseline_sdyd = pd.to_numeric(_clean["Sdyd post-fire"], errors="coerce")
  status = 0
  treatment_cost_vectors = {{}}
  sediment_yield_reduction_thresholds = (baseline_sdyd - sdyd_threshold).clip(lower=0)
  selected_hillslopes = []
  treatment_hillslopes = [[] for _ in treatments]
  total_Sddc_reduction = 0.0
  final_Sddc = float(pd.to_numeric(_clean["Sddc post-fire"], errors="coerce").iloc[0])
  hillslopes_sdyd = list(zip(ids, baseline_sdyd.tolist()))
  sdyd_df = pd.DataFrame({{id_column: ids, "final_Sdyd": baseline_sdyd}})
  untreatable_sdyd = sdyd_df[sdyd_df["final_Sdyd"] > sdyd_threshold].copy()
  total_cost = 0.0
  total_fixed_cost = 0.0
  # upstream set this to 0.0 here, which breaks the .empty checks downstream
  untreatable_sdyd_increase = pd.DataFrame(columns=[id_column, "final_Sdyd"])
else:
  status = _solver_result.primary_status
  treatments = list(_solver_result.treatments)  # aligned label order
  treatment_cost_vectors = _solver_result.treatment_cost_vectors
  sediment_yield_reduction_thresholds = _solver_result.sediment_yield_reduction_thresholds
  selected_hillslopes = _solver_result.selected_hillslopes
  treatment_hillslopes = _solver_result.treatment_hillslopes
  total_Sddc_reduction = _solver_result.total_sddc_reduction
  final_Sddc = _solver_result.final_sddc
  hillslopes_sdyd = _solver_result.hillslopes_sdyd
  sdyd_df = _solver_result.sdyd_df
  untreatable_sdyd = _solver_result.untreatable_sdyd
  total_cost = _solver_result.total_cost
  total_fixed_cost = _solver_result.total_fixed_cost
  untreatable_sdyd_increase = _solver_result.untreatable_sdyd_increase

{assignments_block}

# WEPPPY-SEAM: the threshold sweep is loaded from the job's sweep artifact
# (Phase 2 persists it with JSON-encoded selection columns); upstream computed
# it at render time and cached csv/pkl beside the QMD.
results_df = pd.DataFrame()
has_threshold_analysis = False
generated_threshold_csv_name = "PATH_threshold_analysis_results.csv"
generated_threshold_csv_path = download_dir / generated_threshold_csv_name

if sweep_parquet_path and Path(str(sweep_parquet_path)).exists():
  results_df = pd.read_parquet(sweep_parquet_path)
  if "error" in results_df.columns:
    _errored = results_df["error"].fillna("").astype(str) != ""
    if _errored.any():
      print(f"Note: {{int(_errored.sum())}} sweep cell(s) failed and are excluded.")
    results_df = results_df.loc[~_errored].drop(columns=["error"]).reset_index(drop=True)
else:
  print("Warning: sweep artifact unavailable; interactive threshold analysis disabled.")

has_threshold_analysis = not results_df.empty
if has_threshold_analysis:
  interactive_df = results_df.copy()
  # WEPPPY-SEAM: the sweep grid is integer-quantized; append the exact
  # configured-threshold result so the interactive map's initial state shows
  # this run rather than the nearest grid cell.
  if _solver_result is not None:
    _increase_ids = (
      [int(v) for v in untreatable_sdyd_increase[id_column].tolist()]
      if len(untreatable_sdyd_increase) else []
    )
    _exact_row = {{
      "sdyd_threshold": sdyd_threshold,
      "sddc_threshold": sddc_threshold,
      "model_primary_status": float(status),
      "total_Sddc_reduction": float(total_Sddc_reduction),
      "final_Sddc": float(final_Sddc),
      "total_cost": float(total_cost),
      "total_fixed_cost": float(total_fixed_cost),
      "selected_hillslopes": json.dumps([int(i) for i in selected_hillslopes]),
      "treatment_hillslopes": json.dumps([[int(i) for i in ids] for ids in treatment_hillslopes]),
      "untreatable_ids": json.dumps([int(v) for v in untreatable_sdyd[id_column].tolist()] if id_column in untreatable_sdyd.columns else []),
      "hillslopes_sdyd": json.dumps([[int(i), float(v)] for i, v in hillslopes_sdyd]),
      "untreatable_sdyd_increase": json.dumps(_increase_ids),
    }}
    _dupe = (
      (interactive_df["sdyd_threshold"] == sdyd_threshold)
      & (interactive_df["sddc_threshold"] == sddc_threshold)
    )
    interactive_df = pd.concat(
      [interactive_df.loc[~_dupe], pd.DataFrame([_exact_row])], ignore_index=True
    ).sort_values(["sdyd_threshold", "sddc_threshold"]).reset_index(drop=True)

  interactive_df.to_csv(generated_threshold_csv_path, index=False)
  interactive_csv_text = interactive_df.to_csv(index=False)
  interactive_config["csvText"] = interactive_csv_text
  interactive_config["csvUrl"] = None
  interactive_config["treatmentLabels"] = list(treatments)
  interactive_config["hasInteractiveData"] = interactive_hillslopes_data is not None and has_threshold_analysis
  display(HTML(f"<script>window.PATH_REPORT_CONFIG = {{_script_json(interactive_config)}};</script>"))
```
"""

out = "\n".join(
    [
        FRONTMATTER,
        prose.rstrip() + "\n",
        HEAD_LOADER,
        IMPORTS_CELL,
        PARAMS_CELL,
        SOLVE_SWEEP_CELL,
        tail,
    ]
)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(out)
print(f"wrote {OUT} ({len(out.splitlines())} lines)")
