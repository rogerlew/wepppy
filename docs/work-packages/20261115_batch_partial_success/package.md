# Batch and culvert partial-success results

Status: M1 inventory and concrete contract proposal prepared; ratification pending. Created 2026-11-16 06:13 UTC.

## Purpose and scope

A batch with 32 successful runs and one 12-hour timeout must deliver the 32 valid results and report the omitted run. Cover ordinary batch and culvert finalizers, persistence, jobinfo/jobstatus serialization, artifact publication, and consumer guidance. Preserve genuine RQ leaf failures and sanitized tracebacks. The finalizer should finish normally when it publishes partial results; generic RQ tree status remains unchanged.

Execution is at the preimplementation contract checkpoint. Follow the [ExecPlan](prompts/active/implementation_execplan.md), [tracker](tracker.md), and [draft contract decision](artifacts/20261116_contract_decision.md). Runtime changes, deployment, and production requeues have not been performed. The user requested a contract-first package and migration-guide update; exact contract ratification and implementation remain future milestones.

The investigated batch `1f2933b8-12a7-48cc-b508-5f2719baa8a7` had 33 SSURGO failures and is an all-failed control. Resolve the separate mixed-success timeout incident identity during implementation; do not conflate the two.

## Deliverables and authority

Promote the ratified additive `batch` schema into `docs/schemas/rq-response-contract.md` before implementation. Inventory related webhook, batch, artifact, and subsystem contracts and reconcile conflicts. The migration guide is consumer guidance, not another canonical authority.

Cover `wepppy/rq/batch_rq.py`, `culvert_rq.py`, `culvert_rq_pipeline.py`, `culvert_rq_manifest.py`, `job_info.py`, corresponding rq-engine polling routes, and tests. Inventory ordinary batch artifact/download surfaces before assuming the culvert ZIP convention applies. External client adoption in `Culvert_web_app/culvert_app/tasks/wepp_cloud_integration_task.py` is a required handoff and end-to-end acceptance dependency. Server-only completion must not imply client adoption.

## Security and complexity budget

Security impact: **high**, because public polling, downloads, and potentially queue dependencies are affected. Require independent security and correctness reviews before closure. Preserve authorization, path containment, traceback sanitization, restricted catalog disclosure, and token handling. Public summaries must not contain credentials or filesystem paths.

Use existing RQ, batch persistence, and artifact infrastructure only. No new service, datastore, queue, scheduler, or dependency. Exclude SSURGO retries, model parameterization changes, global status rewrites, and production recovery from this package's implementation scope.

## Acceptance

Both workflows pass the decision artifact's state matrix. A real short-timeout RQ test proves the 12-hour failure class: finalization runs, jobstatus/jobinfo expose partial success, an HTTP download succeeds, and semantic readback contains only successful run IDs across metrics and geometry. Finalizer failure and zero-success cases cannot advertise usable results. Normal project inspection agrees with polling and downloads. Complete independent reviews and regression gates; distinguish implemented, wired, environment validated, deployed, and incident repaired. This scaffold cannot close implementation scope.
