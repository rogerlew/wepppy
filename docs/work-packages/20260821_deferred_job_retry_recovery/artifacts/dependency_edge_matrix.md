# Dependency edge correction matrix

This is the exhaustive SURF-20A dependency-construction boundary. `Strict`
means ordinary RQ dependency semantics. `Tolerant finalizer` and `Tolerant
serialization` permit `Dependency(allow_failure=True)` only for `finished` and
`failed` prerequisites. A named finalizer consumes no required model output; a
named serialization edge connects independent work to bound resource use or
serialize same-resource mutation ownership. WBT request serialization protects
mutation ownership: the later request reconstructs and validates required state
under the existing admission and directory-root locks and must not consume a
partially failed predecessor mutation as required output.

| Owner / source | Dependent edge | Class | Output contract and regression |
| --- | --- | --- | --- |
| WEPP `wepppy/rq/wepp_rq_pipeline.py::_enqueue` | Every prep, execution, interchange, analysis, export, cleanup, and completion edge | Strict | Every dependent is transitive workflow work; a stage-0 failure leaves every descendant never-started. Live-RQ transitive test. |
| Culvert `wepppy/rq/culvert_rq_pipeline.py` | `run_culvert_run_rq[]` to `_final_culvert_batch_complete_rq` | Tolerant finalizer | Aggregates direct child outcomes without consuming failed model files. Failed-child/finalizer test. |
| Geneva `wepppy/microservices/rq_engine/geneva_routes.py` | `prepare_hrus` to `build_frequency_panel` to `run_batch` | Strict | Each stage consumes predecessor artifacts. Production admission failure/deferred/retry test. |
| Run sync `wepppy/microservices/rq_engine/run_sync_routes.py` | `run_sync_rq` to `migrations_rq` | Strict | Migration consumes the synchronized run tree. Production admission failure/deferred/retry test. |
| WBT `wepppy/rq/project_rq.py::_enqueue_serial_subcatchment_tree` | Prior request tail to next `build_subcatchments_rq` | Tolerant serialization | Separate user submissions do not consume each other's outputs; the edge serializes mutation ownership. Prove an earlier failed request can release the later independently valid build. |
| WBT same source | `build_subcatchments_rq` to `abstract_watershed_rq` | Strict | Abstraction requires the successful build state. Existing controlled validation/apply failures retain canonical failure-safe cancellation of the never-started abstraction child; other failures naturally leave it deferred. Prove canceled/deferred descendants never start and admission retry remains safe. |
| Channels `wepppy/rq/project_rq.py::fetch_dem_and_build_channels_rq` | `fetch_dem_rq` to `build_channels_rq` | Strict | Channel build consumes fetched DEM. Failed-fetch and production retry test. |
| SWAT `wepppy/rq/swat_rq.py::run_swat_rq` | `_build_swat_inputs_rq` to `_run_swat_rq` | Strict | Execution consumes `TxtInOut`. Failed-build plus authenticated retry test. |
| Omni scenarios `wepppy/rq/omni_rq.py::run_omni_scenarios_rq` | Stage 1 to stage 2; last scenario stage to compile; compile to finalize | Strict | Later stages require a complete scenario result/summary set. Transitive stop plus admission retry test. |
| Omni contrasts `wepppy/rq/omni_rq.py::run_omni_contrasts_rq` | Contrast batch to next contrast batch | Tolerant serialization | Contrasts are independent; the edge only caps concurrent memory use. Prove a failed contrast releases the next batch without reading its output. |
| Omni contrasts same source | Last contrast batch to `_finalize_omni_contrasts_rq` | Tolerant finalizer | Aggregates direct contrast outcomes and publishes terminal status. Failed-contrast/finalizer test. |
| AgFields `wepppy/rq/ag_fields_rq.py::run_ag_fields_watershed_suite_rq` | Routing scheme to next scheme | Tolerant serialization | Comparison schemes are independently composable and output-isolated under `docs/schemas/output-scope-contract.md`; the edge only controls memory use. Prove later schemes run without reading failed output, including failure before dependent registration. |
| AgFields same source | Direct scheme jobs to `finalize_ag_fields_watershed_suite_rq` | Tolerant finalizer | Aggregates direct scheme statuses without consuming failed output. Failed-scheme/finalizer test. |
| Batch `wepppy/rq/batch_rq.py::run_batch_rq` | Direct leaf jobs to batch finalizer | Tolerant finalizer | Aggregates direct leaf statuses without consuming failed leaf artifacts. Failed-leaf/finalizer test. |
| Batch same source | Dynamic Omni final job appended to the batch finalizer | Tolerant finalizer | RQ 1.16.2 stores one tolerance flag for the finalizer's complete dependency set. A failed Omni final receipt may therefore release aggregation; an Omni final receipt blocked deferred by an earlier strict failure cannot release it. Early-Omni-failure evidence must prove failed aggregate status and authenticated retry cleanup of both deferred jobs. |
| Fork `wepppy/rq/project_rq.py::fork_rq` | Rerun `run_wepp_rq` to `_finish_fork_rq` | Tolerant finalizer | Reports a failed WEPP rerun and releases the profile-fork ownership claim in `finally`; it consumes no WEPP model outputs. Failed-WEPP/finalizer/claim-release test. |

## Status and persisted-state matrix

- No dependency or an empty dependency list enqueues normally.
- Required dependencies all `finished`: strict dependent may enqueue.
- Any required dependency queued, started, scheduled, or deferred: dependent
  remains deferred.
- Any required dependency failed, stopped, or canceled: strict dependent
  naturally remains deferred and never starts unless an existing owning contract
  explicitly cancels that never-started dependent, as for WBT controlled policy
  failures. Both deferred and canceled outcomes remain never-started.
- Tolerant finalizer or serialization prerequisites all `finished` or `failed`:
  RQ may release the dependent.
- Any present tolerant-finalizer or serialization prerequisite stopped or
  canceled blocks release. The explicit eager-release helper also fails closed
  on missing or malformed prerequisite records and exact-cardinality mismatch.
  Native RQ fan-out may release a terminal observer after an earlier successful
  prerequisite record expires; production workers retain those records for one
  week, and observers must not consume model outputs.
- Failed plus blocked-deferred registered tree, with no queued/started/scheduled
  member: aggregate is `failed`; a viable deferred-only tree is `deferred`.
- Legacy jobs retain their persisted `allow_dependency_failures` value. Source
  deployment cannot rewrite their semantics in place.

## Mixed-version rollout

Stop all producers before cutover. Do not deploy while an old producer can
create additional tolerant executable edges. Allow queued/started/scheduled old
trees to drain; do not mutate them. Reconcile safely associated deferred old
trees only through the existing authenticated ordinary-resubmission path. Once
no executable legacy tree remains, restart rq-engine, WEPPcloud, and every RQ
worker from the same revision, then run one strict-edge live smoke and one
failed-tree ordinary-retry smoke. Rollback uses the same producer stop/drain
boundary; never run mixed dependency constructors concurrently.
