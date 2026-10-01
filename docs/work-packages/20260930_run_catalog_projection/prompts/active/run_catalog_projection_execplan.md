# Implement and roll out the PostgreSQL run catalog


This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries,
Decision Log, and Outcomes & Retrospective current together with this package's
`tracker.md`. The current authorized task is forest1 application deployment,
following verified forest read cutover. Wepp1 is not authorized. No other active package
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

- [x] (2026-10-01 UTC) Operator authorized startup-fix commit/redeploy and a default-off environment-controlled sweep switch. Forest's enabled setting moves to its gitignored environment; no global enablement or new service.


- [x] (2026-09-30 UTC) Profile production and retain the 169.56-second baseline.
- [x] (2026-09-30 UTC) Record portable-project requirement and operator-endorsed architecture.
- [x] (2026-09-30 UTC) Author canonical specification, ADR, shared amendments, package, and rollout plan.
- [x] (2026-09-30 UTC) Obtain independent initial correctness/security findings.
- [x] (2026-09-30 UTC) Close all findings with independent post-fix contract PASS verdicts.
- [x] (2026-09-30 UTC) Operator authorized the reviewed package for implementation; forest deployment remains on hold.
- [x] M0: Acceptance checkpoint `db8e6be126fb231f16dd5e76f322d2b03089c10c` recorded before runtime edits.
- [x] M1 implementation: schema, repository, extractor, operator seed/status/compare and real SQL/file tests.
- [x] (2026-09-30 UTC) Initial additive migration/extractor/SQL tests: 11 file tests and 3 isolated-schema PostgreSQL tests passed.
- [x] (2026-09-30 UTC) Initial portable observer change passed 136 focused NoDb tests; implementation review remains open.
- [x] Clarification checkpoint `bf6b0584f7d9a4831576559e9354ff4bb53fa8b6`: both independent reviewers approved technical/operator readiness separation and connection-bound consumer proof before follow-on CLI edits.
- [x] Real file → observer → PostgreSQL → HTTP → Chromium chain passed in isolation; real authenticated SQL alias/shared-scope routes and a real isolated RQ sweep passed.
- [x] Broad pre-handoff run passed: 10,034 tests, 99 skipped, 12 subtests (started before final review fixes; latest targeted rerun required).
- [x] M2 implementation: portable observer and inventoried producer/process wiring; deployment startup/identity witnesses remain M5.
- [x] M3 implementation: serialized refresh, reconciliation, scheduler coalescing, CLI, SQL/Redis fault tests and isolated capacity measurements.
- [x] M4 implementation: SQL-only routes, freshness UI, authenticated scope regression and isolated file-to-browser evidence.
- [x] (2026-10-01 UTC) Independent bounded implementation and evidence-method reviews passed with all findings closed; requested pre-forest deployment hold reached.
- [x] (2026-10-01 UTC) Operator authorized forest steps 1–5; candidate committed, additive migration applied, consumer origin proof passed, shadow compared and postgres reads activated with browser evidence.
- [ ] Forest1 deployment authorized without fixed soak; backup/idle checks passed. After the divergent-branch guard stopped the first attempt, the operator explicitly authorized switching to existing master; canonical deployment resumed.
- [ ] M5 prerequisite/acceptance: production-equivalent producer/consumer mounts, startup, real queue/model capacity, browser-map/network timing, and stage-specific operator evidence.
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

Implementation review exposed serializer-envelope, grouped-identity,
descriptor-binding, archive-finalizer and public-error-boundary defects; their
fixes and independent dispositions are retained in the implementation review.
NoDb's existing commit cost dominates absolute observer latency, so incremental
timing requires matched producer-specific baselines. Counterbalanced raw samples
retain earlier adverse measurements; TTL has limited isolated timing margin.
Full NoDb convenience imports already reach Flask through BatchRunner/helpers;
the new portable seam does not add that dependency or require PostgreSQL.

Forest contains 463 registrations including old test records, not an 805-run
production scope. Of these, 368 have missing Ron/TTL and 95 are readable. The
principal authorized account returns 85 projects identically from all three
legacy/SQL surfaces. Two new dev-agent witness projects bring totals to 465/97.
Flask migration commands require an explicit app module in this container;
host static builds need repository virtualenv Python for Jinja2.


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

