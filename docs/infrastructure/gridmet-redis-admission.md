# GridMET Redis admission on Forest

This runbook applies to `forest.bearhive.internal`, using the installed `wctl`
development preset and `docker/docker-compose.dev.yml`. It does not deploy
production, forest1, registry images, or Kubernetes. The
[contract](../schemas/gridmet-redis-admission-contract.md) defines behavior;
[ADR-0050](../adrs/ADR-0050-gridmet-redis-admission.md) and
[ADR-0061](../adrs/ADR-0061-gridmet-persistent-queue-recovery.md) own parameter rationale.

## Activation

First verify `hostname`, a clean source tree and pushed candidate SHA, and the
installed wctl script's `COMPOSE_FILE_RELATIVE`. Use `wctl docker compose config
--services` to verify the selected topology. Inspect Redis health through
`redis_connection_kwargs(RedisDB.LOCK)` inside a worker; never print connection
kwargs, full environment dumps, or secret values.

Back up only lines beginning `GRIDMET_REDIS_ADMISSION_` from gitignored
`docker/.env` into a mode-0600 temporary file. Replace those lines with:

```dotenv
GRIDMET_REDIS_ADMISSION_ENABLED=true
GRIDMET_REDIS_ADMISSION_LIMIT=4
GRIDMET_REDIS_ADMISSION_WAIT_TIMEOUT_SECONDS=900
GRIDMET_REDIS_ADMISSION_LEASE_SECONDS=300
GRIDMET_REDIS_ADMISSION_QUEUE_TTL_SECONDS=60
GRIDMET_REDIS_ADMISSION_POLL_INTERVAL_SECONDS=0.25
GRIDMET_REDIS_ADMISSION_KEY=wepppy:gridmet:admission:v1
```

Run `wctl docker compose config --quiet`. Inspect only the seven named values
from a parsed Compose render to verify propagation; the complete render may
contain secrets. Source code is mounted, but environment changes require
container recreation. Verify workers are idle before recreating the
GridMET-capable default and batch pools:

```bash
wctl docker compose up -d --no-deps rq-worker rq-worker-batch
wctl docker compose exec -T rq-worker python -c 'from wepppy.climates.gridmet.admission import GridMetAdmissionConfig; print(GridMetAdmissionConfig.from_env())'
wctl docker compose exec -T rq-worker-batch python -c 'from wepppy.climates.gridmet.admission import GridMetAdmissionConfig; print(GridMetAdmissionConfig.from_env())'
```

Confirm fresh processes agree on source SHA and configuration, both containers
remain running, and six default/four batch workers register. The fork/archive
pool does not execute climate builds. Other development services inherit the
common values on their next recreation; do not restart unrelated services for
this bounded worker activation.

## Diagnostics and acceptance

Snapshot state includes queued and active counts, a zero-based waiting position,
and elapsed wait. Position is not an ETA. Healthy waiters have no age deadline.
`WAIT_TIMEOUT_SECONDS` remains a legacy compatibility/fingerprint value and does
not expire waiting requests. Transient Redis transport errors log recovery
attempts and retry; authentication, malformed state, conflicting policy and lost
lease remain terminal errors. Inspect the effective operational namespace without
renewing or removing live owners. Expired entries are pruned on observation.

For operational diagnostics, resolve the worker's actual environment policy:

```bash
wctl docker compose exec -T rq-worker python -c 'from dataclasses import asdict; from wepppy.climates.gridmet.admission import GridMetAdmissionConfig, GridMetAdmissionController; c = GridMetAdmissionConfig.from_env(); print("disabled" if c is None else asdict(GridMetAdmissionController(c).snapshot()))'
```

This also reports the operational limit correctly when the namespace has never
been used. The probe CLI's defaults describe its isolated test policy.

Use `tools/gridmet_admission_probe.py --help` for bounded probe commands. All
mutating probes require a unique test namespace and refuse the default and
effective operational namespaces. Never flush Redis or delete keys by pattern.
Run at least six contenders across two worker containers with test limit two;
observe a nonempty queue, peak exactly two, FIFO sequence, and empty final
state. Repeat with a killed waiter and holder. Use the short valid test lease
for crash probes; public HTTP acceptance needs the normal 300-second lease.

For example, give each `worker` a distinct `--worker-id` and redirect its JSON
lines to a separate file. Run three in each container, alongside an observer:

```bash
wctl docker compose exec -T rq-worker python tools/gridmet_admission_probe.py worker --key "$GRIDMET_TEST_KEY" --worker-id rq1 --hold-seconds 3
wctl docker compose exec -T rq-worker-batch python tools/gridmet_admission_probe.py observe --key "$GRIDMET_TEST_KEY" --duration-seconds 45 --require-peak --require-queued
```

The test key must start `wepppy:gridmet:admission:acceptance:` and include the
candidate SHA and UTC timestamp. Default test policy is limit two, lease 30,
queue TTL nine and poll 0.05; the legacy wait value is 120 seconds and has no
effect on queue waiting. Keep policy identical across
all contenders. Combine their files and the observer file with `summarize
--key "$GRIDMET_TEST_KEY" --contenders 6 --minimum-containers 2 --input FILE`
(repeat `--input` for each file). The summary checks contender identities,
namespace, FIFO, occupancy, completion, and cleanup.

Run one public GridMET client acquisition with its own unique namespace while
the other container observes admission. Require valid output plus empty final
queue/active state. Upstream failure can demonstrate cleanup but is not a
successful download. Do not submit a batch. Record candidate SHA, container
identities, exact probe arguments, server time, peak/order, cleanup and expiry
durations in the active work package's Forest integration artifact.

The real-client invocation is `public --key "$GRIDMET_PUBLIC_TEST_KEY"
--lease-seconds 300 --timeout-seconds 180`; run `observe` from the other
container with the same key and lease, and require at least one queued or active
sample. The public mode requests precipitation for one location and year and
checks its public DataFrame result. A forced timeout may leave a killed owner's
lease until expiry; record that honestly and observe final reclamation.

The guarantee is a ceiling on live Redis permits. A lease cannot forcibly stop
an already-running upstream request after suspension or partition; clients
reject detected stale ownership before continuing or publishing results.

## Rollback and tuning

Set `GRIDMET_REDIS_ADMISSION_ENABLED=false` in the same environment file and
recreate the same two idle worker services with the activation command. Verify
fresh `GridMetAdmissionConfig.from_env()` returns `None`. On deployment failure,
restore the backed-up admission lines and repeat the same checks. Restore the
accepted enabled values after any acceptance rollback rehearsal.

Do not delete an operational namespace while any enabled client can own it.
Idle metadata expires automatically. A policy change requires draining all
participating clients and updating them together; mixed live settings fail.
Operators should assess queue depth, transport recovery, upstream retries, lease loss,
and throughput before revising the ADR and deploying new values. A separate
registry build, openwepp.org deployment, and batch validation remain the
operator's later phase.


## Recovery signals

Healthy recovery retains live FIFO order, completes releases and leaves no
abandoned owners beyond heartbeat/lease expiry. A Redis outage can leave a
request waiting until recovery or explicit job cancellation. Active HTTP still
requires a confirmed unexpired lease. Increasing the legacy wait value cannot
fix Redis transport delays. Never bypass capacity checks or delete live keys.

A recurrence of poll/release transport aborts, duplicate grants, occupancy above
the limit, terminal malformed-state errors or unreclaimed owners requires a new
incident investigation citing the
[queue recovery package](../work-packages/20260909_gridmet_queue_recovery/package.md).
Record pre/post failure counts, queue depth and recovery logs without credentials.
Historical infrastructure latency for the September 9 incident is not proven.
