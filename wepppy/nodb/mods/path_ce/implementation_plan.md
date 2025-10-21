# PATH Cost-Effective Integration Plan

## Core Goals
- Wrap the existing PATH cost-effectiveness prototype logic inside a first-class NoDb controller (`PathCostEffective`) so runs compose with the rest of weppcloud.
- Persist analysis inputs/outputs under `<wd>/path/` and emit telemetry so operators can monitor progress through the standard status pipeline.
- Prepare backend endpoints and client scaffolding for a forthcoming spatial/reporting UI (page delivery is out of scope for this pass).

## Data & Dependencies
- **Inputs**: Omni scenario summaries (hillslope, outlet, and hillslope characteristics aggregates) stored alongside the working directory. The controller must validate presence/version and hydrate pandas DataFrames from these artifacts before solving.
- **Solver**: Use PuLP with the default CBC backend. Expose a hook to override the solver path if deployments ship a different COIN-OR binary.
- **Packages**: Ensure `pulp` (and its CBC dependency) is declared in `docker/requirements-uv.txt` and mirrored in the stubbed requirements set.

## Controller Design (`PathCostEffective`)
1. **Initialization**
   - `PathCostEffective.getInstance(wd)` should create/return the singleton.
   - Resolve `path_dir = Path(wd) / "path"`; create on demand with locking.
2. **Configuration Payload**
   - Persist thresholds, treatment configurations, and filter selections (slope/burn severity) to the NoDb instance.
   - Add helpers to update/read config using `nodb_setter` patterns for telemetry-friendly mutations.
3. **Data Preparation**
   - Implement a private `_load_omni_artifacts()` that reads Omni summaries into DataFrames, enforcing schema expectations.
   - Port `path_data_ag` into a service layer (`_build_solver_dataframe`) that assembles post-fire vs. treatment metrics, converting units where required.
4. **Optimization Execution**
   - Wrap `ce_select_sites_2` inside a method (`run_solver`) that:
     - Applies configured thresholds/filters.
     - Handles `PulpSolverError` and publishes failures to Redis DB 2.
     - Stores structured results (selected hillslopes, per-treatment allocations, totals, untreatable list, tables) on the NoDb instance.
   - Serialize final outputs back to disk + Redis via `dump_and_unlock()`.
5. **Results Surface**
   - Provide accessors for downstream consumers: summary (`get_summary`), detailed table (`get_sdyd_table`), and cost breakdowns.

## Task Breakdown
1. **Code Migration**
   - Relocate solver/data-prep logic from `/workdir/PATH-cost-effective/PATH_CE.py` into moduleized helpers under `wepppy/nodb/mods/path_ce/solver.py`.
   - Add `__init__.py` exporting `PathCostEffective` and helper factories; update `wepppy/nodb/mods/__init__.py` aggregator.
2. **RQ Integration**
   - Add `run_path_cost_effective` task in `wepppy/rq/project_rq.py` (or a new module) that instantiates the controller, executes `run_solver`, and streams progress via `StatusMessenger`.
   - Ensure results land in the NoDb payload so future HTTP responses can fetch them.
3. **Flask Endpoints (Skeleton)**
   - Stub routes under `wepppy/weppcloud/routes/path_ce.py` with POST (configure + launch) and GET (fetch state). Final UI wiring deferred.
   - Register blueprint and guard access based on project readiness (Omni artifacts present).
4. **Client Placeholder**
   - Add controller entry in `wepppy/weppcloud/controllers_js/` that can request current status and results. Actual template/report work tracked separately.
5. **Testing & Tooling**
   - Create unit tests under `wepppy/nodb/mods/tests/test_path_ce.py` covering:
     - Data loading validation.
     - Solver success with mock Omni data.
     - Threshold/filters edge cases (already-met thresholds, infeasible scenarios → fallback path).
   - Sync stub files (`tools/sync_stubs.py`) and extend `stubs/wepppy/nodb/mods/path_ce.pyi`.
   - Update Docker requirements and run `wctl run-stubtest wepppy.nodb.mods.path_ce`.
6. **Documentation**
   - Author `README.md` in this directory describing configuration options, expected inputs, and solver outputs.
   - Update top-level `ARCHITECTURE.md` and any operator guides pointing to the new functionality.

## Risks & Mitigations
- **Solver availability**: CBC must be present in runtime images; add CI smoke test that exercises the controller with a tiny Omni fixture.
- **Data drift**: Omni summary schema changes could break ingestion. Mitigate with schema checks and descriptive failure messages surfaced via telemetry.
- **Long runtimes**: Ensure RQ task emits periodic status updates and supports cooperative cancellation before large pulp solve calls.

## Follow-Up (Out of Scope)
- Build the dedicated report page with spatial visualization, tables, and download/export actions.
- Evaluate performance for large watersheds and consider chunked solving or heuristics if runtime exceeds acceptable thresholds.
