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
- Implementation presently lives under `wepppy/wepp/interchange/hill_*.py` with `run_wepp_hillslope_interchange` orchestrating the per-product writers. The pass runner (`hill_pass_interchange.py`) hydrates the other artifacts to keep existing call sites working during the transition.
- Target watershed (pw0) interchange deliverables in a follow-up scope.
- Plot-level hillslope outputs are explicitly out-of-scope for the interchange.

## Key Requirements
- **Canonical IDs**: include `wepp_id` (hillslope integer), `ofe_id` (when applicable), and a unified date bundle: `year`, `month`, `day`, `julian`, `water_year`.
- **Schema discipline**: define Arrow schemas up-front, including units metadata attributes where practical. Use column names from existing data files to avoid confusion
- **Field naming**: preserve the legacy WEPP labels (e.g., `Runoff (m^3)`, `Sed Del (kg)`) so hydrologists can match terminology across WEPP and WEPPCloud surfaces.
- **Parser ergonomics**: when porting the text files, reuse the Fortran variable names from the originating module (e.g., `wshpas.for`) for local variables and column mapping to improve traceability.
- **Performance**: streaming readers with a fan-out pool feeding a single Arrow writer per Parquet target. Avoid loading entire directories into memory at once, but performance is more important than memory. (Current implementation executes sequentially; parallel file ingestion is scheduled for the next phase.)
- **Idempotence**: not a requirement. initiating wepp run will intentionally wipe `interchange` dir. 
- **Source of truth philosophy transition**: source of truth is moving from WEPP flat file outputs to interchange parquet files. Long term goal is to be able to delete `wepp/output` after interchange. Along the way to this goal we will move from 0. do nothing. 1. tar archive output 2. delete after interchange.
- **Validation hooks**: expose lightweight data sanity checks (row counts per source file, non-null gauges, optional hash) to support regression test harnesses.

## Processing Pipeline Expectations
1. Discover raw hill files beneath `wepp/output` (glob `H*.{ebe,element,pass,loss,soil,wat}.dat`).
2. Dispatch file readers in a worker pool. Workers parse raw text to Arrow RecordBatches (schema-specific) while adding normalized identifiers.
3. Aggregate worker output via a thread-safe queue feeding a dedicated writer task that appends to `pyarrow.parquet.ParquetWriter`.
4. Each Parquet file is written once per run (single writer instance). Temporary output path (`.tmp`) in `/dev/shm` renamed atomically on success. We don't care about cross-platform support.
   - Upcoming work: shard file parsing across a worker pool so readers can stream concurrently into the shared writer.
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
- 2025-02-17: Landed dedicated hillslope interchange writers (`hill_ebe_interchange.py`, `hill_element_interchange.py`, `hill_loss_interchange.py`, `hill_soil_interchange.py`, `hill_wat_interchange.py`) with Arrow schemas mirroring WEPP column labels. Added regression coverage per product.
- 2025-02-17: Elevated orchestration via `run_wepp_hillslope_pass_interchange`/`run_wepp_hillslope_interchange` so a single call materializes all hillslope parquet artifacts beneath `wepp/output/interchange/`. Tests now assert every parquet target is emitted when PASS runs.
- 2025-02-20: Added worker-pool helper integration across all hillslope writers with `/dev/shm` staging, taught EBE parsing to accept a `start_year` offset for 1-indexed WEPP years, and refreshed the interchange tests to assert the concurrent fan-out path.
- 2025-02-21: Swapped the thread pool for a `ProcessPoolExecutor` plus a streaming writer queue so parsing and parquet emission overlap fully. End-to-end runtime on `/wc1/runs/co/copacetic-note/wepp/ag_fields/output/` dropped from ~5,360 s to ~469 s (≈11× faster), leaving raw file I/O as the primary cost.

