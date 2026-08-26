# Phase 2A Pilot Artifacts

This directory holds compact, reviewable evidence for the completed Topanga
multi-hillslope pilot. Large event, routing, and hydrograph datasets remain
outside Git and are referenced through typed artifact-storage manifests.

Expected committed artifacts include the frozen pilot-selection manifest,
scenario and mutation manifests, schema versions, routing-closure validation,
candidate adjudication summaries, storage/runtime projection, and the final
ten-criterion exit report.

## Evidence Map

| Artifact | Evidence |
| --- | --- |
| `scenario-manifest.json`, `pilot-selection.json` | Frozen inputs, observer, and eight-hillslope preregistration |
| `selected-baseline-inventory.csv` | Selected soil, cover, topography, solver, and surface-return strata |
| `mutation-terminal-summary.json`, `candidate-events.csv` | Complete 64-trial ledger and protocol candidate screen |
| `event-packets/`, `replay-reports/` | Real no-surplus and known-positive frozen replay |
| `candidate-adjudication.json` | Adaptive bracket, mechanism, and incomplete-HDRIVE dispositions |
| `routing-trial-validation.csv`, `routing-validation-summary.json` | All-channel closure, timestamp, and flow checks |
| `artifact-storage-*.json` | External locators, byte counts, SHA-256 hashes, formats, and retention |
| `h106-1986-day046-hydrograph.csv`, `h106-1986-day046-volume-check.csv` | Known-positive 600-second series and daily volume comparison |
| `storage-runtime-projection.json` | Measured pilot and projected 1,120-trial cost |
| `phase2a-exit-report.json`, `phase2a-exit-report.md` | Ten-criterion disposition |
| `study-design-amendment-local-census.md` | Post-pilot decision to cull routing from the local census gate |
| `schemas/` | Additive Phase 2A JSON Schema contracts |

External evidence is rooted at
`/home/workdir/peakflow-phase2a-evidence/8162d509d69cb4da`. The storage
manifests record locators, hashes, sizes, formats, and retention status.

Regenerate the external routing inventory from the retained evidence and then
verify every recorded byte count and SHA-256 hash with:

```bash
.venv/bin/python tools/peakflow_phase2a_pilot.py storage
.venv/bin/python tools/peakflow_phase2a_pilot.py --verify-external validate
```

`adjudicate` also requires an explicit `--replay-binary` built under the
accepted Phase 1 procedure; the CLI deliberately has no temporary-path
fallback.

## Disposition

Seven automatic criteria pass. Criteria 5–7 fail because one-target mutations
change sibling-channel routing and interval discharge does not integrate to
the daily authoritative volume. The original routing-coupled census remains
withheld. The subsequent design amendment releases a hillslope-only local
census and forbids downstream-impact claims.
