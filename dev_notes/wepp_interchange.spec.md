# WEPP Hillslope Interchange (Draft Spec)

## Motivation
- Replace ad-hoc parsing of WEPP flat files with durable, columnar interchange artifacts that downstream analytics can query uniformly.
- Reduce filesystem load by allowing post-processing tools to depend on a compact `wepp/interchange` directory instead of the raw `wepp/output` tree.
- Provide well-defined schemas with stable typing so DuckDB / Arrow clients can be used without custom adapters.

## Scope (Phase 1)
- Hillslope-level products emitted by classic WEPP runs: `H*.ebe.dat`, `H*.element.dat`, `H*.pass.dat`, `H*.loss.dat`, `H*.soil.dat`, `H*.wat.dat`.
- Generate a single Parquet file per product type inside `wepp/interchange/` for each project run:
  - `H.ebe.parquet`
  - `H.element.parquet`
  - `H.pass.parquet`
  - `H.loss.parquet`
  - `H.soil.parquet`
  - `H.wat.parquet`
- Target watershed (pw0) interchange deliverables in a follow-up scope.
- Plot-level hillslope outputs are explicitly out-of-scope for the interchange.

## Key Requirements
- **Canonical IDs**: include `wepp_id` (hillslope integer), `ofe_id` (when applicable), and a unified date bundle: `year`, `month`, `day`, `julian`, `water_year`.
- **Schema discipline**: define Arrow schemas up-front, including units metadata attributes where practical. Use column names from existing data files to avoid confusion
- **Field naming**: preserve the legacy WEPP labels (e.g., `Runoff (m^3)`, `Sed Del (kg)`) so hydrologists can match terminology across WEPP and WEPPCloud surfaces.
- **Parser ergonomics**: when porting the text files, reuse the Fortran variable names from the originating module (e.g., `wshpas.for`) for local variables and column mapping to improve traceability.
- **Performance**: streaming readers with a fan-out pool feeding a single Arrow writer per Parquet target. Avoid loading entire directories into memory at once, but performance is more important than memory.
- **Idempotence**: not a requirement. initiating wepp run will intentionally wipe `interchange` dir. 
- **Source of truth philosophy transition**: source of truth is moving from WEPP flat file outputs to interchange parquet files. Long term goal is to be able to delete `wepp/output` after interchange. Along the way to this goal we will move from 0. do nothing. 1. tar archive output 2. delete after interchange.
- **Validation hooks**: expose lightweight data sanity checks (row counts per source file, non-null gauges, optional hash) to support regression test harnesses.

## Processing Pipeline Expectations
1. Discover raw hill files beneath `wepp/output` (glob `H*.{ebe,element,pass,loss,soil,wat}.dat`).
2. Dispatch file readers in a worker pool. Workers parse raw text to Arrow RecordBatches (schema-specific) while adding normalized identifiers.
3. Aggregate worker output via a thread-safe queue feeding a dedicated writer task that appends to `pyarrow.parquet.ParquetWriter`.
4. Each Parquet file is written once per run (single writer instance). Temporary output path (`.tmp`) in `/dev/shm` renamed atomically on success. We don't care about cross-platform support.
5. Each project will standup a DataManager(NoDbBase) singleton for logging and auditability.

## H.pass.parquet Notes
- Normalize `EVENT`, `SUBEVENT`, and `NO EVENT` records into a single tabular schema; populate unavailable metrics with zeros so downstream aggregations stay straightforward.
- PASS header metadata (climate file ids, simulation year spans, particle diameter arrays, support practice coefficients) is not required in the Parquet output for the initial delivery.
- Always emit the five sediment class delivery columns; WEPP fixes `npart = 5`, so dynamic column handling is unnecessary.
- Trust WEPP’s Julian dates; leap days are already accounted for and no timezone adjustments are needed when deriving calendar breakdowns.
- Additional run identifiers (project slug, scenario ids, etc.) can be layered on later once the core interchange architecture is proven; keep the initial schema minimal.
- Validation will center on confirming that the interchange-backed `TotalWatSed` reproduction matches trusted baselines; legacy `HillPass` parity is informative but not necessary.
- Operational wiring (CLI flags, run hooks) will be tackled separately—focus here on writer accuracy and performance characteristics.

