# RHEM NoDb Mod

> Prepares and runs the Rangeland Hydrology and Erosion Model (RHEM) for each TOPAZ subcatchment in a WEPPcloud run.

> **See also:** [AGENTS.md](../../AGENTS.md) for NoDb locking/caching expectations and debugging tips.

## Overview

This mod is implemented as two NoDb singletons:

- `Rhem` (`rhem.nodb`): builds per-hillslope RHEM inputs under `<wd>/rhem/` and runs the compiled RHEM binary in parallel.
- `RhemPost` (`rhempost.nodb`): reads RHEM `*.sum` outputs and aggregates them into watershed-wide annual and return-period summaries used by reports and map queries.

At a glance, it:

- Combines **watershed slope geometry**, **soil texture**, **rangeland cover fractions**, and **CLIGEN climate** into RHEM `*.par` and `*.stm` inputs.
- Writes one `*.run` file per hillslope and executes `wepppy/rhem/bin/rhem_v23` concurrently (per-hillslope logs go to `*.err`).
- Produces `*.sum` outputs consumed by `RhemPost` and exposed through WEPPcloud report/query endpoints.

## Workflow

### Preconditions

`Rhem.prep_hillslopes()` expects these NoDb controllers to already be in a usable state:

- `Watershed`: watershed abstracted and subcatchment summaries available.
- `Soils`: `soils.domsoil_d` populated and soil textures resolvable.
- `RangelandCover`: `covers` mapping available for each TOPAZ ID.
- `Climate`: per-subcatchment climate summaries and `.cli` files present.

If required inputs are missing, `Rhem` raises `RhemNoDbLockedException` with a message describing what must be run first.

### Stages

1. `Rhem.clean()`
   - Recreates `<wd>/rhem/runs/` and `<wd>/rhem/output/`.
2. `Rhem.prep_hillslopes()`
   - For each TOPAZ subcatchment, creates:
     - `hill_<id>.par` via `wepppy.rhem.make_parameter_file(...)`
     - `hill_<id>.stm` from the CLIGEN `.cli` file (Rust-accelerated when `wepppyo3` is installed; otherwise uses the Python `ClimateFile.make_storm_file` fallback)
     - `hill_<id>.run` via `wepppy.rhem.make_hillslope_run(...)`
3. `Rhem.run_hillslopes()`
   - Runs `wepppy.rhem.run_hillslope(...)` for each TOPAZ ID (threaded).
   - Calls `RhemPost.run_post()` to populate `rhempost.nodb` aggregates.

## API / Usage

### Python (direct NoDb usage)

```python
from wepppy.nodb.mods.rhem import Rhem, RhemPost

wd = "/path/to/run"

rhem = Rhem.getInstance(wd)
rhem.clean()
rhem.prep_hillslopes()
rhem.run_hillslopes()

rhempost = RhemPost.getInstance(wd)
print(rhempost.watershed_annuals)
print(rhempost.query_sub_val("runoff"))  # "runoff" | "sed_yield" | "soil_loss"
```

### RQ-engine entrypoint (WEPPcloud)

The rq-engine exposes a FastAPI route that enqueues the RHEM job:

- `POST /runs/{runid}/{config}/run-rhem` (JWT scope `rq:enqueue`)

The request body may include these booleans (all default to `true` when omitted):

| Field | Meaning |
|------|---------|
| `clean` / `clean_hillslopes` | Reset `rhem/runs` and `rhem/output` before prep/run |
| `prep` / `prep_hillslopes` | Generate `*.par`, `*.stm`, and `*.run` files |
| `run` / `run_hillslopes` | Execute the RHEM binary and run `RhemPost` |

## Outputs

### Files on disk

| Path | Produced by | Notes |
|------|-------------|------|
| `<wd>/rhem/runs/hill_<id>.par` | `Rhem.prep_hillslopes()` | Parameter file (cover/soil/slope derived) |
| `<wd>/rhem/runs/hill_<id>.stm` | `Rhem.prep_hillslopes()` | Storm file derived from CLIGEN `.cli` |
| `<wd>/rhem/runs/hill_<id>.run` | `Rhem.prep_hillslopes()` | Batch runner input to `rhem_v23 -b` |
| `<wd>/rhem/runs/hill_<id>.err` | `Rhem.run_hillslopes()` | Captures stdout/stderr for that hillslope run |
| `<wd>/rhem/output/hill_<id>.sum` | RHEM binary | Parsed by `RhemPost` |

### Aggregates in `rhempost.nodb`

After `RhemPost.run_post()`:

- `hill_summaries[topaz_id]`: per-hillslope `RhemSummary` objects (may be missing annuals when a `.sum` is incomplete).
- `watershed_annuals`: watershed totals and normalized values (includes `mm/yr` conversions).
- `watershed_ret_freqs` and `ret_freq_periods`: return-period series aggregated across hillslopes.
- `missing_summaries_count`: how many hillslopes did not parse into annuals.

## Integration Points

- **Depends on (inputs)**
  - `wepppy.nodb.core`: `Watershed`, `Soils`, `Climate`
  - `wepppy.nodb.mods.rangeland_cover`: `RangelandCover`
  - `wepppy.topo.watershed_abstraction.SlopeFile`: slope geometry (`.slp`)
- **Model execution**
  - `wepppy.rhem`: input file writers + `run_hillslope(...)` wrapper around `wepppy/rhem/bin/rhem_v23`
  - Optional accelerator: `wepppyo3.climate.make_rhem_storm_file` (when installed)
- **Used by (outputs)**
  - WEPPcloud reports and queries via `wepppy/weppcloud/routes/nodb_api/rhem_bp.py`
  - Export flows via `wepppy/export/arc_export.py` (reads `RhemPost` when present)
  - Preflight checklist via `services/preflight2` (checks the `RedisPrep` timestamp for `run_rhem`)

## Developer Notes

- `prep_hillslopes()` is CPU-parallel; keep per-hillslope work self-contained (it is safe to extend `prepare_single(...)` when new inputs map cleanly to a TOPAZ ID).
- Storm generation is optional-Rust: the code prefers `wepppyo3` when available and otherwise falls back to Python CLIGEN parsing. Avoid adding “silent” extra fallbacks beyond this established boundary.
- `RhemPost.run_post()` assumes `hill_<id>.sum` exists for every TOPAZ ID and tracks missing/invalid annuals via `missing_summaries_count`.

## Operational Notes

- The RHEM binary is executed with a per-hillslope timeout (currently `200` seconds). Timeouts and other subprocess errors propagate up and abort the batch.
- `wepppy.rhem.run_hillslope(...)` writes logs to `hill_<id>.err` but does not currently check the subprocess exit code; treat missing/empty `*.sum` outputs as a primary signal of failure.
- If you suspect stale NoDb state during debugging, use the NoDb refresh guidance in [AGENTS.md](../../AGENTS.md) and re-run `Rhem.clean()` before a fresh prep.

## Further Reading

- `wepppy/nodb/mods/rhem/rhem.py` (controller and orchestration)
- `wepppy/nodb/mods/rhem/rhempost.py` (post-processing and aggregates)
- `wepppy/rhem/rhem.py` (binary wrapper and input writers)
- `wepppy/microservices/rq_engine/rhem_routes.py` (rq-engine enqueue API)
- `wepppy/weppcloud/routes/nodb_api/rhem_bp.py` (report/query endpoints)