Implementation disposition (2026-10-01 UTC): accepted clarification checkpoint
`bf6b0584f7d9a4831576559e9354ff4bb53fa8b6` separates automated technical readiness
from mandatory stage-specific operator witnesses. URI hashes are not identity
proof; each eligible consumer needs the actual-connection nonce and mount tests.
Both reviewers returned bounded predeployment implementation PASS. The current
handoff stops before forest deployment; no M5 proof or package closure is claimed.


## Outcomes & Retrospective


Implementation now includes schema, data-only extraction, portable observer,
process/producer wiring, coalesced maintenance, CLI and SQL-only readers. Tests
use isolated PostgreSQL schemas and owned Redis queues, including actual file,
archive, SQL, HTTP and Chromium boundaries. The broad suite passed; final
targeted functional regression passed 487 tests, separate SQL/performance
validation passed 24 tests, and the final reader suite passed eight tests.
Correctness and security implementation reviews passed within predeployment scope.
Forest now runs migration `d30c91a7b802`, catalog writes, scheduled sweeps and
postgres reads. Live consumer origin/mount proof, source/SQL/HTTP parity and
browser table/map checks passed. Three 100-request authenticated series on the
actual 85-project scope passed, with p95 56–66 ms and concurrent checks.
M5 capacity/rollback remain open; fixed nonproduction waits are operator-waived.
Handoff evidence: `artifacts/2026-09-30_predeploy_validation.md`; operations and
developer integration: `docs/dev-notes/run-catalog-operations.md`. Runtime candidate
is committed as `3e6cbdcb9`; live evidence is in
`artifacts/2026-10-01_forest_deployment.md`. Forest-local schedule activation is
gitignored host environment configuration. Forest1's failed deployment and
containment are recorded separately; production acceptance and closeout are not claimed.


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
    wctl run-pytest tests/weppcloud/test_run_catalog_extractor.py tests/weppcloud/test_run_catalog_postgres.py tests/weppcloud/test_run_catalog_reader.py tests/weppcloud/test_run_catalog_cli.py tests/nodb/test_persistence_events.py tests/rq/test_run_catalog_rq.py
    wctl check-rq-graph
    wctl check-test-stubs
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1

The catalog tests now exist. Focused TTL, migration, scheduler, registration,
restore, notification and producer regressions supplement existing suites. Run applicable
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
Operator amendment: forest has one account and lacks the 805-run scope. Use
actual forest projects and controlled traffic; retain isolated scale evidence
separately and require representative host scale on the first eligible stage,
before wepp1 cutover if unavailable earlier. The operator authorized steps 1–5;
48-hour observation and full reconciliation still gate host promotion.
Operator amendment (2026-10-01 UTC): deploy forest1 now. Fixed 48-hour waits on
forest/forest1 are waived because both have one human operator and cannot
establish representative production traffic by waiting. Retain controlled
technical/deployment checks and label unobserved recovery windows honestly.
This authorizes the forest1 application, not its forest companion or wepp1.
Forest1 still checks out `feature/project-owned-config`; the canonical deploy
fetched a non-descendant upstream and correctly stopped before build/restart.
The existing master branch can preserve the feature branch, but switching
requires explicit operator authority. Its profiled fork/archive worker also
needs the documented separate activation because full deploy excludes it.

The initial forest1 attempt stopped safely at a divergent feature branch.
Preflight/backup passed and the operator then approved switching to existing
master. See the forest1 deployment run sheet for the subsequent runtime failure
and containment; the earlier branch blocker is resolved.
Forest1's first master rollout exposed package-import coupling: browse/download
import rq-engine auth, so module-level catalog initialization demanded secrets
those services intentionally do not have. Move initialization to ASGI lifespan,
not broader credential mounts. Read services were restored to the retained
previous image after the deploy's stability gate failed. The production image
also bakes a disabled sweep schedule with no host-local activation switch.

The operator approved switching forest1 to existing master. The resumed deploy
reached runtime but failed its stability gate on catalog-related browse/download
import failures. Both read services were restored to their exact previous image;
the canonical failure handler restored CAP and released its RQ fence. Catalog
schema/activation remain untouched. The operator subsequently approved committing
and redeploying the tested ASGI startup fix and a default-off host-local sweep
switch. Focused startup/scheduler/topology tests passed 33 cases. This closes
the activation-control gap without shipping a globally enabled schedule.
