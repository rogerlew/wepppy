# Implement and prove cluster-wide GridMET Redis admission

This ExecPlan is a living document. Maintain it in accordance with
`docs/prompt_templates/codex_exec_plans.md`, including the `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective`
sections. Update this file and
`docs/work-packages/20260907_gridmet_redis_admission/tracker.md` at every
stopping point.

## Purpose / Big Picture

WEPPpy currently limits multiple-interpolated GridMET NetCDF downloads to four
processes inside one climate build. Each RQ worker process or Kubernetes pod can
create its own pool, and point requests have no shared cap, so a deployment can
send many more concurrent requests than intended. After this work, deployments
may explicitly enable a Redis-backed FIFO admission queue shared by every
GridMET client. Operators can see waiting and active state, clients fail in
bounded and diagnosable ways, dead clients do not permanently consume capacity,
and deployments without the enabling environment variable behave exactly as
they do now.

The implementation is not complete merely because unit tests pass. Completion
requires deploying the exact reviewed commit and the ratified variables to the
`forest` development Compose stack, then having an agent prove across
independent containers that observed concurrent holders never exceed the test
limit and that a real public GridMET client request participates. Do not run a
batch. The operator will test a batch later after a separate registry build and
deployment to `openwepp.org`.

## Progress

- [x] (2026-09-07 15:53 UTC) Assessed current point/grid acquisition, retry,
  process-pool, Redis configuration, and deployment boundaries.
- [x] (2026-09-07 15:53 UTC) Scaffolded the work package and live Forest gate.
- [x] (2026-09-07) Execution preflight: clean master at
  `583e6870c639999515035423f133e5925dae2da5`, Forest hostname, installed dev
  wctl preset, healthy standalone Redis 8.6.2, and 54 baseline tests passing.
- [x] (2026-09-07 16:22 UTC) Write canonical admission contract and ADR-0050;
  independent correctness/security contract reviews pass with all medium
  findings resolved. Standalone ancestor commit precedes runtime edits.
- [ ] Implement admission state/configuration and deterministic tests.
- [ ] Wire all GridMET clients and callers and update deployment documentation.
- [ ] Complete focused/full validation and independent reviews.
- [ ] Commit and push the reviewed candidate to `master`.
- [ ] Deploy exact candidate plus variables to Forest and verify containers.
- [ ] Run and record Forest cross-container and real-client probes.
- [ ] Close and archive the package; leave openwepp.org batch testing deferred.

## Surprises & Discoveries

- Observation: the NoDb contract-first standard requires two independent
  contract reviews before the standalone checkpoint commit. Both reviews are
  assigned; runtime edits remain pending that gate.
- Observation: Forest source-mounts this checkout. Feature activation remains
  disabled during implementation; container recreation and acceptance follow
  the reviewed, pushed candidate.

- Observation: the existing `ProcessPoolExecutor(max_workers=4)` is local to a
  single multiple-interpolated build.
  Evidence: `ClimateGridmetMultipleBuildService._retrieve_gridmet_netcdfs()` in
  `wepppy/nodb/core/climate_gridmet_multiple_build_service.py` constructs the
  executor for each build.
- Observation: recent failures occurred in the single-location path, which has
  no local parallel pool but can run once in every active RQ worker.
  Evidence: `wepppy/climates/gridmet/gridmet_singlelocation_client.py` calls
  `request_single_location_json()` directly.
- Observation: `requests` read timeouts bound socket inactivity, not necessarily
  total streamed-response wall time.
  Evidence: both GridMET clients use `stream=True` and iterate response chunks.
  Admission therefore needs lease renewal and an explicit overall wait budget.

## Decision Log

- Decision: use a dedicated `wepppy.climates.gridmet.admission` module.
  Rationale: Redis queue mechanics, configuration, errors, and observation are
  a separate concern from response validation and DataFrame/NetCDF conversion.
  Date/Author: 2026-09-07, Roger Lew and Codex.
