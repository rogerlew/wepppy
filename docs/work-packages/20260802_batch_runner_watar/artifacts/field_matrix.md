# SURF-02C Batch Runner WATAR Contract Matrix

**Date**: 2026-08-03 UTC
**Authority**: Canonical finite contract for SURF-02C after the accepted
GOV-00A-M1F standalone ancestor

| Obligation | Normative behavior | Evidence required |
| --- | --- | --- |
| Directive identity | One Batch Runner directive uses slug `run_watar`, label `Run WATAR`, the existing `TaskEnum.run_watar` glyph, and a boolean enabled state. | BatchRunner state/snapshot and actual generic directive render/controller tests. |
| UI persistence | The generic Batch Runner directive control saves `run_watar` through the existing `run_directives` mapping and reloads the stored state. No WATAR-specific endpoint or payload field is added. | Route snapshot/update tests and Jest serialization/reload assertions. |
| Eligibility | `run_watar` is applicable only when the leaf run contains `ash.nodb`. Absence of `ash.nodb` excludes it from completion proof and execution. | Classifier tests for WATAR and non-WATAR leaves, including old serialized batches. |
| Upstream dependency | Eligible WATAR requires non-null `run_wepp_hillslopes` and `run_wepp_watershed` timestamps and a non-single-storm climate. Batch Runner calls `ensure_hillslope_interchange`, `ensure_totalwatsed3`, and `ensure_watershed_interchange` in order, then requires `H.pass.parquet`, `H.wat.parquet`, and `totalwatsed3.parquet`; any failure leaves WATAR unset. | Call-order, timestamp, single-storm, missing/interrupted interchange tests plus generated logs. |
| Inputs | Batch WATAR consumes the leaf's persisted `Ash` fire date, initial white/black depths, model, transport mode, rasters, and advanced parameters copied from `_base`. No Batch Runner defaults or scientific conversions are introduced. | Focused invocation test and generated leaf state/output evidence. |
| AshPost | The user-visible `Run WATAR` stage includes `Ash.run_ash`, `AshPost.run_post`, and catalog publication. Data-producing leaves require current versioned datasets/docs. Legitimate no-data leaves complete when AshPost records null return-period state and updates the catalog without normal datasets/version/docs. There is no separate AshPost directive. | AshPost failure, data-producing, and no-data tests plus generated post/catalog evidence. |
| Completion | `TaskEnum.run_watar` is timestamped only by the existing Ash pipeline after AshPost succeeds. Batch Runner does not timestamp it directly. | Test where AshPost raises and timestamp remains absent; successful pipeline test. |
| Retry | Retry selection is timestamp-authoritative. Missing/failed WATAR on an otherwise WEPP-complete leaf is retry eligible and reruns WATAR without rerunning completed upstream stages. A timestamp-complete WATAR leaf is skipped without recurring artifact/version/catalog audits. Full workspace reset remains controlled only by `Remove existing files`. | Retry classifier/worker tests and disposable batch rerun evidence. |
| Existing leaves | No selective `ash.nodb` resync is added. Changes made to `_base` after leaf creation require the existing `Remove existing files` full-rerun path. | Documentation assertion and regression that ordinary retry preserves leaf Ash inputs. |
| Failure reporting | WATAR/AshPost exceptions propagate through the existing leaf failure metadata, status stream, and final batch failure summary. They are not swallowed or converted to success. | Leaf worker/finalizer failure tests. |
| Old state | Post-load normalization inserts missing `DEFAULT_TASKS` keys as enabled, allowing old batches to disable/save/reload `run_watar`; eligibility still requires `ash.nodb`. | Old-state snapshot, update, persistence, and reload regression. |
| Locking | Batch WATAR locks sorted `climate`, `landuse`, and `watershed` roots with archive preflight, bounded Batch Runner retries, and post-acquisition recheck. Leaf-job exclusivity owns `ash/` writes; no nested `run_ash_rq` call occurs. | Lock order/contention/archive-form/no-nested-worker tests. |
| Security and paths | Existing Batch Runner admin/JWT/CSRF checks, safe leaf ids, run-root confinement, active-job guards, and NoDb/NoDir lock contracts remain unchanged. | Existing route/security suites, focused path/lock regression where touched, and security review. |

## Exclusions

Ash formulas, defaults, units, thresholds, calibration, transport-mode tokens,
standalone WATAR form fields, AshPost schemas, RQ response shapes, auth policy,
new queue topology, selective base-to-leaf Ash resync, and unrelated Batch
Runner stages are outside SURF-02C.
