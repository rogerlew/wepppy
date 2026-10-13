# EDDE v2 research client usage

Run from the repository root with the existing virtualenv. No AWS account or new dependency is needed. This is an experimental research client; see the [durable contract](../../../schemas/edde-v2-experimental-client-contract.md) before interpreting generated climate.

## Query a point

Use a new output directory each time. The default variables are daily precipitation and air-temperature extrema; values in `daily.csv` retain published units (mm-equivalent precipitation and Kelvin temperatures).

```bash
/workdir/wepppy/.venv/bin/python -m wepppy.climates.edde query \
  --model WRF-MPI --scenario SSP2-4.5 \
  --start 2060-01-01 --end 2060-12-31 \
  --point Calgary,-114.07,51.05 --point Vancouver,-123.12,49.28 \
  --cache /tmp/edde-cache --output /tmp/edde-query-2060 \
  --max-download-bytes 4000000000
```

Expect one row per point/day, source object and cell provenance, and byte/timing information. More points share the same monthly acquisition. A one-year three-variable query downloads roughly 1.16 GB cold; actual benchmarks are retained in package artifacts. Warm cache reads reverify hashes. No nearest-land relocation occurs, so some coastal land coordinates fail because their 12 km source cell is ocean.

## Inventory and reproduce studies

```bash
/workdir/wepppy/.venv/bin/python -m wepppy.climates.edde inventory \
  --model WRF-Nor --scenario SSP2-4.5 --year 2079 \
  --cache /tmp/edde-cache --output /tmp/edde-inventory-2079
```

Current inspected availability is MPI historical 1985–2014 and both future scenarios 2025–2099; NorESM historical 1985–2014 and SSP2-4.5 2025–2079. Re-inventory rather than assuming these limits are permanent.

The package's `artifacts/acquire.py`, `reference.py`, `auxiliary_probe.py`, `assess.py`, and `workflows.py` retain the exact study logic. Acquisition takes model/scenario and explicit first/last years and resumes only completed hash-verified point tables. Run each acquisition for the windows listed in `assess.py`; run reference and auxiliary probes, then assessment. Workflow experiments use frozen real-project hillslope fixtures from the prior dewpoint study and write new scratch directories; they do not mutate live projects.

CLIGEN API entry points are `build_climate(table, manifests, station, output, seed=...)` and `revise_prism(source, output, reference, target)` in `wepppy.climates.edde.cligen`. The caller selects the auxiliary station explicitly. Preserve raw query tables/manifests; do not relabel EDDE as observed weather because the underlying CLIGEN function is named `run_observed`.

## Failure and retry

Inspect incomplete manifests, partial download identity, and CLIGEN logs. Resolve the identified request/source/scientific problem; retry in a new output directory. Missing dates, absent scenarios, invalid cells, quality-guard failure, and PRISM temperature inversions are explicit errors. Never repair them by silently changing the cell, replacing weather records, clamping temperature, or selecting another scenario. Cache directories need an operator-selected storage location and enough disk for the explicit query footprint.
