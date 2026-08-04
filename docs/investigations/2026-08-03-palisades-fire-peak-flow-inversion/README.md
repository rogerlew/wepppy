# Palisades Fire 2024 — Peak-Flow Analysis (WEPPcloud)

This dated directory is the canonical WEPPpy-owned home of the investigation.
It was migrated from the former standalone `/workdir/palisades-fire-investigation`
repository on 2026-08-03 Pacific time; nested Git metadata was intentionally
removed.

This repo contains scripts + a LaTeX report for analyzing **peak flow / return-interval behavior** in WEPPcloud run `upset-reckoning`, including:
- burned (base) vs undisturbed comparisons
- sub-daily channel-hydrograph “desynchronization” diagnostics
- homogeneous (omni) scenario controls (`uniform_moderate`, `uniform_high`)

Intermediate artifacts under `tmp_*` are intentionally kept.

## Four-cell ET attribution

The follow-up [burned/undisturbed by PMET/legacy experiment](artifacts/four-cell-et/results.md)
ran all 278 hillslopes in each of four cells. PMET materially changes `Es`/ET
partitioning, but it does not dry burned profiles or suppress burned runoff;
the runoff interaction is slightly opposite the inversion hypothesis. The
peak inversion remains a runoff-timing and routing problem.

## Python environment (uv)

- Create/sync the virtualenv: `uv sync`
- Run scripts with the venv Python, e.g.: `.venv/bin/python skills/weppcloud-agent/scripts/desynchronization_analysis.py --help`

## Build the report

- Build: `latexmk -pdf -interaction=nonstopmode -halt-on-error report_upset_reckoning_hydroshape.tex`

## Handoff

See `AGENTS.md` for the full “where we left off” notes, key scripts, and reproduction commands.
