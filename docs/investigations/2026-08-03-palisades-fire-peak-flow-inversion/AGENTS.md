# Palisades Fire 2024 — Peak-Flow Analysis (WEPPcloud)
## What this repo is
This repository contains a **reproducible analysis workflow** (scripts + LaTeX report + intermediate artifacts) for diagnosing **peak-flow / return-interval behavior** in a WEPPcloud run, with emphasis on the Palisades Fire (2024) case study.

It started life as an “AI agent skill” sandbox; it has since **morphed into an analysis repo** and keeps intermediate outputs intentionally.

## Key run + scenarios
- **WEPPcloud runid:** `upset-reckoning`
- **Query Engine base URL:** `https://wc.bearhive.duckdns.org/query-engine`
- **Scenario conventions in scripts:**
  - **Burned / baseline** = *base scenario* (Query Engine payload **omits** `"scenario"`).
  - **Undisturbed** = `"scenario": "undisturbed"`.
  - **Homogeneous (omni) scenarios** used for “controlled experiments”:
    - `"scenario": "uniform_moderate"`
    - `"scenario": "uniform_high"`

## Repo layout (important paths)
- **Main report (source):** `report_upset_reckoning_hydroshape.tex`
- **Main report (compiled):** `report_upset_reckoning_hydroshape.pdf`
- **Analysis scripts:** `skills/weppcloud-agent/scripts/`
- **Intermediate outputs (committed):**
  - `tmp_upset_reckoning_scope/` (CTA scope tables derived from `chan.out`)
  - `tmp_upset_reckoning_hydroshape/` (event-scale diagnostics + rank plots)
  - `tmp_upset_reckoning_root_cause/` (process-of-elimination proxy diagnostics)
  - `tmp_upset_reckoning_desync/` (5‑minute channel hydrograph overlays + metrics)
  - `tmp_upset_reckoning_omni_homog/` (homogeneous severity scenario comparisons)
  - `tmp_upset_reckoning_landuse_peakflow/`, `tmp_upset_reckoning_man_compare/`, etc.

## Environment + secrets
- Python: `>=3.12,<3.13` (see `pyproject.toml`)
- Dependency manager: `uv` (see `uv.lock`)
- Local token: create a local `.env` (NOT committed) containing:
  - `WEPPCLOUD_JWT_TOKEN=...` (only needed for WEPPcloud UI endpoints; Query Engine analysis typically works without it)

## Reproduce the analysis (canonical)
From repo root:

1) Sync environment
```bash
uv sync
```

2) Regenerate the burned-vs-undisturbed CTA tables used in the **Scope** section
```bash
.venv/bin/python skills/weppcloud-agent/scripts/cta_scope_tables.py \
  --runid upset-reckoning --undisturbed-scenario undisturbed \
  --outlet-topaz-id 24 --recurrence 2,5,10 \
  --out-dir tmp_upset_reckoning_scope \
  --base-url https://wc.bearhive.duckdns.org/query-engine
```

3) Regenerate the homogeneous omni scenario comparison section (undisturbed vs uniform moderate vs uniform high)
```bash
.venv/bin/python skills/weppcloud-agent/scripts/omni_homogeneous_flashiness.py \
  --runid upset-reckoning \
  --out-dir tmp_upset_reckoning_omni_homog \
  --scenarios undisturbed,uniform_moderate,uniform_high \
  --recurrence 2,5,10 --top-n 100 \
  --base-url https://wc.bearhive.duckdns.org/query-engine
```

4) (Optional) Regenerate 5‑minute desynchronization diagnostics (requires the run to have been re-run with `dtchr=300`, `ichout=3` for instrumented channel IDs)
```bash
.venv/bin/python skills/weppcloud-agent/scripts/desynchronization_analysis.py \
  --runid upset-reckoning --undisturbed-scenario undisturbed --top-n 30 \
  --topaz-ids "604 324 24" --outlet-topaz-id 24 \
  --out-dir tmp_upset_reckoning_desync \
  --base-url https://wc.bearhive.duckdns.org/query-engine
```

5) Build the PDF
```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error report_upset_reckoning_hydroshape.tex
```

## What we believe is happening (current state)
The “undisturbed peak > burned peak at similar/lower volume” pattern is supported by:
- event-scale proxies (`T_eff = V/Qp`, `Qp/V`) and
- **definitive 5‑minute routed hydrographs** showing **burned outlet hydrographs are broader** (larger `width50`), while undisturbed hydrographs are sharper.

Working hypothesis:
- burned scenario introduces **spatial heterogeneity** (mixed severities / landuse responses) that **desynchronizes** tributary contributions and increases dispersion/attenuation at the outlet;
- undisturbed is more spatially homogeneous, producing more synchronized arrivals and a sharper outlet peak.

## Next steps (if continuing)
- Instrument a **denser set of channel IDs** with `ichout=3`, `dtchr=300` and compute a true “tributary synchrony index” at the outlet peak.
- Add PASS-based per-event spatial-heterogeneity metrics (variance across disturbed classes/landuse in a flashiness proxy) and test whether heterogeneity is systematically higher in burned on flagged events.
