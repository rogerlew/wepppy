# Implement and roll out the PostgreSQL run catalog


This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries,
Decision Log, and Outcomes & Retrospective current together with this package's
`tracker.md`. The current authorized task is implementation and pre-deployment
validation, holding before forest deployment. No other active package
is being executed here.


## Purpose / Big Picture


After implementation, a user with hundreds of projects can open the runs table
or map without the web request opening every project on NFS. Project files stay
authoritative and remain usable by standalone WEPPpy without PostgreSQL. The
database holds a disposable catalog, refreshed after saves and reconciled after
missed notifications or offline edits. Deploy in the operator's order: forest,
forest1 test production, then wepp1, with evidence before each promotion.

The complete durable specification is
`docs/schemas/run-catalog-projection-contract.md`; its schema, state transitions,
limits, and host procedure are incorporated by reference. It is part of this
same repository change set. ADR rationale is
`docs/adrs/ADR-0078-run-catalog-projection.md`. The work is faithful extraction
with explicitly specified freshness behavior, not an unwired scaffold.


## Progress


- [x] (2026-09-30 UTC) Profile production and retain the 169.56-second baseline.
- [x] (2026-09-30 UTC) Record portable-project requirement and operator-endorsed architecture.
- [x] (2026-09-30 UTC) Author canonical specification, ADR, shared amendments, package, and rollout plan.
- [x] (2026-09-30 UTC) Obtain independent initial correctness/security findings.
- [x] (2026-09-30 UTC) Close all findings with independent post-fix contract PASS verdicts.
- [x] (2026-09-30 UTC) Operator authorized the reviewed package for implementation; forest deployment remains on hold.
- [ ] M0: Record acceptance checkpoint SHA before runtime edits.
- [ ] M1: Schema, repository, extractor, operator seed/status/compare, and direct tests.
- [ ] M2: Portable notification interface and complete process/producer wiring.
- [ ] M3: Serialized refresh, reconciliation, scheduler coalescing, CLI, and capacity proof.
- [ ] M4: Database-only routes, freshness UI, regression and browser evidence.
- [ ] M5: Forest acceptance, full cycle, rollback, and observation.
- [ ] M5: Forest1 production rehearsal, full cycle, rollback, and observation.
- [ ] M5: Wepp1 backfill/cutover, full cycle, original-workflow acceptance.
- [ ] Legacy-read retirement disposition, final independent review, and closure.


## Surprises & Discoveries


NoDb already calls a PostgreSQL timestamp helper after save, but the helper
imports the Flask app and constructs an engine per session. This is precedent
for best-effort mirroring, not an acceptable standalone integration boundary.
READONLY and TTL writers are separate from Ron dump, so a Ron-only hook misses
required metadata. The catalog forces Ron metadata for every run and performs
serial path resolution before starting its ten-worker metadata collector.

Forest1 hosts distinct roles: test-production web app and a companion batch
worker for forest. Hostname alone cannot identify the correct database/stack.
The scheduler already accepts per-task startup/jitter overrides, but currently
enqueues each due task without catalog-specific coalescing. A 15-second sweep
therefore needs admission coalescing to avoid growing the batch queue.

Initial review found a TTL CHECK/retention contradiction, null-policy CHECK
loophole, and finalizer-gated readiness without durable completion evidence.
Metadata availability now defines readiness, optional TTL failure clears stored
expiry, and the CHECK is null-safe. Security review requires descriptor-bound
source containment and pure grouped resolution, compatible remote sweep
consumers, and a public-safe catalog-specific RQ diagnostic boundary. The
scheduler's 30-second sleep also needs bounded wakeup for the 15-second task.


## Decision Log


Decision (2026-09-30 UTC, operator): projects remain portable without PostgreSQL;
use the proposed separate catalog and optional notification/reconciliation
architecture. Rationale: file authority and standalone use must survive this
performance improvement.

Decision (2026-09-30 UTC, operator): stage forest → forest1 → wepp1. Rationale:
validate integration on development and production-compose rehearsal before
production. This does not select the companion worker as forest1 acceptance.