- Decision: construct nothing when the enable variable is absent or false.
  Rationale: Redis coordination is an opt-in client capability, not a new
  implicit dependency for every library consumer.
  Date/Author: 2026-09-07, Roger Lew and Codex.
- Decision: track FIFO queued tickets and expiring active leases.
  Rationale: a counter cannot provide fair admission, position, stale-waiter
  recovery, or enough state to diagnose admission timeouts.
  Date/Author: 2026-09-07, Roger Lew and Codex.
- Decision: start Forest at a shared limit of four and use a separate unique
  test namespace/limit for destructive-free acceptance.
  Rationale: four preserves the prior per-build ceiling while making it global;
  the isolated test must not alter the normal Forest admission state.
  Date/Author: 2026-09-07, Codex; requires ADR ratification during execution.

## Outcomes & Retrospective

Not yet implemented. At closeout, summarize code behavior, automated evidence,
Forest evidence, actual values, residual risks, rollback result, and the exact
deferred openwepp.org batch step without claiming Kubernetes acceptance.

## Context and Orientation

`wepppy/climates/gridmet/acquisition.py` owns single-location retry and payload
validation. `wepppy/climates/gridmet/gridmet_singlelocation_client.py` exposes
precipitation, wind, and full-timeseries DataFrame clients.
`wepppy/climates/gridmet/client.py` downloads and validates gridded NetCDF
files. `wepppy/nodb/core/climate_gridmet_multiple_build_service.py` downloads
eight measures for every requested year through a four-process local pool.
GridMET is also reached indirectly from
`wepppy/nodb/core/climate_build_helpers.py`, Daymet, and PRISM clients.

`wepppy/config/redis_settings.py` is the only connection configuration source
to use. Admission belongs in `RedisDB.LOCK`; do not create a new Redis database
number or parse credentials independently. A waiting ticket represents one
HTTP attempt waiting for permission. An active lease represents a unique owner
currently allowed to contact/stream from GridMET. A lease expires unless its
owner renews it, preventing a killed process from leaking capacity forever.

Forest is `forest.bearhive.internal`, serving the development stack described
by `docker/docker-compose.dev.yml` and `docker/AGENTS.md`. It is not `forest1`,
WEPPcloud production, or Kubernetes. Repository code is source-mounted there,
but changed environment values require container recreation. Use the installed
`wctl` preset and inspect its effective Compose command before acting; do not
invent another deployment workflow.

## Plan of Work

### Milestone 1: Contract and parameterization checkpoint

Before implementation, add a canonical GridMET acquisition/admission contract
under `docs/schemas/` or the nearest existing durable climate documentation.
Define absent, false, true-valid, true-invalid, Redis-unavailable, empty queue,
populated queue, stale queue, active, expired, cancelled, and ownership-conflict
states. Define that `GridMetAdmissionConfig.from_env()` returns `None` when
`GRIDMET_REDIS_ADMISSION_ENABLED` is absent or false. Unknown or malformed
boolean text must fail explicitly rather than being treated as true or false.
When enabled, validate positive limit/timings and timing relationships before
making an outbound request.

Create the next available ADR in `docs/adrs/` following
`docs/standards/parameterization-adr-standard.md`. Ratify or revise the initial
Forest values in `package.md`. Explain why an aggregate limit of four is the
starting value, how the wait/lease/queue TTL values interact with current 60
and 120 second read timeouts, what signals permit later tuning, and who owns
that decision. Commit this contract checkpoint separately before behavior code.

Acceptance: documentation lint passes; independent contract/correctness review
finds no unresolved medium/high issue; no runtime behavior has changed.

### Milestone 2: Dedicated admission module

Create `wepppy/climates/gridmet/admission.py`. Define immutable, pickle-safe
configuration containing primitive values only; explicit admission exceptions;
a controller; an ownership-token permit context manager; and an immutable
snapshot containing at least ticket state, zero-based or one-based position
with clear semantics, queued count, active count, limit, and elapsed wait.
Construct the Redis connection lazily through `redis_connection_kwargs()` for
`RedisDB.LOCK`. Do not store a live Redis connection in configuration passed to
child processes.

