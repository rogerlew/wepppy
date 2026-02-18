# Phase 10 Mod Workflow Contract Notes

## Contract Anchors
- NoDir allowlist remains: `landuse`, `soils`, `climate`, `watershed`.
- Canonical NoDir errors must remain unchanged at workflow boundaries:
  - `409 NODIR_MIXED_STATE`
  - `500 NODIR_INVALID_ARCHIVE`
  - `503 NODIR_LOCKED`
- Phase 10A is inventory/contract mapping only; no runtime redesign is proposed here.

## Per-Surface Projection Contract Mapping

| surface | file:function | contract mapping | notes |
| --- | --- | --- | --- |
| Treatments enqueue route | `wepppy/microservices/rq_engine/treatments_routes.py:build_treatments` | mutation projection | Enqueue boundary for `landuse`/`soils` mutation should fail fast on mixed/invalid/locked root states before queue submission. |
| Treatments RQ owner job | `wepppy/rq/project_rq.py:build_treatments_rq` | mutation projection | Already routed through `mutate_roots(...)` owner wrapper for `landuse` + `soils`. |
| Treatments mutation implementation | `wepppy/nodb/mods/treatments/treatments.py:build_treatments` | mutation projection | Direct root writes (`landuse/*.man`, `soils/*.sol`) must remain owner-wrapped and not run in unmanaged dir/archive mixed state. |
| Ash enqueue route | `wepppy/microservices/rq_engine/ash_routes.py:run_ash` | read projection | Route should preflight dependent roots (`climate`, `watershed`, `landuse`) to preserve canonical NoDir status/code responses. |
| Ash RQ job | `wepppy/rq/project_rq.py:run_ash_rq` | read projection | Job currently delegates root read behavior to `Ash.run_ash`; projection semantics are not explicit at this layer. |
| Ash model execution | `wepppy/nodb/mods/ash_transport/ash.py:Ash.run_ash` | read projection | Path-heavy `climate.cli_path` read is a projection-era contract point; helper-backed projected path usage is required. |
| Debris enqueue route | `wepppy/microservices/rq_engine/debris_flow_routes.py:run_debris_flow` | read projection | Route should preflight dependent roots before enqueue to avoid deferred NoDir failures in workers. |
| Debris RQ job | `wepppy/rq/project_rq.py:run_debris_flow_rq` | read projection | Delegates to `DebrisFlow.run_debris_flow`; no explicit NoDir preflight at job boundary today. |
| Debris computation | `wepppy/nodb/mods/debris_flow/debris_flow.py:DebrisFlow.run_debris_flow` | read projection | Uses controller attributes from `watershed`/`soils`; no direct allowlisted-root file-path reads identified. |
| Omni scenarios enqueue route | `wepppy/microservices/rq_engine/omni_routes.py:_run_omni` | read projection | Root-form compatibility for downstream scenario clone/execute path should be validated before enqueue. |
| Omni contrasts enqueue route | `wepppy/microservices/rq_engine/omni_routes.py:_run_omni_contrasts` | read projection | Boundary should preserve canonical NoDir errors for dependent roots before RQ fan-out. |
| Omni contrast dry-run route | `wepppy/microservices/rq_engine/omni_routes.py:_dry_run_omni_contrasts` | read projection | Dry-run path still reads watershed/dependent state and should follow the same preflight contract. |
| Omni scenarios RQ coordinator | `wepppy/rq/omni_rq.py:run_omni_scenarios_rq` | read projection | Coordinator depends on clone/root-normalization internals; no explicit root-form guard here. |
| Omni contrasts RQ coordinator | `wepppy/rq/omni_rq.py:run_omni_contrasts_rq` | read projection | Coordinator relies on `_run_contrast` and sidecar/clone assumptions for allowlisted-root reads. |
| Omni scenario clone | `wepppy/nodb/mods/omni/omni.py:_omni_clone` | read projection | Mixed dir-copy and archive-symlink behavior for roots is not normalized for `landuse`/`soils` archive sources. |
| Omni sibling clone replacement | `wepppy/nodb/mods/omni/omni.py:_omni_clone_sibling` | read projection | Explicit directory copy assumptions for `landuse`/`soils` conflict with archive-form source scenarios. |
| Omni contrast runner | `wepppy/nodb/mods/omni/omni.py:_run_contrast` | read projection | Uses NoDir-aware parquet sidecar lookup, but still sits inside clone/root-form behavior that is not fully normalized. |
| Observed blueprint routes | `wepppy/weppcloud/routes/nodb_api/observed_bp.py:submit_task_run_model_fit` | no NoDir dependency | Operates on observed CSV + report assets; no direct allowlisted-root path dependency surfaced in this inventory. |
| Observed processing | `wepppy/nodb/mods/observed/observed.py:calc_model_fit` | no NoDir dependency | Reads observed + WEPP/SWAT output artifacts, not allowlisted root paths. |

## Proposed Wave Ownership (W1-W4)
- `W1`: Route/RQ preflight hardening for treatments, ash, debris flow, omni enqueue/dry-run boundaries.
- `W2`: Ash path-heavy climate read adoption (`Ash.run_ash` + upstream RQ boundary alignment).
- `W3`: Omni clone/contrast root-form normalization (`_omni_clone`, `_omni_clone_sibling`, `_run_contrast`, and dependent RQ coordinators).
- `W4`: Observed closure and final hardening validation (confirm no hidden allowlisted-root dependency).

## Open Questions / Contract Ambiguities
1. Should Phase 10 W1 preflight checks be route-only, or also added inside `run_ash_rq` and `run_debris_flow_rq` for non-route enqueue callers?
2. For ash climate CLI reads, should fallback materialization be disabled by default to preserve fail-fast `503 NODIR_LOCKED` semantics?
3. In omni sibling cloning, what is the canonical source behavior when `landuse`/`soils` exist only as `.nodir` archives in sibling scenarios?
4. For `_run_contrast`, should missing archive-side parquet sidecars keep raising `FileNotFoundError`, or be normalized to canonical NoDir error payloads at the boundary layer?
5. Do we want explicit observed regression tests that force allowlisted roots into archive form to guard against future transitive coupling?
