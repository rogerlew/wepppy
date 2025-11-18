# PATH + Omni MVP Spec

> Minimal plan to make PATH cost-effective run end-to-end by auto-provisioning Omni scenarios (SBS map-centric) and collecting user cost inputs in $/ha.

## Current State
- **Frontend (`wepppy/weppcloud/controllers_js/path_ce.js:142-175`)** hardcodes scenario dropdown defaults (`mulch_15_sbs_map`, `mulch_30_sbs_map`, `mulch_60_sbs_map`, `sbs_map`, `undisturbed`) but still exposes free-form scenario text fields and lets users add/remove arbitrary treatments. Costs are labeled as unit/fixed with no unit guidance.
- **Template (`wepppy/weppcloud/templates/controls/path_cost_effective_pure.htm`)** renders generic threshold/filter fields plus a dynamic treatments table (scenario key, quantity, unit cost, fixed cost). Nothing enforces the mulch trio or $/ha.
- **Routes (`wepppy/weppcloud/routes/nodb_api/path_ce_bp.py:83-194`)** only manage config/status/results and enqueue `run_path_cost_effective_rq`; they assume Omni artifacts already exist and do not validate SBS map/Omni readiness.
- **RQ task (`wepppy/rq/path_ce_rq.py:20-58`)** immediately calls `PathCostEffective.run()`; no Omni orchestration or freshness check.
- **NoDb/controller (`wepppy/nodb/mods/path_ce/path_cost_effective.py:47-117, 316-379`)** defaults to post-fire `sbs_map`, undisturbed baseline, and three mulch options with zero costs. It pulls Omni parquet outputs from `_pups/omni` and fails fast if scenarios are missing.
- **Data loader (`wepppy/nodb/mods/path_ce/data_loader.py:64-129`)** expects `_pups/omni/scenarios.hillslope_summaries.parquet` and `contrasts.out.parquet` plus `watershed/hillslopes.parquet`; scenario names must match the configured treatment options.
- **Legacy prototype** (`wepppy/nodb/mods/path_ce_model.py`) is unused and diverges from the newer controller/solver path.

## Gaps vs Desired Flow
- PATH run button does not set up or execute Omni; users must pre-run Omni manually with the exact scenarios Path expects.
- UI allows arbitrary scenario strings and quantity/cost units; no explicit $/ha cost inputs per mulch condition.
- Backend never asserts SBS map availability or creates the undisturbed baseline/treatment scenarios; missing Omni artifacts surface only as data loader errors.
- Scenario naming between Omni and Path is not guaranteed (`mulch_*_sbs_map` keys are assumed but never provisioned).

## Target MVP Behaviour
1. **Assumptions**: run already has an SBS map available for Omni; undisturbed baseline is allowed. If SBS map assets are absent, surface a clear error before queueing.
2. **Standard scenarios** (provisioned automatically via Omni):
   - Post-fire baseline: `sbs_map`.
   - Treatments: `mulch_15_sbs_map`, `mulch_30_sbs_map`, `mulch_60_sbs_map` (ground_cover_increase 15/30/60% applied to SBS map).
   - Reference: `undisturbed`.
3. **UI**: Path control loads with these four scenarios pre-listed; the three mulch rows are fixed/read-only for scenario names and tonnage, exposing only a numeric `$ per ha` cost field for each. Optional thresholds/filters remain, but treatment add/remove is disabled for MVP.
4. **Run Path button**:
   - Builds/refreshes the Omni scenario list above (overriding ad-hoc Omni definitions for this run).
   - Executes Omni (reuse `run_omni_scenarios`/RQ helper) and waits for completion.
   - On successful Omni completion, executes `PathCostEffective.run()` using the generated parquets.
   - Streams status to the PATH channel with clear sub-steps (Omni provisioning → Omni running → Path running).
5. **Costs**: Treat user-entered values as `$ / ha` for each mulch intensity. Backend derives the solver cost vector consistently (e.g., set `quantity=1`, map cost directly to `unit_cost`, ignore fixed cost unless provided).

## Implementation Notes
- **Omni wiring**: Add a small adapter to construct the scenario payloads (SBS map base + three mulch variants + undisturbed) and feed them into `Omni.parse_scenarios`, ensuring scenario names land as `mulch_XX_sbs_map` to satisfy the Path data loader. Consider reusing `run_omni_scenarios_rq` or a synchronous call inside the Path RQ worker for MVP.
- **Route/task orchestration**: Update `tasks/path_cost_effective_run` handler to enqueue a job that performs Omni prep + run + Path run as a single flow (or chained jobs) and surfaces early validation errors (missing SBS map, Omni disabled).
- **Config surface**: Simplify the config payload to cost fields for the three mulch options; server builds `treatment_options` from these costs to keep scenario naming consistent and immutable.
- **Data loader alignment**: Ensure cost semantics match the $/ha UI; if quantity is implicit, normalize `unit_cost` accordingly before calling the solver.
- **Telemetry**: Mirror Omni progress into the PATH status endpoint or emit composite statuses so the UI can convey where time is spent.
- **Safety**: Leave legacy `path_ce_model.py` untouched but note it remains unused; avoid silent fallbacks that hide missing Omni artifacts.

## Open Questions
- Should Omni re-run every time Path is invoked, or can we skip if `_pups/omni` already contains fresh parquets for these scenarios?
- Where is SBS map presence best validated (Disturbed controller vs. filesystem probe), and what constitutes “ready”?
- Do we need to preserve existing custom Omni scenarios, or is it acceptable to overwrite with the fixed Path set for this workflow?
- Are per-hectare costs sufficient, or do we need optional fixed costs (mobilization) per mulch intensity?