Use versioned, namespaced keys. Implement atomic Lua operations that use Redis
`TIME`, not client wall clocks, to prune expired queue tickets/leases, allocate
a monotonic queue sequence, inspect state, transition only the live FIFO head
when capacity exists, renew only the matching ownership token, and release or
cancel only owned state. Ensure the key design works atomically on the deployed
Redis topology. Bound connection/socket operations. Enabled Redis failures fail
closed with a distinct exception and useful sanitized context.

Waiting clients refresh a bounded queue-ticket liveness record. Poll with
jitter to avoid synchronized Redis load. Active clients renew leases while
streaming. Do not use bare `INCR`/`DECR`, an unexpiring set, Redis pub/sub for
correctness, or an unbounded blocking call. No log may contain credentials or a
full GridMET query URL.

Add deterministic tests using an isolated real Redis service for atomic
cross-process behavior. Mocks may cover parsing/error translation but cannot be
the only evidence for the concurrency boundary. Test FIFO, maximum occupancy,
independent process clients, killed waiter/holder reclamation, foreign-token
renew/release rejection, cancellation, timeout cleanup, Redis outage, and
server/client clock disagreement.

Acceptance: a multiprocessing test observes queued state, reaches its expected
parallelism, never exceeds its limit, and ends with no waiting or active entry.

### Milestone 3: HTTP-client integration and timeout accounting

Add an optional keyword-only admission configuration to the public
single-location functions and `retrieve_nc()`. Keep default `None`. Resolve
environment configuration once at the orchestration/client boundary specified
by the contract; do not instantiate at import time. Ensure direct clients can
explicitly pass `None` or a config. Do not add a global singleton carrying a
fork-unsafe Redis socket.

Acquire for each HTTP attempt. Hold the permit while `requests.get()` and the
response stream are active. Renew safely during streaming and release before
payload/NetCDF validation that no longer occupies the upstream connection, and
before every retry backoff. Re-enter FIFO for a retry so one failing request
cannot monopolize capacity. Carry one monotonic overall admission deadline
across retries; do not multiply a 900-second wait by three unnoticed. Preserve
the current payload limits, atomic NetCDF publication, response closing,
transient-status handling, and public DataFrame contracts.

Propagate the immutable config through observed GridMET, precipitation
monthlies, PRISM/Daymet GridMET wind, SNOTEL supplementation, and the
multiple-interpolated downloader. Retain its local four-process pool. Audit all
imports/calls with `rg`; record the inventory in the validation artifact. If a
public surface or stub changes, update it and run the repository stub gates.

Add tests proving disabled clients perform zero Redis construction/I/O; enabled
point/grid attempts admit and release; validation and backoff do not hold a
permit; exceptions clean up; retries requeue; indirect call paths propagate;
and process-pool arguments pickle successfully.

Acceptance: focused client and climate tests pass, and failure messages clearly
distinguish admission wait exhaustion, Redis unavailability, lost lease, and
upstream GridMET acquisition failure.

### Milestone 4: Deployment wiring, diagnostics, and probe

Pass every `GRIDMET_REDIS_ADMISSION_*` value through the common WEPPpy
environment in `docker/docker-compose.dev.yml` so every GridMET-capable Forest
worker receives the same values. The committed development Compose default is
disabled. Do not edit production or worker-only Compose files. Update
`docs/configuration-reference.md` and the appropriate Docker/operator runbook
with semantics, values, diagnostics, activation, and rollback. Do not place
credentials in these variables.

Add a bounded reusable probe under `tools/` or `scripts/` that can use a unique
Redis namespace, create concurrent holders from independent processes, sample
queue/active snapshots, and emit machine-readable summary containing configured
limit, observed peak, whether queued state was seen, acquisition order, cleanup
counts, and pass/fail. It must refuse the canonical operational key unless an
explicit safe mode requires read-only inspection. It must always attempt
ownership-safe cleanup and never flush a Redis database.

