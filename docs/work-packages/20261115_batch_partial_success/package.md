# Batch and culvert partial-success results

Status: implemented in server and companion client; local acceptance and independent reviews complete. Created 2026-11-16 06:13 UTC.

## Purpose and scope

A batch with 32 successful runs and one 12-hour timeout must deliver the 32 valid results and report the omitted run. Cover ordinary batch and culvert finalizers, persistence, jobinfo/jobstatus serialization, artifact publication, and consumer guidance. Preserve genuine RQ leaf failures and sanitized tracebacks. The finalizer should finish normally when it publishes partial results; generic RQ tree status remains unchanged.

The operator approved the reviewed contract and implementation commits. Contract
checkpoint `390108471` and climate compatibility addendum `0aec93f1c` precede
runtime edits. Follow the [ExecPlan](prompts/active/implementation_execplan.md) and
[tracker](tracker.md) for implementation, test and review evidence. Deployment and
production requeues have not been performed.

The original mixed-success incident identity is immaterial: the operator revised
stream-order reduction to avoid its timeout trigger. Generic real-timeout
regression remains in scope; incident identification and recovery are excluded.

## Deliverables and authority

Promote the ratified additive `batch` schema into `docs/schemas/rq-response-contract.md` before implementation. Inventory related webhook, batch, artifact, and subsystem contracts and reconcile conflicts. The migration guide is consumer guidance, not another canonical authority.

Cover `wepppy/rq/batch_rq.py`, `culvert_rq.py`, `culvert_rq_pipeline.py`, `culvert_rq_manifest.py`, `job_info.py`, corresponding rq-engine polling routes, and tests. Inventory ordinary batch artifact/download surfaces before assuming the culvert ZIP convention applies. External client adoption in `Culvert_web_app/culvert_app/tasks/wepp_cloud_integration_task.py` is a required handoff and end-to-end acceptance dependency. Server-only completion must not imply client adoption.

## Security and complexity budget

Security impact: **high**, because public polling, downloads, and potentially queue dependencies are affected. Require independent security and correctness reviews before closure. Preserve authorization, path containment, traceback sanitization, restricted catalog disclosure, and token handling. Public summaries must not contain credentials or filesystem paths.

Use existing RQ, batch persistence, and artifact infrastructure only. No new service, datastore, queue, scheduler, or dependency. Exclude SSURGO retries, model parameterization changes, global status rewrites, and production recovery from this package's implementation scope.

## Acceptance

Both workflows pass the decision artifact's state matrix. A real short-timeout RQ test proves the 12-hour failure class: finalization runs, jobstatus/jobinfo expose partial success, an HTTP download succeeds, and semantic readback contains only successful run IDs across metrics and geometry. Finalizer failure and zero-success cases cannot advertise usable results. Normal project inspection agrees with polling and downloads. Complete independent reviews and regression gates; distinguish implemented, wired, environment validated, deployed, and incident repaired. Local fixtures do not establish production-equivalent full-model deployment acceptance.
