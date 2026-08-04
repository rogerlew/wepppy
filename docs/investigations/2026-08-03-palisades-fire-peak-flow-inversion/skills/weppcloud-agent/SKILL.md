---
name: weppcloud-agent
description: Help WEPPcloud users set up and run projects, understand and interpret WEPP results (runoff, sediment delivery, peak flows, water balance), compare scenarios, and draft a clear technical report. Use when a user shares a WEPPcloud run link or run ID and asks what the outputs mean, how to download/organize results, how to summarize findings, or how to write a report based on WEPPcloud results.
---

# Weppcloud Agent

## Workflow (use this order)

### 0) Ask for the minimum inputs
- Run link(s): ask the user to paste the WEPPcloud URL(s) from their browser (preferred) or the run ID(s).
- Goal: what decision question the run supports (risk, treatment comparison, post-fire response, etc.).
- Scenario set: what differs between runs (climate period, land use/management, disturbance severity, treatments).
- Deliverable: quick explanation, a comparison table, or a full narrative report.

If any critical context is missing (area, time window, scenario differences), ask 1–2 targeted questions and proceed with a provisional interpretation.

### 1) Help them run the project (WEPPcloud web app)
Keep this user-facing and UI-agnostic:
- Confirm the project/scenario inputs align with the user’s goal (AOI, soils/landcover/management, climate source + period, any disturbance/treatment layers).
- Suggest a minimal scenario matrix when comparing (change one thing at a time; keep everything else fixed).
- When a run fails or stalls: collect the visible error, where it occurs (step/page), and any downloadable logs/diagnostics the UI exposes.

See `references/user-workflows.md`.

### 2) Pull results into a “working set”
Ask the user to download/export the key artifacts WEPPcloud provides (tables + maps) and point you to them (upload, paste snippets, or describe where they are in the UI).

Minimum recommended working set for interpretation:
- A small set of summary tables (outlet delivery, water balance, event extremes if relevant).
- A note of the modeled area (for unit normalization).
- If comparing scenarios: the same artifacts for each run.

See `references/outputs-and-units.md`.

### 3) Summarize + interpret (be explicit about units and basis)
When explaining results, always state:
- **Where** (outlet vs hillslope vs channel; whole watershed vs subareas).
- **When** (time window; annual average vs event-based).
- **Units** and **area basis** (mm vs volume; kg/ha vs tonnes).

Use `references/comparison-checklist.md` when comparing scenarios.

### 4) Draft the report
Use `assets/report-outline.md` as the default structure. Populate with:
- “What changed between scenarios”
- “What changed in outputs” (tables/figures)
- “So what” interpretation (implications, tradeoffs, uncertainties)

Always include:
- Exact run links/IDs
- Inputs summary (what the run represents)
- Key metrics with units and definitions

## Return periods (peak flow)
If the user asks about short return periods (2/5/10-year) and wants event-date comparisons, request the event-by-event export (`ebe_pw0.txt`) for each scenario and run:
- `scripts/return_period_compare.py --burned-ebe <path> --undisturbed-ebe <path> --start-year <yyyy>`

This produces CSV tables (CTA + AM) plus an overlay histogram of peak discharge events.

## Operator-only notes (do not assume available)
If (and only if) the user is an internal operator with filesystem or stack access, the following references describe backend-level resolution and report tooling:
- `references/operator-wctl-workflows.md`
- `references/operator-run-directory-layout.md`
- `references/operator-wepppy-reports.md`
- `references/operator-weppcloudr-rendering.md`

## Conventions (keep responses actionable)
- Always state the run link/ID(s) you are interpreting.
- When comparing runs, normalize: units, time window (water years), and area basis (mm vs volume; kg/ha vs tonnes).
- Prefer exporting intermediate tables (CSV) alongside the narrative so results are reproducible.
- Only mention a filesystem `run_dir` when you actually have backend access.