Specification decision (2026-09-30 UTC, Codex; technical review passed): one projection
table with per-row revision and scheduling metadata, bounded existing-queue
refresh, and explicit stale-state presentation. No cursor/outbox table or new
service. Numeric limits and detailed UI policies are recorded in ADR-0078 and
must pass the contract checkpoint and measured capacity gate.

Review disposition (2026-09-30 UTC): Dirac and Ohm independently confirmed
contract-only PASS after two amendment rounds. All ten distinct findings were
corrected, including TTL constraints/readiness, source identity/pure resolution,
worker compatibility, polling/identifier/rollback safety, and startup readiness.
Detailed operator ratification and runtime evidence are not supplied by review.


## Outcomes & Retrospective


Specification and executable sequence authored; independent correctness and
security contract reviews passed with all findings closed. Runtime is unchanged;
no implementation test, migration, deployment, or incident resolution is claimed.
Next are detailed operator ratification and the accepted checkpoint, not activation.
Review-session documentation lint, relative link targets, and whitespace checks
passed. Spelling preview left unrelated existing tracker prose unchanged.


## Context and Orientation


`wepppy/weppcloud/routes/user.py` contains runs queries, path construction,
parallel Ron/TTL extraction, and the three JSON surfaces. The browser code is
inline in `wepppy/weppcloud/templates/user/runs2.html`. Database models and
registration live in `wepppy/weppcloud/app.py`; existing timestamp integration
is `wepppy/weppcloud/db_api/__init__.py`. Alembic migrations live under
`wepppy/weppcloud/migrations/versions/`.

`wepppy/nodb/base.py` owns locked file commits and READONLY markers;
`wepppy/nodb/core/ron.py` owns names/scenarios/map state. TTL persistence is
`wepppy/weppcloud/utils/run_ttl.py`. Creation, fork, sync, deletion, and migration
writers span `wepppy/microservices/rq_engine/`, `wepppy/rq/project_rq*.py`,
`wepppy/rq/run_sync_rq.py`, and maintenance tools. Read their nearest AGENTS
before edits; build the writer inventory rather than assuming routes are all
writers. Worker startup and `wepppy/tools/scheduler.py` are separate process
boundaries. Schedule configuration is `docker/scheduled-tasks.yml`.

A projection is a database copy of a small subset of authoritative file values.
A dirty revision means those values need re-reading, not that an old event
payload should be replayed. Reconciliation revisits even clean rows to discover
offline/crash-gap edits. Advisory locks serialize projection writers in
PostgreSQL without holding file locks or changing NoDb writer authority.


## Plan of Work


M0 ratifies the detailed behavior. Read the canonical specification, NoDb and
TTL amendments, existing RQ response/CSRF contracts, and the package decision
artifact. Obtain two independent read-only contract reviews and close all
medium/high findings. Populate correctness/security artifacts with actual
review evidence, not author assertions. Record explicit operator disposition
of detailed stale/pending presentation and limits. When committing is authorized,
make the contract set a standalone ancestor and record its SHA. No runtime
edits precede that checkpoint. Retain a corpus covering supported legacy Ron
encodings, empty fields, missing/invalid data, and separate READONLY/TTL states.

M1 creates additive migration and the deployment-only package
`wepppy/weppcloud/run_catalog/` with repository, extractor, and CLI entry point.
Keep shared table metadata separate from importing the full Flask app; bind
app and worker sessions through the deployment adapter. Implement state/type
constraints, seed/rebuild incarnation fencing, and current/legacy extraction
without NoDb construction or file writes. Real PostgreSQL and filesystem tests
must establish schema and value parity, null-safe TTL transitions, pure grouped
resolution, descriptor-bound containment, and unchanged directory/link inventories.
Existing routes remain legacy.

