# PATH Cost-Effective Integration Plan (Solver & Data Prep)

## Goal
Embed the existing PATH Cost-Effective optimization workflow inside the `PathCostEffective` NoDb controller so the model runs from within WEPPcloud using Omni scenario outputs and watershed parquet data.

## Required Inputs
- **Omni scenario hillslope summaries**: `_pups/omni/scenarios.hillslope_summaries.parquet`
- **Omni scenario outlet report**: `_pups/omni/contrasts.out.parquet`
- **Watershed hillslopes parquet** (source of `slope_scalar`, geometry metadata): `watershed/hillslopes.parquet`
- Optional future extensions: path-specific config stored under `<wd>/path/*.json`

## Module Layout
```
wepppy/nodb/mods/path_ce/
├── path_cost_effective.py     # NoDb controller scaffolding (already present)
├── path_ce_solver.py          # (new) wraps PuLP model + data framing helpers
├── data_loader.py             # (new) Omni & watershed parquet ingestion utilities
├── __init__.py
├── implementation_plan.md
└── integration_plan.md        # (this document)
```

## Integration Steps
1. **Data Loading Utilities**
   - Create `data_loader.py` with helpers to:
     - Validate presence of all required Omni/watershed parquet files.
     - Read Omni hillslope summaries into DataFrames, pivoting by scenario (`mulch_15_sbs_map`, etc.) and normalizing column names.
     - Read Omni outlet contrast report and isolate sediment discharge metrics for mulch contrasts.
     - Merge watershed hillslope attributes (particularly `slope_scalar`, `wepp_id`, `topaz_id`, burn severity proxies) into the solver-ready table.
     - Compute slope degrees inside the helper (`np.degrees(np.arctan(slope_scalar))`).

2. **Solver Module (`solver.py`)**
   - Port `ce_select_sites_2` and related logic from the prototype, adjusting signatures to accept:
     - Prepared DataFrame (already filtered/merged).
     - Config object that includes thresholds, slope/burn filters, treatment catalog.
   - Expose a `run_cost_effective_solver(config, data)` function returning structured results (selected hillslopes, cost totals, tables).
   - Split fallback logic (secondary maximize) into a dedicated function for clarity/testing.

3. **Controller Wiring (`PathCostEffective`)**
   - Add a `run()` method that:
     1. Calls data loader to assemble DataFrame.
     2. Applies configuration (thresholds, filters).
     3. Invokes the solver module.
     4. Stores results via `store_results()`, including:
        - Treatment allocations per hillslope.
        - Total/Fixed cost summaries.
        - Final sediment discharge/yield stats.
        - Untreatable hillslopes table.
   - Emit progress/status updates (`set_status`) at major milestones (loading, solving, storing).

4. **Error Handling & Telemetry**
   - Wrap solver execution in try/except:
     - On failure, update status to `failed` with an informative message.
     - Re-raise or return errors suitable for RQ task reporting.
   - Provide lightweight validation (e.g., thresholds <= post-fire totals) and log warnings.

5. **Testing**
   - Add unit tests under `wepppy/nodb/mods/tests/test_path_ce.py` with synthetic Omni-like fixtures to verify:
     - Data loader correctly merges slope/burn severity.
     - Solver respects thresholds and secondary optimization path.
   - Include regression test to ensure slope degrees originate from watershed parquet (`slope_scalar`) rather than Omni data.

6. **Cleanup & Doc Updates**
   - Retire `/workdir/PATH-cost-effective/PATH_CE.py` once ported; archive or reference in README.
   - Update `implementation_plan.md` and create `README.md` summarizing runtime usage.
   - Document new RQ task / API endpoints once implemented.

## Storage & Schema Decisions
- Persist solver outputs as parquet files within `<wd>/path/`, leveraging Arrow schema helpers from `wepppy.wepp.interchange.schema_utils.pa_field` so downstream consumers have consistent typing.
- Keep a condensed JSON snapshot in the NoDb payload for quick API responses, but treat parquet as the authoritative archive for tables/exports.

## Open Questions
- Additional treatment sets beyond mulch are expected; design loader mappings so new Omni scenario names can be configured without code changes.

## Next Actions
1. Build `data_loader.py` with unit coverage.
2. Port solver into `solver.py` and adapt to new config structure.
3. Implement `PathCostEffective.run()` orchestrating loader + solver + persistence.
4. Hook into RQ/Flask once backend execution path is confirmed.
