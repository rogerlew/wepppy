# M1 inventory and compatibility plan

Date: 2026-11-16. Source baseline: df8b5249c70a3d98fd27f2b3b3b16ac1d96deb52.
Read-only source inventory; no runtime changes or production access performed.

## Confirmed shared failure class

Treating aggregate RQ success as the only indicator of usable results loses
successful siblings when a leaf times out. Conversely, caught leaf errors can
leave RQ execution finished despite failed domain results. Metadata-only success
and fixed archive existence also cannot prove usable results.

| Consumer/boundary | Evidence and disposition |
| --- | --- |
| Ordinary dispatch/finalizer | batch_rq.py already permits failed dependencies; freezes only retry-eligible selection, but finalizer classifies all project leaves; confirmed cohort mismatch for the proposed selected-only outcome |
| Ordinary two-stage and Omni | batch-task-boundary-contract.md and dynamic Omni links; preserve stage handoffs and wait for Omni descendants; success metadata alone insufficient |
| Culvert dispatch/finalizer | culvert_rq_pipeline.py already permits failed dependencies; finalizer scans stray directories and trusts metadata, catches packaging failure; confirmed publication gaps |
| Culvert ZIP | culvert_rq_manifest.py packages all runs, including failed output; file symlinks followed; new derivative requires success-only membership and member authorization checks |
| Polling | job_info.py and job_routes.py aggregate children; additive root object must preserve generic status and feature projections |
| Browse download | browse/_download.py existing batch and culvert file routes can serve attempt ZIPs under existing auth; no endpoint needed |
| External client | /workdir/Culvert_web_app/culvert_app/tasks/wepp_cloud_integration_task.py aborts failed status and resume probe discards failed handles; metrics and geometry independently infer run IDs from ZIP directories; both confirmed consumers |
| Culvert retry/finalize | culvert_routes.py single-run retry replaces run tree and standalone finalize returns its own polling handle; must invalidate current publication and freeze new source receipts |
| Webhook | execution status deliberately differs from domain outcome; verified contract unaffected, clarification only |
| Restricted catalog polling | projection must exclude new private manifests and batch object; validation pending |
| Normal inspection/archive | visible attempt records required, normal status surface must reconcile; runtime evidence pending |

Search scope: named workers, job serialization/routes, batch/culvert download
routes, external integration task, corresponding schema contracts and targeted
tests. Other clients consuming generic RQ status retain legacy behavior; no
system-wide client migration is claimed.

## Compatibility and regression plan before data writes

Add a versioned derivative artifact and public `batch` object. Do not rename
existing CSV/Parquet columns or mutate scientific inputs. Preserve legacy ZIP,
metadata and diagnostic downloads. Freeze selected-only ordinary cohort; a
zero-selection retry has no new result bundle even if historical results exist.
A baseline-WEPP-only ZIP is proposed; WATAR/Omni output downloads remain existing
project surfaces. This choice and prep-only no-results semantics require exact
operator ratification before runtime work.

Validate both polling endpoints and batch jobinfo, retained public projections,
ordinary directive/optional-module/Omni combinations, source identity retention,
retry/finalize races and hard process death. Read actual ZIP manifest and every
delivered Parquet/GeoJSON; compare IDs across the real client's metrics,
hillslopes and channels. Run a short-timeout real RQ worker and authorized HTTP
download, plus hostile path/member cases and archive/restore byte preservation.
The source excerpt confirms hillslope geometry uses subcatchments.WGS.geojson;
there is no separate hillslopes.WGS.geojson requirement.

## Environment and retained limitations

The external Culvert repository exists and contains unrelated dirty changes;
preserve them. Its adoption is possible locally but has not begun. The named
33-run SSURGO batch remains an all-failed control. No evidence identifying the
separate 32-success/one-timeout incident was found in this package; a synthetic
real-timeout test can prove the failure class but cannot claim incident recovery.
Production deployment and recovery remain out of scope.

Precedents: batch-task-boundary-contract.md supplies existing failure-tolerant
terminal observation and visible handoff artifacts; rq-webhook-contract.md
supplies execution/domain separation; artifact observability and generated
artifact validation standards supply retention and semantic readback rules.
No new queue, service, dependency or model parameterization is proposed.