M2 adds `wepppy/nodb/persistence_events.py`, frozen commit records, explicit
observer installation, and bounded deployment SQL notifications. Replace the
direct database import in dump while preserving existing modification mirrors.
Implement timestamp-only staging and catalog-write modes. Wire registration,
Ron, READONLY, TTL, lifecycle completion, workers, and maintenance. Failed SQL
after a file commit must leave the file saved, report mirror failure, and not
implicitly register anything. Exercise deployment configuration in subprocesses
and prove standalone import/save paths cannot load Flask or database libraries.

M3 implements per-run publication serialization, revision acknowledgment,
per-row reconciliation progress, and the global sweep/concurrency boundary.
Implement remaining CLI subcommands and one bounded task in
`wepppy/rq/run_catalog_rq.py`. Reuse scheduler per-task delay/jitter controls
and add opt-in atomic coalescing without changing existing task scheduling.
Bound scheduler wakeup by the next catalog due time. Implement the reserved
prefixed UUID exception and public-safe job-info/jobstatus outer error handling,
including failures before deserialization; test unrelated polling compatibility.
Update `wepppy/rq/job-dependencies-catalog.md`, generated graph, and live tree
evidence. Measure queue delay, source-read capacity, and full-reconciliation
completion under sustained writes; do not add queues or services without a
failed acceptance result and a recorded scope decision.

M4 switches the three JSON routes through an explicit read mode. Build database
rows without invoking model properties that probe paths. Preserve authorization,
payload/sort/pagination behavior and add the specified scoped freshness fields.
Update inline UI and accessible status messaging without changing mutation
authority. Database errors remain explicit; there is no automatic NFS fallback.
Tests must fail on any project-I/O helper invocation in database mode, including
admin/map routes. Live HTTP/browser comparisons establish actual wiring.

M5 follows canonical spec section 11 exactly. Forest proves all producer and
standalone/fault paths. Forest1 proves the production image, secrets, migrations,
two no-argument canonical deployments, existing login/CAPTCHA/RQ/DEVAL checks,
and rollback. Wepp1 repeats shadow/backfill/compare/preflight before read cutover
and tests the original large account. Each stage retains 48 healthy hours and
a full reconciliation cycle. Seven further healthy days after wepp1 precede
the reviewed legacy-read retirement disposition. Do not accelerate calendar
observation by repeatedly invoking a sweep or calling unit tests a soak test.
Gate every eligible queue consumer before admission; drain/remove catalog-only
work before incompatible worker rollback. Public serializers must retain
redaction for the lifetime of retained catalog job records, including terminal
failures; test anonymous polling after rollback independently of queue draining.


## Concrete Steps


Run development validation from `/home/workdir/wepppy` (or the target checkout's
actual path), using installed `wctl`. Commands below for new modules become
available only after their implementation; missing commands are not existing
infrastructure failures during specification authoring.

    wctl run-pytest tests/nodb/test_base_boundary_characterization.py tests/nodb/test_base_unit.py tests/nodb/test_base_misc.py
    wctl run-pytest tests/weppcloud/routes/test_runs_catalog_contract.py
    wctl run-pytest tests/weppcloud/test_run_catalog.py tests/nodb/test_persistence_events.py tests/rq/test_run_catalog_rq.py
    wctl check-rq-graph
    wctl check-test-stubs
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1

