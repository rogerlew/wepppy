# RQ operation webhooks: operation and recovery

Contract: [RQ-WH-01](../schemas/rq-webhook-contract.md). Admission and dispatch
are disabled by default. This implementation is undergoing acceptance; do not
activate until the work package records worker coverage, performance, real workflow
artifact parity and final correctness/security review evidence.

## Client use

The four admitted operations are `run-wepp`, `run-wepp-watershed`,
`prep-wepp-watershed`, and `culverts-wepp-batch`. Add `webhook_url` to the existing
JSON/form payload and an `Idempotency-Key` header containing 16–128 letters,
digits, periods, underscores or hyphens. Use a public DNS HTTPS destination on
port 443. Authentication and run/feature authorization are unchanged.

```http
POST /rq-engine/api/runs/RUN/CONFIG/run-wepp
Authorization: Bearer YOUR_CURRENT_TOKEN
Idempotency-Key: client-operation-0001
Content-Type: application/json

{"webhook_url":"https://receiver.example/operations"}
```

Retain the key and exact payload until the submission outcome is known. An
identical authorized retry returns the same operation; changed content conflicts.
A pending receipt is HTTP 202. Culvert receipt replay mints fresh browse credentials;
credentials are never stored in the callback receipt. A postcommit mint failure
preserves acceptance and returns a warning; repeat the same request with current
authorization. Never switch keys merely because a response was lost.

A callback contains `event: operation.completed`, its stable `event_id`, `job_id`,
operation/resource identifiers, timestamps, and `execution_status`. A `finished`
execution can contain domain failures caught by a task. Retrieve culvert results
and WEPP artifacts through existing APIs; the callback does not certify domain
success. No bearer credentials or signature are sent. Receivers must deduplicate
by event ID. Accepted delivery does not revalidate the submitting token.

Attempts have a 10-second total deadline, at most three attempts, and a one-hour
age limit. Transient retries wait 30 then 120 seconds, extended by bounded
Retry-After up to 300 seconds. Redirects, invalid TLS and forbidden destinations
are not followed. Delivery is best effort; continue to support status polling.
Other submission routes reject a supplied callback field before mutation.

Job hashes must still exist when completion is evaluated. Zero-TTL or early job
deletion can therefore leave notification unavailable even after model execution
finishes; existing RQ retention is not extended. Poll existing results as usual.
Attempt-generation gaps likewise suppress callbacks rather than reuse stale closure.

## Components and controls

`webhook_hooks.py` records server-owned lineage and lifecycle receipts;
`webhook_tracking.py` owns the Redis namespace and conditional event commit;
`webhook_settlement.py` evaluates generic immutable snapshots;
`webhook_dispatcher.py` independently evaluates and delivers;
`webhook_http.py` isolates each HTTPS exchange in a deadline-bounded subprocess.
No computation worker performs callback HTTP or recursive hierarchy evaluation.

The development Compose source is `docker/docker-compose.dev.yml`. Its
`rq-webhooks` profile contains `rq-webhook-dispatcher`, separate from computation
queues. It mounts source read-only and only needs the existing Redis credential.
The canonical production deployment entry remains `scripts/deploy-production.sh`;
this package does not authorize a production deployment.

Before local activation, record an environment-specific `RQ_WEBHOOK_ENVIRONMENT`,
the current Redis server `run_id` as `RQ_WEBHOOK_REDIS_RUN_ID`, and prove all
relevant workers advertise protocol `rq-wh-01` for that environment. Set
`RQ_WEBHOOK_INSTRUMENTATION=rq-wh-01` only after coverage acceptance. API admission
requires `RQ_WEBHOOK_ADMISSION=enabled`; dispatch separately requires
`RQ_WEBHOOK_DISPATCH=enabled` (or CLI `--dispatch`). Empty defaults do not activate.
Use installed `wctl` Compose wrappers; do not replace an unrelated service.

Sanitized inspection uses the same environment and Redis configuration:

```sh
wctl exec -T rq-webhook-dispatcher /opt/venv/bin/python -m wepppy.rq.webhook_dispatcher \
  --environment LOCAL_ENVIRONMENT --inspect JOB_ID
```

Inspection exposes safe host/fingerprint, state and bounded attempt metadata,
never the destination path/query. Raw destinations exist only in restricted Redis
intent until terminal delivery/expiry. Do not dump entire root records into logs.
Profile recording redacts callback values and drops unredactable structured raw
previews; playback omits captured callback intent.

## Pause, restart, restore and uncertain state

Disable admission to stop new accepted intents. Disable dispatch to stop starting
HTTP attempts; already started subprocesses may finish. Stopping the dispatcher
leaves persisted attempt-start records; recovery waits for its 30-second claim
lease. Interrupted attempts count toward the three-attempt limit. Age limits keep
advancing during downtime. Acknowledgment loss can cause a duplicate of the same
immutable event. Do not reset counters or manually replay into original URLs.

Before any backup restore, disable admission and dispatch and stop/drain existing
sender processes. A Redis process identity change invalidates external arming.
An in-place RESTORE into the same Redis process cannot be detected by run_id;
explicit disarming before that operation is mandatory. Copied stores must remain
disarmed. Review duplicate risk, retained ages and environment identity before
explicitly rearming against the current Redis process. Never flush shared Redis
or alter RQ job TTLs to repair notification state.

Incomplete publication, missing receipts or an unverified producer stay unknown;
they are not inferred finished. Known prepublication validation/lock failures can
retry the same reserved identity after owned staging cleanup. Ambiguous publication
preserves staged inputs and requires receipt reconciliation. Unknown tracking ages
out after 30 days to an unavailable outcome/tombstone; terminal audits remain for
30 further days. No completion is fabricated to clear a backlog.
