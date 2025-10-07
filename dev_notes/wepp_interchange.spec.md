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
- **Performance**: streaming readers with a fan-out pool feeding a single Arrow writer per Parquet target. Avoid loading entire directories into memory at once.
- **Idempotence**: rerunning interchange should refresh Parquet targets safely (temp file + replace) without requiring a clean output directory.
- **Configurability**: allow callers to scope processing to selected hillslopes or file patterns for large projects.
- **Validation hooks**: expose lightweight data sanity checks (row counts per source file, non-null gauges, optional hash) to support regression test harnesses.

## Processing Pipeline Expectations
1. Discover raw hill files beneath `wepp/output` (glob `H*.{ebe,element,pass,loss,soil,wat}.dat`).
2. Dispatch file readers in a worker pool. Workers parse raw text to Arrow RecordBatches (schema-specific) while adding normalized identifiers.
3. Aggregate worker output via a thread-safe queue feeding a dedicated writer task that appends to `pyarrow.parquet.ParquetWriter`.
4. Each Parquet file is written once per run (single writer instance). Temporary output path (`.tmp`) renamed atomically on success.
5. Emit optional JSON manifest that records source file mtimes, row counts, schema version for auditability (future phase).

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
The legacy parsers live under `wepppy/wepp/out/` and act as data brokers for other services.

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
- Both `TotalWatSed2` classes read Parquet today but still instantiate `HillPass` / `HillWat` when caches miss.

## Test Assets
- Mini project for unit tests: `tests/wepp/interchange/test_project/output/`. Contains representative hill files (`H1`, `H2`) plus watershed loss parquet snapshots for regression comparisons.
- Use this dataset to validate new interchange writers and to backfill tests for legacy parity (e.g., cross-check `TotalWatSed2` metrics).

## Open Questions / To Refine
- Do we version schemas via Arrow metadata (e.g., `schema_version=1`)?
- How do we expose snow/ash augmentation in interchange (embed extra columns or separate Parquet)?
- What is the retention policy for the raw `wepp/output` folder once interchange completes—delete automatically or gated by config?
- Confirm concurrency limits that play nicely with HPC environments (default worker count vs CPU detection).

