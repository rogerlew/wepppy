# Omni hillslope response summaries

Read-only production snapshot, 2026-09-21 UTC, host `wepp1`.
No project state, inputs, outputs or jobs were changed.

- Rithet Creek: `choice-feminist`, 455 hillslopes, 22 averaging years.
- Judge: `aliquot-shoji`, 167 hillslopes, 21 averaging years.
- Each CSV contains the base SBS run followed by all seven configured Omni
  scenarios. All saved executable selections are `wepp_260803`; this is not
  independent binary provenance verification.

The 66 columns and their order exactly match
[the reference CSV](../../work-packages/20260917_mofe_scenario_artifact_integrity/artifacts/mofe-production-hillslope-response-summary.csv).
Calculations match its `summarize_production.py`: annual hillslope runoff volume
divided by area in hectares times 10 gives runoff depth in mm/year; kilograms
are divided by 1,000 for tonnes. Quantiles use pandas linear interpolation;
standard deviation is the sample statistic (`ddof=1`). Distribution statistics
are unweighted across hillslopes; the explicitly area-weighted runoff field is
total volume divided by total area times 10. Sediment yield and soil loss are
distinct source fields, not interchangeable. Totals describe hillslopes, not
watershed-outlet delivery.

[summarize.py](summarize.py) reads `loss_pw0.hill.parquet` from the base and each
`_pups/omni/scenarios` directory over SSH. It verifies the configured scenario
set, unique expected hillslope IDs, positive and identical areas across
scenarios, finite/nonnegative responses and consistent averaging years within
each project. Separate `.sources.json` files retain definitions, source paths,
SHA-256 hashes, modification times and retrieval times without adding columns
to the requested CSVs. No causal or parameterization-equivalence audit is claimed.

Judge's reported moderate-severity sediment yield is 428.0105 tonnes/year,
slightly below low severity at 445.5765 tonnes/year; values are retained without
rank adjustment. The original historical reference CSV was not modified.

Reproduce from the repository root:

```bash
.venv/bin/python docs/investigations/20260921_omni_hillslope_response/summarize.py
```

This refreshes the local CSVs/provenance from current production artifacts;
source runs remain read-only.
