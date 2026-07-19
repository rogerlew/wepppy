# WATAR Integration Plan

**Project:** NASA ROSES Utility Watersheds

**Batch:** `nasa-roses-202606-psbs`

**Status:** Draft; blocked on MOFE runoff integration and Alex's approved parameters

**Last updated:** July 18, 2026

## Purpose

Integrate the Alex/Watanabe WATAR model with the Oregon and Washington NASA
ROSES utility-watershed batch, validate the integration on a small set of
representative watersheds, and then run WATAR across every eligible batch run.

This plan records the modeling request from Mariana, the multi-OFE (MOFE)
investigation, the selected parameter-development watersheds, the engineering
work required before calibration, and the operational gates for the full batch.

## Source Request and Working Decisions

Mariana's email summarized the requested workflow:

1. Use the static WATAR formulation exposed by the interface.
2. Continue treating WATAR as a single hillslope reservoir rather than adding
   OFE-by-OFE ash routing.
3. Convert the batch's MOFE water balance into one daily hillslope runoff input
   for WATAR.
4. Give Alex one to three representative watersheds so he can exercise the
   model and recommend default parameters. Include South Fork/Bull Run.
5. After Alex approves the parameters, run WATAR on the complete watershed
   collection.

The following working decisions were made on July 14, 2026:

- Use the Alex/Watanabe model with `transport_mode=static`. Do not rely on the
  implementation default, which is currently `dynamic`.
- Use the full `OR-6` Bull Run batch run as the requested Bull Run
  representative; a separate South Fork delineation is not required for this
  effort.
- Use `OR-60` for fast iteration, `WA-10` for intermediate validation, and
  `OR-6` for the final large-watershed transfer and performance test.
- Do not interpret the current WATAR output from a MOFE run as calibration
  evidence until the runoff aggregation blocker below is resolved. The static
  formulation blocker was resolved and verified on July 18, 2026.

## Current Batch State

Read-only inspection of `wepp1` on July 14, 2026 found:

- Batch root:
  `/geodata/wc1/batch/nasa-roses-202606-psbs/`
- 93 leaf run directories and run metadata records.
- 92 runs classified as successful.
- `WA-77` classified as failed and therefore not currently eligible for WATAR.
- Successful runs use `disturbed9002-wbt-mofe.cfg`, have 39-year climate
  records, and have complete WEPP interchange artifacts.
- The selected runs have `wepp._multi_ofe = true`, an existing SBS raster, and
  no current files in their `ash/` output directories.
- Their `ash.nodb` files currently select `model=multi`; selecting the Alex
  model and static mode must be an explicit, recorded batch input change.
- The batch runner's default task graph does not contain `run_watar`. The
  existing RQ `run_ash_rq` path runs WATAR for one project, but batch-mode input
  submission currently updates settings without enqueueing WATAR jobs.

No production files or job state were changed during the inspection.

## Selected Parameter-Development Watersheds

The metrics below were calculated from the production run artifacts. Area,
slope, and hillslope count came from `watershed/hillslopes.parquet`; OFE metrics
came from `H.wat.parquet` metadata; SBS percentages are raster pixel fractions;
and precipitation/runoff are mean annual sums from the 39-year
`totalwatsed3.parquet` record.

| Run | Source watershed | Area (km²) | Hillslopes | Median slope | Mean OFEs | MOFE hillslopes | SBS unburned/low/moderate/high | Mean annual precipitation/runoff (mm) | `H.wat` size |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| `OR-60` | Cooper Creek | 11.2 | 115 | 0.360 | 3.35 | 79.1% | 1.2% / 30.6% / 54.5% / 13.7% | 1,149 / 207 | 0.08 GiB |
| `WA-10` | Wildwood-Stillman Creek | 50.4 | 543 | 0.399 | 3.10 | 77.3% | 13.0% / 26.6% / 43.1% / 17.3% | 2,286 / 790 | 0.51 GiB |
| `OR-6` | Bull Run | 251.7 | 2,422 | 0.223 | 3.15 | 73.8% | 26.6% / 26.1% / 24.8% / 22.4% | 3,192 / 1,673 | 2.60 GiB |

All three have a maximum of five OFEs per hillslope, but not every hillslope has
five. Code and documentation should therefore say "up to five OFEs" rather
than assuming a fixed five-row layout.

### Recommended use