Provide a second probe mode or documented invocation that runs a real public
GridMET client acquisition with admission enabled and a unique acceptance key,
then proves queue and active state are empty. Keep the request bounded and do
not print its full query URL.

Acceptance: default-off and enabled development Compose renders pass; probe unit tests pass;
security review confirms safe key handling, timeouts, cleanup, and logging.

### Milestone 5: Review, commit, and Forest deployment

Run focused and full validation and complete independent correctness, QA/code,
and security artifacts. Resolve every medium/high finding. Commit and push the
reviewed candidate to `master` before live deployment, and record its full SHA.
Do not deploy an uncommitted tree.

On `forest`, verify hostname, repository path, clean worktree, active wctl
preset resolves to `docker/docker-compose.dev.yml`, Redis health, affected
service names, and current revision. Pull the exact candidate. Back up only the relevant non-secret lines
of gitignored `docker/.env` to a permission-restricted temporary file. Add the
ratified variables from `package.md`. Render Compose and confirm the values
reach all GridMET-capable RQ services without exposing Redis credentials.
Recreate only those services with the supported `wctl`/Compose path. Verify
container health, worker registration, exact source revision, and effective
values from fresh processes.

If deployment fails, restore the prior environment lines, recreate the same
services, verify admission resolves to `None`, and retain sanitized failure
evidence. Do not flush Redis, clear RQ, restart unrelated stateful services, or
move to another host.

Acceptance: Forest runs the exact pushed candidate and all intended workers
resolve the same enabled config and shared key.

### Milestone 6: Forest concurrency and real-client acceptance

Run the reusable probe concurrently from at least two independent Forest
Compose containers or disposable containers on the same Compose network. Use a
unique key containing the candidate SHA and timestamp, with test limit two and
at least six contenders. Hold permits long enough to observe both active and
queued states. Require all contenders to finish, observed peak exactly two,
zero limit violations, FIFO acquisition among continuously live tickets, and
zero queued/active entries afterward. Kill one queued contender and one active
holder in separate repetitions and prove reclamation within the contracted
bounds. Record Redis server time and container identities, but no credentials.

Then execute one bounded, actual public single-location GridMET client request
from a Forest worker container with an isolated acceptance key. Sample state
from another container while it runs. Require evidence that the client entered
queued or active admission, returned a valid public result, released its permit,
and left zero queue/active state. If the upstream is unavailable, record the
upstream failure separately; the admission proof still requires evidence of
acquire/release and must not be relabeled a successful end-to-end download.

Finally inspect the canonical operational pool for plausible empty or active
state and no expired debris. Exercise rollback by rendering/recreating with the
enable variable false if doing so is safe, or document a precise non-disruptive
rehearsal; restore the ratified enabled Forest state before closeout. Save
evidence in `artifacts/<date>_forest_integration.md`.

Acceptance: independent containers demonstrably share one ceiling, the real
GridMET client is wired, cleanup/expiry work, Forest remains healthy, and no
batch was submitted.

## Concrete Steps

Work from `/workdir/wepppy` on Linux/Forest and from the repository root in any
other development environment. First inspect rather than assume commands:

    git status --short --branch
    git pull --ff-only
    rg -n "retrieve_nc|retrieve_historical_(precip|wind|timeseries)|request_single_location_json" wepppy tests
    sed -n '1,220p' wepppy/config/redis_settings.py
    wctl docker compose config --services

After adding tests, run the discovered focused modules, including at minimum:

    wctl run-pytest tests/climates/gridmet/test_download_clients.py --maxfail=1
    wctl run-pytest tests/nodb/test_climate_build_helpers.py --maxfail=1

Add explicit admission and live-Redis test modules and include their exact paths
here once named. Validate configuration and documentation:

    wctl docker compose config --quiet
    wctl doc-lint --path docs/work-packages/20260907_gridmet_redis_admission
    wctl doc-lint --path docs/configuration-reference.md
    git diff --check
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

Run relevant stub/API gates if signatures are represented by stubs. Before
candidate handoff run:

    wctl run-pytest tests --maxfail=1