```
>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.element.parquet').info()
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 432 entries, 0 to 431
Data columns (total 32 columns):
 #   Column            Non-Null Count  Dtype  
---  ------            --------------  -----  
 0   wepp_id           432 non-null    int32  
 1   ofe_id            432 non-null    int16  
 2   year              432 non-null    int16  
 3   day               432 non-null    int16  
 4   julian            432 non-null    int16  
 5   month             432 non-null    int8   
 6   day_of_month      432 non-null    int8   
 7   water_year        432 non-null    int16  
 8   OFE               432 non-null    int16  
 9   DD                432 non-null    int16  
 10  MM                432 non-null    int16  
 11  YYYY              432 non-null    int16  
 12  Precip (mm)       432 non-null    float64
 13  Runoff (mm)       432 non-null    float64
 14  EffInt (mm/h)     432 non-null    float64
 15  PeakRO (mm/h)     432 non-null    float64
 16  EffDur (h)        432 non-null    float64
 17  Enrich (Ratio)    432 non-null    float64
 18  Keff (mm/h)       432 non-null    float64
 19  Sm (mm)           432 non-null    float64
 20  LeafArea (Index)  432 non-null    float64
 21  CanHgt (m)        432 non-null    float64
 22  Cancov (%)        432 non-null    float64
 23  IntCov (%)        432 non-null    float64
 24  RilCov (%)        432 non-null    float64
 25  LivBio (Kg/m^2)   432 non-null    float64
 26  DeadBio (Kg/m^2)  432 non-null    float64
 27  Ki                432 non-null    float64
 28  Kr                432 non-null    float64
 29  Tcrit             432 non-null    float64
 30  RilWid (m)        432 non-null    float64
 31  SedLeave (kg/m)   432 non-null    float64
dtypes: float64(20), int16(9), int32(1), int8(2)
memory usage: 77.8 KB
>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.element.parquet')
     wepp_id  ofe_id  year  day  julian  month  day_of_month  ...  LivBio (Kg/m^2)  DeadBio (Kg/m^2)     Ki     Kr  Tcrit  RilWid (m)  SedLeave (kg/m)
0          1       1  2000    1       1      1             1  ...            0.493             1.382  0.041  0.007    3.0        0.15              0.0
1          1       1  2000   15      15      1            15  ...            0.493             1.382  0.041  0.007    3.0        0.15              0.0
2          1       1  2000   32      32      2             1  ...            0.493             1.382  0.041  0.007    3.0        0.15              0.0
3          1       1  2000   46      46      2            15  ...            0.493             1.382  0.041  0.007    3.0        0.15              0.0
4          1       1  2000   61      61      3             1  ...            0.493             1.382  0.041  0.007    3.0        0.15              0.0
..       ...     ...   ...  ...     ...    ...           ...  ...              ...               ...    ...    ...    ...         ...              ...
427        3       1  2005  288     288     10            15  ...            0.493             1.382  0.039  0.007    3.0        0.15              0.0
428        3       1  2005  305     305     11             1  ...            0.493             1.382  0.039  0.007    3.0        0.15              0.0
429        3       1  2005  319     319     11            15  ...            0.493             1.382  0.039  0.007    3.0        0.15              0.0
430        3       1  2005  335     335     12             1  ...            0.493             1.382  0.039  0.007    3.0        0.15              0.0
431        3       1  2005  349     349     12            15  ...            0.493             1.382  0.039  0.007    3.0        0.15              0.0

[432 rows x 32 columns]

>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.ebe.parquet').info()
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 0 entries
Data columns (total 17 columns):
 #   Column            Non-Null Count  Dtype  
---  ------            --------------  -----  
 0   wepp_id           0 non-null      int32  
 1   year              0 non-null      int16  
 2   month             0 non-null      int8   
 3   day_of_month      0 non-null      int8   
 4   julian            0 non-null      int16  
 5   water_year        0 non-null      int16  
 6   Precp (mm)        0 non-null      float64
 7   Runoff (mm)       0 non-null      float64
 8   IR-det (kg/m^2)   0 non-null      float64
 9   Av-det (kg/m^2)   0 non-null      float64
 10  Mx-det (kg/m^2)   0 non-null      float64
 11  Point (m)         0 non-null      float64
 12  Av-dep (kg/m^2)   0 non-null      float64
 13  Max-dep (kg/m^2)  0 non-null      float64
 14  Point (m)_2       0 non-null      float64
 15  Sed.Del (kg/m)    0 non-null      float64
 16  ER                0 non-null      float64
dtypes: float64(11), int16(3), int32(1), int8(2)
memory usage: 124.0 bytes

[empty for test run]

>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.element.parquet').info()
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 432 entries, 0 to 431
Data columns (total 32 columns):
 #   Column            Non-Null Count  Dtype  
---  ------            --------------  -----  
 0   wepp_id           432 non-null    int32  
 1   ofe_id            432 non-null    int16  
 2   year              432 non-null    int16  
 3   day               432 non-null    int16  
 4   julian            432 non-null    int16  
 5   month             432 non-null    int8   
 6   day_of_month      432 non-null    int8   
 7   water_year        432 non-null    int16  
 8   OFE               432 non-null    int16  
 9   DD                432 non-null    int16  
 10  MM                432 non-null    int16  
 11  YYYY              432 non-null    int16  
 12  Precip (mm)       432 non-null    float64
 13  Runoff (mm)       432 non-null    float64
 14  EffInt (mm/h)     432 non-null    float64
 15  PeakRO (mm/h)     432 non-null    float64
 16  EffDur (h)        432 non-null    float64
 17  Enrich (Ratio)    432 non-null    float64
 18  Keff (mm/h)       432 non-null    float64
 19  Sm (mm)           432 non-null    float64
 20  LeafArea (Index)  432 non-null    float64
 21  CanHgt (m)        432 non-null    float64
 22  Cancov (%)        432 non-null    float64
 23  IntCov (%)        432 non-null    float64
 24  RilCov (%)        432 non-null    float64
 25  LivBio (Kg/m^2)   432 non-null    float64
 26  DeadBio (Kg/m^2)  432 non-null    float64
 27  Ki                432 non-null    float64
 28  Kr                432 non-null    float64
 29  Tcrit             432 non-null    float64
 30  RilWid (m)        432 non-null    float64
 31  SedLeave (kg/m)   432 non-null    float64
dtypes: float64(20), int16(9), int32(1), int8(2)
memory usage: 77.8 KB
>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.element.parquet')
     wepp_id  ofe_id  year  day  julian  month  day_of_month  water_year  OFE  ...  IntCov (%)  RilCov (%)  LivBio (Kg/m^2)  DeadBio (Kg/m^2)     Ki     Kr  Tcrit  RilWid (m)  SedLeave (kg/m)
0          1       1  2000    1       1      1             1        2000    1  ...        99.9        99.9            0.493             1.382  0.041  0.007    3.0        0.15              0.0
1          1       1  2000   15      15      1            15        2000    1  ...        99.9        99.9            0.493             1.382  0.041  0.007    3.0        0.15              0.0
2          1       1  2000   32      32      2             1        2000    1  ...        99.9        99.9            0.493             1.382  0.041  0.007    3.0        0.15              0.0
3          1       1  2000   46      46      2            15        2000    1  ...        99.9        99.9            0.493             1.382  0.041  0.007    3.0        0.15              0.0
4          1       1  2000   61      61      3             1        2000    1  ...        99.9        99.9            0.493             1.382  0.041  0.007    3.0        0.15              0.0
..       ...     ...   ...  ...     ...    ...           ...         ...  ...  ...         ...         ...              ...               ...    ...    ...    ...         ...              ...
427        3       1  2005  288     288     10            15        2006    1  ...        99.9        99.9            0.493             1.382  0.039  0.007    3.0        0.15              0.0
428        3       1  2005  305     305     11             1        2006    1  ...        99.9        99.9            0.493             1.382  0.039  0.007    3.0        0.15              0.0
429        3       1  2005  319     319     11            15        2006    1  ...        99.9        99.9            0.493             1.382  0.039  0.007    3.0        0.15              0.0
430        3       1  2005  335     335     12             1        2006    1  ...        99.9        99.9            0.493             1.382  0.039  0.007    3.0        0.15              0.0
431        3       1  2005  349     349     12            15        2006    1  ...        99.9        99.9            0.493             1.382  0.039  0.007    3.0        0.15              0.0


pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.loss.parquet').info()
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 15 entries, 0 to 14
Data columns (total 11 columns):
 #   Column             Non-Null Count  Dtype  
---  ------             --------------  -----  
 0   wepp_id            15 non-null     int32  
 1   class_id           15 non-null     int8   
 2   Class              15 non-null     int8   
 3   Diameter (mm)      15 non-null     float64
 4   Specific Gravity   15 non-null     float64
 5   % Sand             15 non-null     float64
 6   % Silt             15 non-null     float64
 7   % Clay             15 non-null     float64
 8   % O.M.             15 non-null     float64
 9   Sediment Fraction  15 non-null     float64
 10  In Flow Exiting    15 non-null     float64
dtypes: float64(8), int32(1), int8(2)
memory usage: 1.2 KB
>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.loss.parquet')
    wepp_id  class_id  Class  Diameter (mm)  Specific Gravity  % Sand  % Silt  % Clay  % O.M.  Sediment Fraction  In Flow Exiting
0         1         1      1          0.002              2.60     0.0     0.0   100.0   112.5              0.010              0.0
1         1         2      2          0.010              2.65     0.0   100.0     0.0     0.0              0.528              0.0
2         1         3      3          0.030              1.80     0.0    93.7     6.3     7.0              0.072              0.0
3         1         4      4          0.300              1.60    69.2     4.7    26.1    29.4              0.096              0.0
4         1         5      5          0.200              2.65   100.0     0.0     0.0     0.0              0.294              0.0
5         2         1      1          0.002              2.60     0.0     0.0   100.0   112.5              0.010              0.0
6         2         2      2          0.010              2.65     0.0   100.0     0.0     0.0              0.528              0.0
7         2         3      3          0.030              1.80     0.0    93.7     6.3     7.0              0.072              0.0
8         2         4      4          0.300              1.60    69.2     4.7    26.1    29.4              0.096              0.0
9         2         5      5          0.200              2.65   100.0     0.0     0.0     0.0              0.294              0.0
10        3         1      1          0.002              2.60     0.0     0.0   100.0   112.5              0.010              0.0
11        3         2      2          0.010              2.65     0.0   100.0     0.0     0.0              0.528              0.0
12        3         3      3          0.030              1.80     0.0    93.7     6.3     7.0              0.072              0.0
13        3         4      4          0.300              1.60    69.2     4.7    26.1    29.4              0.096              0.0
14        3         5      5          0.200              2.65   100.0     0.0     0.0     0.0              0.294              0.0

>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.pass.parquet').info()
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 6576 entries, 0 to 6575
Data columns (total 32 columns):
 #   Column        Non-Null Count  Dtype  
---  ------        --------------  -----  
 0   wepp_id       6576 non-null   int32  
 1   event         6576 non-null   object 
 2   year          6576 non-null   int16  
 3   day           6576 non-null   int16  
 4   julian        6576 non-null   int16  
 5   month         6576 non-null   int8   
 6   day_of_month  6576 non-null   int8   
 7   water_year    6576 non-null   int16  
 8   dur           6576 non-null   float64
 9   tcs           6576 non-null   float64
 10  oalpha        6576 non-null   float64
 11  runoff        6576 non-null   float64
 12  runvol        6576 non-null   float64
 13  sbrunf        6576 non-null   float64
 14  sbrunv        6576 non-null   float64
 15  drainq        6576 non-null   float64
 16  drrunv        6576 non-null   float64
 17  peakro        6576 non-null   float64
 18  tdet          6576 non-null   float64
 19  tdep          6576 non-null   float64
 20  sedcon_1      6576 non-null   float64
 21  sedcon_2      6576 non-null   float64
 22  sedcon_3      6576 non-null   float64
 23  sedcon_4      6576 non-null   float64
 24  sedcon_5      6576 non-null   float64
 25  frcflw_1      6576 non-null   float64
 26  frcflw_2      6576 non-null   float64
 27  frcflw_3      6576 non-null   float64
 28  frcflw_4      6576 non-null   float64
 29  frcflw_5      6576 non-null   float64
 30  gwbfv         6576 non-null   float64
 31  gwdsv         6576 non-null   float64
dtypes: float64(24), int16(4), int32(1), int8(2), object(1)
memory usage: 1.3+ MB

>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.pass.parquet')
      wepp_id     event  year  day  julian  month  day_of_month  water_year  dur  tcs  ...  sedcon_3  sedcon_4  sedcon_5  frcflw_1  frcflw_2  frcflw_3  frcflw_4  frcflw_5     gwbfv  gwdsv
0           1  SUBEVENT  2000    1       1      1             1        2000  0.0  0.0  ...       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0  1.031100    0.0
1           1  SUBEVENT  2000    2       2      1             2        2000  0.0  0.0  ...       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0  2.021000    0.0
2           1  SUBEVENT  2000    3       3      1             3        2000  0.0  0.0  ...       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0  2.971200    0.0
3           1  SUBEVENT  2000    4       4      1             4        2000  0.0  0.0  ...       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0  3.883500    0.0
4           1  SUBEVENT  2000    5       5      1             5        2000  0.0  0.0  ...       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0  4.759200    0.0
...       ...       ...   ...  ...     ...    ...           ...         ...  ...  ...  ...       ...       ...       ...       ...       ...       ...       ...       ...       ...    ...
6571        3  NO EVENT  2005  361     361     12            27        2006  0.0  0.0  ...       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0  0.011365    0.0
6572        3  NO EVENT  2005  362     362     12            28        2006  0.0  0.0  ...       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0  0.010910    0.0
6573        3  NO EVENT  2005  363     363     12            29        2006  0.0  0.0  ...       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0  0.010474    0.0
6574        3  NO EVENT  2005  364     364     12            30        2006  0.0  0.0  ...       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0  0.010055    0.0
6575        3  NO EVENT  2005  365     365     12            31        2006  0.0  0.0  ...       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0  0.009653    0.0

[6576 rows x 32 columns]

>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.soil.parquet').info()
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 6576 entries, 0 to 6575
Data columns (total 22 columns):
 #   Column             Non-Null Count  Dtype  
---  ------             --------------  -----  
 0   wepp_id            6576 non-null   int32  
 1   ofe_id             6576 non-null   int16  
 2   year               6576 non-null   int16  
 3   day                6576 non-null   int16  
 4   julian             6576 non-null   int16  
 5   month              6576 non-null   int8   
 6   day_of_month       6576 non-null   int8   
 7   water_year         6576 non-null   int16  
 8   OFE                6576 non-null   int16  
 9   Day                6576 non-null   int16  
 10  Y                  6576 non-null   int16  
 11  Poros (%)          6576 non-null   float64
 12  Keff (mm/hr)       6576 non-null   float64
 13  Suct (mm)          6576 non-null   float64
 14  FC (mm/mm)         6576 non-null   float64
 15  WP (mm/mm)         6576 non-null   float64
 16  Rough (mm)         6576 non-null   float64
 17  Ki (adjsmt)        6576 non-null   float64
 18  Kr (adjsmt)        6576 non-null   float64
 19  Tauc (adjsmt)      6576 non-null   float64
 20  Saturation (frac)  6576 non-null   float64
 21  TSW (mm)           6576 non-null   float64
dtypes: float64(11), int16(8), int32(1), int8(2)
memory usage: 706.5 KB

>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.soil.parquet')
      wepp_id  ofe_id  year  day  julian  month  day_of_month  water_year  ...  FC (mm/mm)  WP (mm/mm)  Rough (mm)  Ki (adjsmt)  Kr (adjsmt)  Tauc (adjsmt)  Saturation (frac)  TSW (mm)
0           1       1  2000    1       1      1             1        2000  ...         0.2        0.05       100.0         0.04         0.13            2.0               0.46     30.56
1           1       1  2000    2       2      1             2        2000  ...         0.2        0.05       100.0         0.04         0.13            2.0               0.36     23.62
2           1       1  2000    3       3      1             3        2000  ...         0.2        0.05       100.0         0.04         0.13            2.0               0.32     21.45
3           1       1  2000    4       4      1             4        2000  ...         0.2        0.05       100.0         0.04         0.13            2.0               0.31     20.64
4           1       1  2000    5       5      1             5        2000  ...         0.2        0.05       100.0         0.04         0.13            2.0               0.31     20.43
...       ...     ...   ...  ...     ...    ...           ...         ...  ...         ...         ...         ...          ...          ...            ...                ...       ...
6571        3       1  2005  361     361     12            27        2006  ...         0.2        0.05       100.0         0.04         0.13            2.0               0.37     24.55
6572        3       1  2005  362     362     12            28        2006  ...         0.2        0.05       100.0         0.04         0.13            2.0               0.45     29.54
6573        3       1  2005  363     363     12            29        2006  ...         0.2        0.05       100.0         0.04         0.13            2.0               0.38     24.86
6574        3       1  2005  364     364     12            30        2006  ...         0.2        0.05       100.0         0.04         0.13            2.0               0.41     26.96
6575        3       1  2005  365     365     12            31        2006  ...         0.2        0.05       100.0         0.04         0.13            2.0               0.47     30.71

[6576 rows x 22 columns]

<class 'pandas.core.frame.DataFrame'>tests/wepp/interchange/test_project/output/interchange/H.wat.parquet').info() 
RangeIndex: 6576 entries, 0 to 6575
Data columns (total 28 columns):
 #   Column                 Non-Null Count  Dtype  
---  ------                 --------------  -----  
 0   wepp_id                6576 non-null   int32  
 1   ofe_id                 6576 non-null   int16  
 2   year                   6576 non-null   int16  
 3   day                    6576 non-null   int16  
 4   julian                 6576 non-null   int16  
 5   month                  6576 non-null   int8   
 6   day_of_month           6576 non-null   int8   
 7   water_year             6576 non-null   int16  
 8   OFE (#)                6576 non-null   int16  
 9   J                      6576 non-null   int16  
 10  Y                      6576 non-null   int16  
 11  P (mm)                 6576 non-null   float64
 12  RM (mm)                6576 non-null   float64
 13  Q (mm)                 6576 non-null   float64
 14  Ep (mm)                6576 non-null   float64
 15  Es (mm)                6576 non-null   float64
 16  Er (mm)                6576 non-null   float64
 17  Dp (mm)                6576 non-null   float64
 18  UpStrmQ (mm)           6576 non-null   float64
 19  SubRIn (mm)            6576 non-null   float64
 20  latqcc (mm)            6576 non-null   float64
 21  Total-Soil Water (mm)  6576 non-null   float64
 22  frozwt (mm)            6576 non-null   float64
 23  Snow-Water (mm)        6576 non-null   float64
 24  QOFE (mm)              6576 non-null   float64
 25  Tile (mm)              6576 non-null   float64
 26  Irr (mm)               6576 non-null   float64
 27  Area (m^2)             6576 non-null   float64
dtypes: float64(17), int16(8), int32(1), int8(2)
memory usage: 1014.8 KB

>>> pd.read_parquet('/workdir/wepppy/tests/wepp/interchange/test_project/output/interchange/H.wat.parquet')
      wepp_id  ofe_id  year  day  julian  month  day_of_month  water_year  ...  latqcc (mm)  Total-Soil Water (mm)  frozwt (mm)  Snow-Water (mm)  QOFE (mm)  Tile (mm)  Irr (mm)  Area (m^2)
0           1       1  2000    1       1      1             1        2000  ...         0.34                 566.70          0.0            12.20        0.0        0.0       0.0   105300.34
1           1       1  2000    2       2      1             2        2000  ...         0.56                 565.48          0.0            18.00        0.0        0.0       0.0   105300.34
2           1       1  2000    3       3      1             3        2000  ...         0.82                 563.90          0.0            18.00        0.0        0.0       0.0   105300.34
3           1       1  2000    4       4      1             4        2000  ...         1.15                 561.67          0.0            41.90        0.0        0.0       0.0   105300.34
4           1       1  2000    5       5      1             5        2000  ...         1.76                 559.30          0.0            41.90        0.0        0.0       0.0   105300.34
...       ...     ...   ...  ...     ...    ...           ...         ...  ...          ...                    ...          ...              ...        ...        ...       ...         ...
6571        3       1  2005  361     361     12            27        2006  ...         0.00                 359.44          0.0            63.34        0.0        0.0       0.0    83712.00
6572        3       1  2005  362     362     12            28        2006  ...         0.00                 384.19          0.0            59.44        0.0        0.0       0.0    83712.00
6573        3       1  2005  363     363     12            29        2006  ...         0.00                 387.78          0.0            55.34        0.0        0.0       0.0    83712.00
6574        3       1  2005  364     364     12            30        2006  ...         0.00                 403.76          0.0            54.15        0.0        0.0       0.0    83712.00
6575        3       1  2005  365     365     12            31        2006  ...         0.00                 429.39          0.0            47.72        0.0        0.0       0.0    83712.00

[6576 rows x 28 columns]
```