1. **`OR-60`, Cooper Creek:** implementation smoke test and rapid parameter
   iteration. It is compact, relatively dry, steep, and dominated by moderate
   SBS.
2. **`WA-10`, Wildwood-Stillman Creek:** intermediate transfer test with a
   wetter climate, steep terrain, and substantial moderate/high SBS coverage.
3. **`OR-6`, Bull Run:** required Bull Run representative and final stress
   test. Its 108,518,410 `H.wat` rows make it useful for detecting inefficient
   scans or excessive memory use before batch-wide execution.

## MOFE Investigation

### Current behavior

`Ash.run_ash` runs WATAR once per WEPP hillslope. Before invoking either ash
model it calls:

```python
load_hill_wat_dataframe(wepp.output_dir, wepp_id, collapse="daily")
```

The daily collapse:

- converts every configured millimeter-valued `H.wat` column to volume using
  the row's OFE area;
- sums those volumes across OFEs;
- divides by the sum of OFE areas to recover one daily depth; and
- sets `ofe_id` and `OFE` to zero.

The Alex model therefore receives one synthetic daily record and maintains one
ash reservoir for the entire hillslope. It does not preserve OFE identity,
simulate separate OFE ash stores, or route ash between OFEs. That behavior is
consistent with Mariana's request to retain a one-reservoir WATAR formulation.

### Confirmed runoff problem

Applying the generic area-weighted collapse to `Q` is not valid for MOFE
hillslopes. Each `H.wat.Q` row is cumulative routed runoff at the bottom of that
OFE, normalized by cumulative contributing length. It is not an independent
increment generated by that OFE. Consequently, `SUM(Q * Area)` counts routed
upslope water more than once and does not recover canonical hillslope runoff.

The canonical daily hillslope runoff volume is `H.pass.runvol`. For recent WEPP
outputs, the bottom OFE's `Q` is also the canonical hillslope-average runoff
depth, but `H.pass.runvol` is preferred because it is authoritative across
legacy and current WEPP output versions.

This matters directly to WATAR. The Alex implementation uses daily `Q` to:

- calculate infiltration as `RM - Q`;
- determine whether runoff exceeds ash saturated storage;
- calculate ash-bearing runoff; and
- drive the static or dynamic transport response.

Using the existing collapsed `Q` can therefore change ash consolidation,
decomposition, runoff thresholds, and transported mass.

### Required hillslope-daily input contract

Implement a WATAR-specific MOFE adapter, or extend the interchange loader with
an explicit canonical-runoff mode. The adapter must produce exactly one row per
`wepp_id` and simulation day with the following semantics:

| Field | Required derivation |
|---|---|
| Date keys | Preserve `year`, `sim_day_index`, `julian`, `month`, `day_of_month`, and `water_year`; reject duplicate or missing days. |
| `Area` | Sum the distinct OFE footprint areas for the hillslope-day. |
| `Q` | `1000 * SUM(H.pass.runvol) / hillslope_area_m2`, yielding millimeters. Aggregate `H.pass` by hillslope and day using the established `totalwatsed3` event/subevent handling. |
| `P`, `RM` | OFE-area-weighted daily depths from `H.wat`. |
| Soil-water and snow state | OFE-area-weighted daily values for the fields retained in WATAR output. |
| `ofe_id`, `OFE` | Set to zero only after aggregation, signaling a hillslope-daily record rather than a physical OFE. |

The adapter should select only the fields WATAR consumes or emits. It should
not silently apply the same aggregation rule to cumulative routing fields such
as `Q`, `QOFE`, `UpStrmQ`, or `SubRIn`.

### MOFE regression requirements

Add regression coverage for:

- single-OFE parity with the existing WATAR input;
- synthetic two- and five-OFE hillslopes with analytically known runoff;
- `H.pass` event, subevent, and no-event records grouped to one day;
- exact agreement between `H.pass.runvol / area` and bottom-OFE `Q` for a
  current WEPP fixture;
- an intentionally nonuniform MOFE case demonstrating that area-weighted `Q`
  differs from canonical runoff;
- missing `H.pass`, missing dates, duplicate dates, zero area, and nonfinite
  values failing explicitly; and
- preservation of row order and climate/WAT day alignment.

## Static Alex Model Readiness

The interface exposes Alex `dynamic` and `static` transport modes. The static
mode uses separate white- and black-ash values for:

- initial transport capacity `A` (`initranscap`, tonne ha⁻¹ mm⁻¹); and
- depletion coefficient `B` (`depletcoeff`, mm⁻¹).

