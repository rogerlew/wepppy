# Local Forest validation dispatch

User authorized restarting the local stack and submitting the synced project.
Host: `forest`, development Compose, not `forest1` or production.
Run: `/wc1/runs/ve/ventilated-gag`, config `canada-wbt-mofe`.

`wctl rq-info` reported zero queued/executing jobs before `wctl restart`.
Restart exited 0; Redis/Postgres healthy, batch workers listening, rq-engine
health returned HTTP 200. Worker/source SHA256 matched for the changed builder:
`f431ac15cb27d6b66f2c59798bb9fc5f5758814e25b31b59ac284f53fee8f6af`.

Authenticated setup discovery, pipeline and readiness returned HTTP 200.
Readiness identified `rq_engine_run_omni` as dependencies-satisfied. The operation
schema lookup returned 404 despite its presence in readiness and OpenAPI;
record this discovery-metadata inconsistency as a follow-up, not a run blocker.
The published OpenAPI route and existing route parser confirmed submission shape.
Used a short-lived run-scoped service bearer; no token retained.

At 2026-09-18 18:51:00 UTC, POST
`/api/runs/ventilated-gag/canada-wbt-mofe/run-omni` returned HTTP 202:

```json
{"job_id":"8c88742d-defd-4b3e-ac33-a3efd622dd42","message":"Job enqueued.","status_url":"/rq-engine/api/jobstatus/8c88742d-defd-4b3e-ac33-a3efd622dd42"}
```

Submitted saved definitions unchanged: uniform low, moderate, high; prescribed
fire; thinning canopy/ground cover 40%/75% and 65%/85%. Persisted dependency tree
and scenario run-state list were empty before submission. Initial status poll
returned HTTP 200, queued. Correlation ID:
`omni-mofe-segment-eligibility-20260918-forest`.

Await user notification of completion/error; then inspect child outcomes and
generated/prepared OFE artifacts. Enqueue success is not acceptance evidence.