New tests are proposed filenames, not claims they exist. Add focused TTL,
migration, scheduler, and producer tests beside existing suites. Run applicable
stubtest commands for changed public APIs. Inspect new code with
`python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
and non-blocking quality observability; run the existing vulture gate if this
work removes legacy code. Record unrelated failures instead of fixing them.

After the schema exists and notifications/sweeps are enabled, future operator
invocations through the installed preset include:

    wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog status --json
    wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog seed --limit 50 --apply --json
    wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog reconcile --limit 50 --apply --json
    wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog compare --run-id <registered-integer-id> --json
    wctl exec -T weppcloud python -m wepppy.weppcloud.run_catalog preflight --json

Expect bounded counts, explicit classifications, no secret/path exposure in
public responses, and nonzero exit for failed readiness. Seed/reconcile are
repeatable; do not infer full completion from one 50-row batch.

Before forest1/wepp1 activation inspect hostname, current preset and canonical
deployment plan. From the target `/workdir/wepppy`, read `docker/README.md`
and `scripts/deploy-production.sh`, then use:

    hostname
    pwd
    wctl rq-info --detailed
    scripts/deploy-production.sh --print-plan

Actual deploy and migration follow spec section 11 and active-job gates. Do not
use raw Docker workflows or the forest1 companion-worker skill to activate the
test-production application. Never disclose resolved secrets in evidence.


## Validation and Acceptance


For a real registered test project, rename and change scenario, map, readonly,
and TTL through normal authorized writers. Record committed file values, SQL
values, authorized HTTP payload, and browser rendering within the 60-second
target. Repeat through a worker and maintenance process. Update files offline
without notification and prove the scheduled full reconciliation finds them
within 24 hours. Confirm a disconnected database cannot undo a successful file
save and that recovery repairs the catalog without replaying values into files.

Exercise concurrent refresh/invalidation, deletion, projection-row replacement,
restored databases, abandoned sweeps, and source read errors using actual SQL
and filesystem boundaries. Show a read error does not imply deletion and that
known-invalid Ron still follows the omission policy. Verify all scope/state
dimensions in canonical spec section 12, including unauthorized aliases and
legacy projects. No fixture-only or mock-only closeout is sufficient.

Performance evidence includes at least 100 sequential authenticated requests
per catalog/map surface on an 805-run scope plus concurrent readers, p95/p99,
payload/TTFB/browser timing, and zero request-side project filesystem calls.
Model-job capacity and added save latency must meet specified limits. Require
real production-equivalent users/groups/mounts/umask/process startup at every
host boundary, not just tests inside a developer shell.


## Idempotence and Recovery


Schema/backfill are additive. Seed inserts only missing projection rows, refresh
is version-fenced, reconciliation resumes through SQL timestamps, and registration
deletion cascades. No command synthesizes ownership or deletes projects. Explicit
read rollback returns to legacy latency while preserving useful state. Stop
overloaded sweeps without erasing dirty state. Adapter rollback uses a known-good
application revision so the old modification mirror is not silently lost.

Never drop the catalog, clear unrelated queues, or restore project files from
SQL as a rollback. Candidate recovery requires a fresh comparison/preflight and
healthy observation window. An uncompleted external gate remains pending; do
not mark the package complete to end a session.


## Artifacts and Notes


Retain `producer_inventory.md`, source compatibility cases, per-host run sheets,
redacted comparison manifests, raw timing summaries, queue/freshness metrics,
rollback evidence, independent reviews, and revisions in package `artifacts/`.
Do not put account emails or raw credentials into general diagnostic output.
Retain actual job IDs and internal source details only in appropriately scoped
operator evidence; public responses remain bounded and path-free.


## Interfaces and Dependencies


The portable boundary is `ProjectCommit` plus registration/notification in
`wepppy/nodb/persistence_events.py`. The deployment-only package
`wepppy/weppcloud/run_catalog/` supplies `repository.py`, `extractor.py`,
`adapter.py`, `service.py`, and `__main__.py` (organize narrowly; do not split
further without need). Reuse existing PostgreSQL/SQLAlchemy, JSON and hashlib,
Redis/RQ, scheduler, coherent-read helpers, Flask-Migrate, and UI conventions.
No new dependency, secret transport, daemon, or deployment topology is allowed.

Revision note (2026-09-30 UTC): initial plan authored from operator-approved
architecture and host sequence; detailed behavior and defaults await the M0
checkpoint. No implementation or deployment is claimed.
Execution authorization (2026-09-30 UTC, operator): execute this reviewed package
and hold when ready to deploy to forest. Implement M1–M4 and isolated validation;
do not migrate the live application database, restart/recreate services, enable
sweeps, or switch live readers. Host acceptance/soak gates remain M5 work.