The implementation currently defaults Alex instances to `dynamic`, so every
pilot and batch job must explicitly record `transport_mode=static`.

### Resolved static-branch blocker

On 2026-07-18, the requesting maintainer approved the scalar static equation:

`delta_M = (A / B) * [exp(-B * Q_previous) - exp(-B * (Q_previous + delta_Q))]`

Here `Q_previous` is `cum_ash_runoff_mm[i - 1]` and `delta_Q` is the current
`ash_runoff_mm[i]`. This replaces the invalid `cum_ash_runoff_mm[:i]` array
expression and fixes its sign and parenthesis convention. Units and decision
provenance are recorded in
`docs/adrs/ADR-0022-alex-static-ash-transport-increment.md`.

Regression coverage includes zero runoff, first and later runoff increments,
nonnegative and monotonically depleted transport, clipping to available ash,
full mass balance, and independence from dynamic-only slope, organic-matter,
and beta coefficients. The output schema is unchanged.

Forest RQ job `b8f5d3ee-e45a-48fd-874e-3c3d839ed807` verified the repaired path
against a local clone of production run `curable-program`. The job completed
through rq-engine and the RQ worker in 59.1 seconds, producing 106 hillslope
parquet files and five post-processing parquet datasets. Across 603,930
hillslope rows, the maximum equation error was `4.88e-15`, the minimum raw
transport was zero, and the maximum ash mass-balance error was `1.64e-14`
tonne ha⁻¹.

## Parameter Package Requested from Alex

Alex's recommendation should be captured in a versioned, machine-readable
manifest rather than transferred only by email. At minimum it must contain:

- model identifier and formulation version;
- `transport_mode=static`;
- the approved static equation or a reference to it;
- white- and black-ash `initranscap` and `depletcoeff`;
- initial/final bulk density, bulk-density factor, particle density,
  decomposition factor, and roughness limit for each ash type;
- field bulk densities used to convert depth and load;
- initial white- and black-ash depth or load assumptions;
- fire date or the rule used to choose it;
- whether wind transport is enabled;
- the ash-type rule for low, moderate, and high SBS; and
- parameter provenance, units, valid ranges, and the date/author of approval.

Current code-seeded values such as `initranscap=0.8` and
`depletcoeff=0.009` are not approved batch defaults until Alex confirms them.

The package also needs an acceptance criterion. If no observed ash-transport
measurements are used, describe the exercise as expert parameter selection and
sensitivity testing rather than statistical calibration.

## Implementation and Execution Plan

### Phase 1: Repair and verify the model inputs

1. Implement canonical hillslope runoff for MOFE WATAR inputs using
   `H.pass.runvol`.
2. Repair the static Alex formula from Alex's specification.
3. Keep existing output column names and units unless a separately approved
   schema change is required.
4. Add focused unit and integration tests, including the MOFE cases above.
5. Run the ash/WATAR tests, interchange tests, stub checks, and the full WEPPpy
   test gate before production use.

### Phase 2: Build a reproducible parameter handoff

1. Add the approved parameter manifest and ADR to the repository.
2. Add a validated loader that applies the manifest to `ash.nodb` without
   relying on manual per-run edits.
3. Record a deterministic parameter-manifest fingerprint in each WATAR run's
   metadata or output manifest.
4. Make a changed parameter fingerprint invalidate WATAR and downstream ash
   summaries, but not upstream DEM, land use, soils, climate, or WEPP results.

### Phase 3: Pilot the selected watersheds

Run in this order:

1. `OR-60`
2. `WA-10`
3. `OR-6`

For each pilot:

- retain the existing 39-year climate and WEPP results;
- apply the same approved parameter manifest;
- run static Alex WATAR with an explicit wind-transport setting;
- confirm one hillslope output for every eligible burned hillslope;
- run `AshPost` and refresh `totalwatsed3.parquet`;
- verify ash mass balance and nonnegative daily/cumulative values;
- compare canonical runoff supplied to WATAR against `H.pass.runvol` for a
  sample of one-, two-, and five-OFE hillslopes;
- inspect black/white and SBS-stratified summaries; and
- record runtime, peak memory, output size, warnings, and failed hillslopes.

Alex and Mariana should approve the pilot results and final manifest before the
full batch is scheduled.

### Phase 4: Add batch WATAR orchestration