Record exact pass counts rather than copying counts from another revision. The
Forest commands must be filled in after inspecting the installed wctl preset
and probe interface; include exact invocations and compact output in the Forest
artifact. Never place a Redis password on a command line or in an artifact.

## Validation and Acceptance

Automated validation must cover configuration state independently from Redis
state: environment absent, false, malformed, and enabled; Redis queue absent,
empty, populated, stale, and hostile/foreign ownership; single and multiple
processes; success, retry, cancellation, timeout, and crash. At least one test
must use the real Redis implementation without mocking the atomic boundary.

Forest validation is a required deployment integration test, not an optional
smoke. It must demonstrate two or more simultaneously active holders while
never exceeding the configured test limit, observe a non-empty waiting queue,
and finish empty. It must span at least two independent containers so a
process-local semaphore would fail the test. A separate actual GridMET public
client call proves wiring. Container identity, candidate SHA, effective config,
Redis snapshots, peak, order, expiry timing, final cleanup, and rollback status
are required evidence.

Package completion does not require and explicitly prohibits a batch test.
Nothing in Forest acceptance proves Kubernetes deployment behavior. Closeout
must identify registry build, openwepp.org deployment, and batch validation as
the operator's separate subsequent phase.

## Idempotence and Recovery

All automated and live probes use unique keys and ownership tokens, tolerate
safe rerun, and clean only their own state. Expiration provides recovery after
a killed process. Never use `FLUSHDB`, wildcard deletion, or the canonical
operational key for destructive testing. On interruption, inspect the unique
key, wait for its documented expiry, and delete only that exact test namespace
after verifying no process still owns it.

Forest environment edits must be line-scoped and backed up without secrets in
the committed record. Reapplying the same variable set and recreating the same
services is idempotent. Rollback disables/removes the feature variables and
recreates only affected services. Code rollback uses the prior known-good SHA.

## Artifacts and Notes

Keep concise evidence under
`docs/work-packages/20260907_gridmet_redis_admission/artifacts/`. Required
artifacts are listed in `tracker.md`. Sanitize Redis URLs, passwords, full
environment dumps, and full GridMET query URLs. It is acceptable to record
hostnames, container names, job/request correlation tokens, key namespaces,
counts, durations, commit SHAs, and exception classes.

## Interfaces and Dependencies

Use the repository's existing `redis` Python dependency and
`wepppy.config.redis_settings.redis_connection_kwargs(RedisDB.LOCK)`. Do not add
a package. The final exact names may be refined in the contract checkpoint, but
the public shape must remain equivalent to:

    @dataclass(frozen=True)
    class GridMetAdmissionConfig:
        enabled: bool
        key: str
        limit: int
        wait_timeout_seconds: float
        lease_seconds: float
        queue_ttl_seconds: float
        poll_interval_seconds: float

        @classmethod
        def from_env(cls) -> GridMetAdmissionConfig | None: ...

    @dataclass(frozen=True)
    class GridMetAdmissionSnapshot:
        state: str
        position: int | None
        queued: int
        active: int
        limit: int
        waited_seconds: float

    class GridMetAdmissionController:
        def acquire(self, *, request_kind: str, deadline: float | None = None) -> GridMetPermit: ...
        def snapshot(self, ticket_or_permit_id: str) -> GridMetAdmissionSnapshot: ...

Public GridMET client functions accept
`admission: GridMetAdmissionConfig | None = None` as a keyword-only parameter.
If orchestration resolves environment configuration, it passes the resulting
immutable value explicitly. `GridMetPermit` supports ownership-safe release and
renewal and is usable as a context manager. Exceptions subclass the existing
GridMET acquisition error where that preserves the canonical caller contract,
while retaining distinct concrete types for diagnosis.

Revision note (2026-09-07 15:53 UTC): initial ExecPlan created from the
operator-ratified Redis, queue visibility, opt-in, Forest deployment, and
post-package Kubernetes batch boundaries.