## Source of Truth (WEPP Core Code)
| Output | WEPP Source File | Notes |
| ------ | ---------------- | ----- |
| `H*.ebe.dat` (Event output) | `wepp-forest/src/outfil.for` lines ~260-340 (unit 30, format 2100) | Controlled by `useout('event by event')`, prints per-storm summary. |
| `H*.element.dat` | `wepp-forest/src/outfil.for` lines ~310-330 (unit 33, format 2300) | Variable OFE line summary output. |
| `H*.loss.dat` | `wepp-forest/src/outfil.for` lines ~140-210 (formats 1200-1500) | Abbreviated annual loss summaries; includes sediment class table. |
| `H*.soil.dat` | `wepp-forest/src/outfil.for` lines ~200-250 (unit 39, format 1900) | Daily soil property output per OFE. |
| `H*.wat.dat` | `wepp-forest/src/outfil.for` lines ~180-220 (units 35/36/39/40 etc., format 1400/1401) | Daily water balance output. |
| `H*.pass.dat` | `wepp-forest/src/wshpas.for` lines ~110-210 | PASS file written when runoff occurs; header written when year==ibyear & day==1. |

(Referenced line numbers are approximate offsets from current source snapshot.)

## Existing Parsers & Downstream Dependencies
The legacy parsers live under `wepppy/wepp/out/` and act as data brokers for other services. These will be deprecated. Core parsing needs to be retained in interchange with no dependency on `wepppy.wepp.out`

### `H*.ebe.dat`
- Parser: `HillslopeEbe` (`wepp/out/ebe.py`). Converts to Pandas then Parquet with schema metadata.
- Downstream: minimal direct use today (mostly manual inspection). Verify none of the cloud routes import it yet.

### `H*.element.dat`
- Parser: `Element` dictionary builder (`wepp/out/element.py`).
- Downstream: referenced in `tests/test_1_wepp_out.py`; imported by `weppcloud/routes/nodb_api/watar_bp.py` (for API responses) and ash transport tests.

### `H*.pass.dat`
- Parser: `HillPass` (`wepp/out/hill_pass.py`).
- Downstream: `TotalWatSed2` (`wepp/out/totalwatsed.py`), disturbed variant, and external hydrology workflows rely on `sed_df`. Any change must keep the sediment class columns accessible. 


### `H*.loss.dat`
- Parsers: `HillLoss` (`wepp/out/hill_loss.py`) plus helper `_parse_tbl` in `loss.py`.
- Downstream: limited (particle size fractions, annual summary). Inventory consumers when migrating (look for `HillLoss` imports).

### `H*.soil.dat`
- Parser: `HillSoil` (`wepp/out/hill_soil.py`) — currently incomplete and lightly used.
- Downstream: no active imports located; safe to treat as new surface but confirm with stakeholders before removal.

### `H*.wat.dat`
- Parser: `HillWat` (`wepp/out/hill_wat.py`). Produces 3D arrays, daily reshape, water balance calculators.
- Downstream: heavy usage:
  - `TotalWatSed2` (`wepp/out/totalwatsed.py`)
  - Watershed stats (`wepp/stats/hillslope_watbal.py`)
  - Ash transport models (`nodb/mods/ash_transport/*.py`)
  - Cloud APIs (`weppcloud/routes/nodb_api/*.py`)
- Replacement interchange must expose equivalent metrics (mm + m³ translations) with consistent naming so these tools can port over.

### Aggregated Tools
- `TotalWatSed2` mixes PASS, WAT, and optional ash products to compute daily streamflow and sediment metrics; acts as regression anchor (compare Parquet outputs before/after interchange refactor).
  - `TotalWatSed` aggregates daily data from across hillslopes from hill sed, wat, and pass outputs. Should be trivial to replicate once interchange is functional.
- Both `TotalWatSed2` classes read Parquet today but still instantiate `HillPass` / `HillWat` when caches miss for legacy projects.
  - legacy projects should force interchange

## Test Assets
- Mini project for unit tests: `tests/wepp/interchange/test_project/output/`. Contains representative hill files (`H1`, `H2`) plus watershed loss parquet snapshots for regression comparisons.
- Use this dataset to validate new interchange writers and to backfill tests for legacy parity (e.g., cross-check `TotalWatSed2` metrics).

## Open Questions / To Refine
- Do we version schemas via Arrow metadata (e.g., `schema_version=1`)? : yes
- How do we expose snow/ash augmentation in interchange (embed extra columns or separate Parquet)? : separate
- What is the retention policy for the raw `wepp/output` folder once interchange completes—delete automatically or gated by config? : delete on wepp run
- Confirm concurrency limits that play nicely with HPC environments (default worker count vs CPU detection). : CPU/manual tuning for now

# Developer Log
- 2025-02-14: Implemented `run_wepp_hillslope_pass_interchange` producing `H.pass.parquet` with Fortran-aligned field names, Julian-to-calendar enrichments, and zero-filling per event type. Added coverage at `tests/wepp/interchange/test_pass_interchange.py` and refreshed spec guidance for PASS outputs.