The existing batch runner does not schedule WATAR. Add a resumable batch task
rather than manually invoking 92 leaf runs.

The orchestrator should:

- add `TaskEnum.run_watar` as an optional batch directive with documented
  dependencies on successful climate, WEPP hillslope, and WEPP watershed work;
- apply the approved ash parameter manifest to each eligible run;
- enqueue `run_ash_rq` jobs on the batch queue, largest watersheds first;
- cap concurrency based on pilot memory and I/O measurements;
- skip a run only when its WATAR completion marker, expected artifacts, model
  version, and parameter fingerprint all match;
- requeue failed or incomplete leaf jobs without deleting successful WATAR
  outputs;
- link leaf jobs to the batch finalizer and expose progress in batch metadata;
- refresh ash post-processing, query-engine catalogs, and
  `totalwatsed3.parquet`; and
- update `wepppy/rq/job-dependencies-catalog.md` and pass
  `wctl check-rq-graph` when the queue wiring is added.

### Phase 5: Execute and validate the full batch

Before enqueueing:

1. Decide whether to repair `WA-77` or record it as an explicit exclusion.
2. Confirm the batch queue has adequate capacity and no conflicting production
   work.
3. Freeze the code revision, model version, parameter manifest, fire-date rule,
   wind setting, and eligible-run list.
4. Estimate storage from the three pilots and verify available capacity.

After completion:

- reconcile eligible, completed, failed, skipped, and excluded counts;
- verify every completed run has its parameter fingerprint and versioned ash
  manifest;
- query batch-wide ash transport by watershed, SBS class, ash type, year, and
  return period;
- spot-check `OR-60`, `WA-10`, and `OR-6` against their approved pilot outputs;
- publish a machine-readable failure/retry inventory; and
- update the NASA ROSES summary documentation with the final run count,
  parameters, exclusions, and output location.

## Risks and Controls

| Risk | Control |
|---|---|
| Noncanonical MOFE runoff biases WATAR | Gate all tuning and batch work on the `H.pass.runvol` adapter and analytical regression tests. |
| Static equation regresses or is misinterpreted | Preserve ADR-0022, exact vectors, model-loop regression tests, and cloned-run RQ evidence. |
| Parameter drift between pilots and batch | Use one versioned manifest and persist its fingerprint with every run. |
| Repeated scans of multi-gigabyte interchange files overload NFS | Use predicate pushdown or a one-pass materialized hillslope-daily input; benchmark with `OR-6`. |
| Batch retry overwrites good results | Make orchestration artifact- and fingerprint-aware and retry only failed/incomplete leaves. |
| Expert-selected parameters are presented as calibrated | Record the evidence and acceptance criterion; use “calibrated” only when supported by observations. |
| One failed upstream watershed is silently omitted | Resolve or explicitly exclude `WA-77` before finalizing the eligible-run count. |

## Definition of Done

WATAR integration is complete when:

- the static equation and parameters are approved and versioned;
- the parameterization ADR is accepted;
- MOFE runoff uses canonical daily `H.pass.runvol` and passes regression tests;
- static mode passes Alex's test vectors and ash mass-balance tests;
- all three pilots are reviewed and accepted;
- batch orchestration is resumable, observable, and dependency-cataloged;
- every eligible watershed has complete, versioned WATAR and AshPost outputs;
- failures and exclusions are reconciled explicitly; and
- final parameters, code revision, run counts, and artifact locations are
  documented in the NASA ROSES project summary.

## Repository References

- WATAR controller: `wepppy/nodb/mods/ash_transport/ash.py`
- Alex model: `wepppy/nodb/mods/ash_transport/ash_multi_year_model_alex.py`
- MOFE daily loader: `wepppy/wepp/interchange/hill_wat_interchange.py`
- Canonical runoff semantics: `wepppy/wepp/interchange/README.md`, section
  “H.wat Multi-OFE Schema Semantics”
- Daily `H.pass` aggregation precedent:
  `wepppy/wepp/interchange/totalwatsed3.py`
- Single-run RQ path: `wepppy/rq/project_rq.py::run_ash_rq`
- RQ-engine WATAR endpoint: `wepppy/microservices/rq_engine/ash_routes.py`
- Batch runner: `wepppy/nodb/batch_runner.py` and `wepppy/rq/batch_rq.py`
- Parameterization ADR standard:
  `docs/standards/parameterization-adr-standard.md`
