# Isolate Fork and Archive Work on One Serial RQ Queue

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to
date as work proceeds. Maintain this plan according to
`docs/prompt_templates/codex_exec_plans.md` and update
`docs/work-packages/20260803_fork_archive_serial_queue/tracker.md` at every
stopping point.

## Purpose / Big Picture

WEPPcloud users can currently submit a project fork, create an archive, or
restore an archive and receive an RQ job ID. RQ is the Redis-backed job system;
its queue name decides which worker process may start a job. All three actions
currently enter the broad `default` queue, so multiple hosts and worker
processes may traverse the same NAS-backed run storage concurrently.

After this change, the three top-level filesystem-heavy jobs enter one queue,
proposed as `fork-archive`, and exactly one worker process dispatches them in
the environment's designated stack. In production, that sole consumer runs on
otherwise-idle wepp3 rather than the wepp1 application host. A second accepted
job visibly remains queued until the first is terminal. Ordinary default and
batch model work continues independently.
The fork and archive consoles tell users that queue wait is normal, while RQ
Admin views and `wctl rq-info` show the queue to operators.

This plan is implementation scope, not a surrogate. It is not complete merely
because compose files contain a service or a route contains a queue name. It is
complete only after live job origins, one-worker placement, two-job
serialization, UI guidance, safe restore dispatch, observability, Forest
cutover/rollback, and a bounded wepp3 canary are demonstrated.

## Progress

- [x] (2026-08-04 05:38Z) Read repository and subsystem instructions, the NFS
  evidence, queue/worker code, compose variants, UI surfaces, operator
  listings, graph artifacts, and focused tests.
- [x] (2026-08-04 05:38Z) Scaffolded the package, tracker, this ExecPlan,
  contract draft, security-review placeholder, infrastructure link, and root
  tracker entry without editing production implementation.
- [x] (2026-08-04 05:50Z) Validated every new/touched Markdown file and all
  five baseline compose render paths; the worker-only render requires the
  contract-mandated `RQ_REDIS_URL` input.
- [x] (2026-08-04 05:57Z) Removed the repurposed HPC compose from the worker
  implementation matrix and retained it as an explicit non-consumer check.
- [x] (2026-08-04 06:09Z) Moved the proposed sole production consumer from
  wepp1 to otherwise-idle wepp3 and recorded the dedicated, dependency-minimal
  wepp3 topology and preflight requirements.
- [x] (2026-08-04) Registered SURF-03A/GOV-00A-M1G, amended the four composed
  owners, recorded starting revision
  `d63df477c887d59e813542a1c2f22730a7f75faa`, and recorded the operator's
  explicit approval of the final matrix and the later queue-specific
  cancellation amendment: queued authorized users; started Admin/Root only.
- [x] (2026-08-04) Dispositioned two independent checkpoint reviews and obtained
  post-fix confirmation with no unresolved High or Medium findings.
- [ ] Commit the checkpoint as a standalone ancestor and record its revision.
- [ ] Add failing focused regressions for queue identity, worker topology,
  operator listings, UI guidance, and dispatch-time safety.
- [ ] Implement the route, compose, listing, UI, documentation, and graph
  changes against the accepted ancestor.
- [ ] Pass focused and broad local validation and live two-job serialization.
- [ ] Execute Forest drain-first cutover and rollback acceptance.
- [ ] Complete security/correctness review, then execute a guarded wepp3 canary
  and observation window.

## Surprises & Discoveries

- Observation: archive restore belongs in the serial queue even though the
  initial request said “fork/archive”; it recursively removes and rewrites the
  same NAS-backed run tree.
  Evidence: `restore_archive_rq` in
  `wepppy/rq/project_rq_archive.py` iterates the run root, removes every entry
  except `archives`, and extracts the selected ZIP.

- Observation: changing only the enqueue sites and named deployment files
  would leave operator-facing surfaces incomplete.
  Evidence: `wepppy/rq/job_listings.py`, `wepppy/rq/job_summary.py`, and
  `tools/wctl2/commands/rq.py` all default to only `default` and `batch`.

- Observation: the HPC compose is being repurposed and is not a deployment
  target for this worker.
  Evidence: operator direction on 2026-08-03 PDT superseded the initial
  discovery assumption that the `hpc` wctl selector remained supported.

- Observation: allowing normal wepp2 worker-stack startup to activate the
  dedicated service would create two production consumers and defeat global
  serialization.
  Evidence: the August 3 incident note records a default-queue fork executing
  on wepp2 while wepp1 and wepp2 shared Redis and the NAS.

- Observation: queue wait lengthens two correctness windows that were small
  under near-immediate dispatch.
  Evidence: `fork_project` creates/registers the destination before enqueue;
  `restore_archive` checks locks at request time, while `restore_archive_rq`
  currently begins destructive removal without repeating that lock check.

- Observation: fresh RQ heartbeat is not sufficient health evidence for this
  worker.
  Evidence: both the archive incident and full-output fork showed live
  heartbeats while child processes were in `rpc_wait_bit_killable`.

## Decision Log

- Decision: Propose queue name `fork-archive`, service name
  `rq-worker-fork-archive`, and worker-pool size `1`.
  Rationale: the names state the bounded workload and match existing
  `rq-worker`/`rq-worker-batch` conventions without adding configurable queue
  policy.
  Date/Author: 2026-08-04 / Roger Lew and Codex; explicitly approved.

- Decision: Include `fork_rq`, `archive_rq`, and `restore_archive_rq`; exclude
  synchronous delete and downstream undisturbify jobs.
  Rationale: the included tasks perform the direct copy/archive/restore NAS
  traversal; the excluded paths do not share the same top-level resource role.
  Date/Author: 2026-08-04 / Roger Lew and Codex; explicitly approved.

- Decision: Run the sole production consumer on otherwise-idle wepp3, with
  wepp1 and wepp2 as non-consumers.
  Rationale: wepp3 has the production NFS mount and provides a host-level
  recovery/fencing boundary without exposing wepp1 application services to a
  blocked NFS worker. The worker-only service must be opt-in so normal wepp2
  deployment cannot start it.
  Date/Author: 2026-08-04 / Roger Lew and Codex; explicitly approved, with the
  exact compose mechanism subject only to checkpoint review for conformance.

- Decision: Treat default queue listings, drain-first cutover, and rollback as
  deliverables.
  Rationale: a queue invisible to normal operator tools or removed before its
  jobs drain is not an operable production feature.
  Date/Author: 2026-08-04 / Codex.

## Outcomes & Retrospective

The discovery milestone is complete. The proposal is technically small at the
enqueue and compose layers, but safe delivery requires a bounded cross-owner
contract amendment, restore dispatch revalidation, fork-destination
characterization, operator-list updates, and a two-stage rollout. No production
code or compose configuration has been changed. Update this section after each
milestone and compare measured NAS/queue behavior with the purpose above.

## Context and Orientation

The three public actions are implemented in
`wepppy/microservices/rq_engine/fork_archive_routes.py`. Each creates an RQ
`Queue` without a name, which means the queue is `default`, then enqueues a
worker exported from `wepppy/rq/project_rq.py`. The underlying fork copy lives
in `wepppy/rq/project_rq_fork.py`; archive creation and restore live in
`wepppy/rq/project_rq_archive.py`.

The primary development stack is `docker/docker-compose.dev.yml`. Forest test
production uses `docker/docker-compose.prod.yml`. Production wepp1 layers
`docker/docker-compose.prod.wepp1.yml` over that base. A separate worker-only
stack, `docker/docker-compose.prod.worker.yml`, is used on wepp2. A dedicated
`docker/docker-compose.prod.wepp3.yml` will define the sole production
`fork-archive` consumer. Because the production hosts share
Redis DB 9 and the NAS, “one worker” means one consumer across all hosts, not
one per compose file.

Wepp3 has the production NFS mount and otherwise runs no containers. The
proposed production implementation uses the wepp3-specific compose and starts
only that named service. It must not depend on `rq-worker`, `rq-worker-batch`, `f-esri`, or
`weppcloudr`. A normal wepp2 `wctl up -d` must not activate it. Wepp1's layered
application compose must also remain a non-consumer.

`docker/docker-compose.dev.hpc.yml` is being repurposed. It is not a supported
deployment target for this package and must not receive the dedicated worker.

The current main and batch services use RQ worker pools of six and four
processes. Production invokes `docker/rq-worker-startup.sh <count> <queue>`;
development invokes `rq worker-pool` directly. The dedicated service should
follow each file's local pattern with count `1` and use the native WEPPpyo3
interchange entrypoint. The wepp3 service mounts `/wc1` and only geodata and
secret files demonstrated necessary by focused startup/task-import evidence.
It must not mount the Docker socket or unrelated Discord, provider, Flask, or
Postgres credentials.

The fork UI is rendered by
`wepppy/weppcloud/templates/controls/fork_console_control.htm` and driven by
`wepppy/weppcloud/static/js/fork_console.js`. The archive UI is rendered by
`wepppy/weppcloud/templates/controls/archive_console_control.htm`; its source
client is `wepppy/weppcloud/static-src/js/archive_console.js` and built copy is
`wepppy/weppcloud/static/js/archive_console.js`. Static explanatory text should
live in the shared control templates so embedded and full-page consoles agree.
Dynamic text may supplement it but must not be the only guidance.

Operator queue defaults appear in `wepppy/rq/job_listings.py`,
`wepppy/rq/job_summary.py`, and `tools/wctl2/commands/rq.py`. The latter also
contains a registry-repair Python snippet with a hard-coded queue tuple.
RQ-engine Admin endpoints and the WEPPcloud `/rq/info-details` page consume the
job-listing default. These must change together.

The queue wiring catalog and generated JSON are
`wepppy/rq/job-dependencies-catalog.md` and
`wepppy/rq/job-dependency-graph.static.json`. Any enqueue-site edit requires
`wctl check-rq-graph` and, when drift is expected,
`python tools/check_rq_dependency_graph.py --write`.

This behavior composes the verified SURF-03 archive console, SURF-04 fork
console, SURF-07 RQ dashboard cancellation, and SURF-17 RQ info-details
contracts. Under
`docs/standards/contract-first-change-standard.md`, implementation cannot begin
until the enhancement is registered, explicitly approved, independently
reviewed twice, dispositioned, and committed as a standalone ancestor.

## Plan of Work

### Milestone 1: Ratify the bounded enhancement before implementation

Finalize
`docs/work-packages/20260803_fork_archive_serial_queue/artifacts/2026-08-04_contract_decision.md`
so it contains the starting revision, exact queue/service names, all three
enqueue sites, worker placement, UI wording, restore dispatch behavior,
fork-destination behavior, compatibility, security, tests, rollout, and
rollback. Register proposed SURF-03A/GOV-00A-M1G in the Pure UI child register
as a bounded enhancement composing SURF-03, SURF-04, SURF-07, and SURF-17 without
advancing or reopening their unrelated behavior.

Amend the four concise owner contracts with the exact normative delta and mark
implementation conformance pending. Obtain two independent read-only reviews,
record raw findings and disposition, and obtain explicit operator approval of
the final matrix. Commit only the checkpoint/register/contract/review documents
as a standalone ancestor. Record its full revision in this ExecPlan and the
tracker. Do not add tests or implementation to that commit.

This milestone is accepted when the ancestor exists and both reviews have no
unresolved high or medium finding. If exact archive cancellation, revision
conflict detection, or fork catalog behavior cannot be agreed, stop at this
milestone rather than guessing.

### Milestone 2: Lock the queue and topology contracts with focused tests

Extend `tests/microservices/test_rq_engine_fork_archive_routes.py` so the queue
stub records constructor arguments and proves all three enqueue sites use exact
queue name `fork-archive`. Retain existing assertions for task, args, timeout,
auth, response, and active-job behavior.

Extend rq-engine cancellation tests before implementation. For origin
`fork-archive`, prove an authorized non-Admin user can cancel only through a
fail-closed queued removal; a queued-to-intermediate handoff race and a started
job both return forbidden without issuing a stop command; Admin and Root may
cancel after start. Prove other origins and Culvert compatibility are unchanged.

Add focused Docker tests under `tests/docker/unit/` that prove dev and Forest
define one dedicated consumer and the wepp1 and wepp2 compose files do not
define one. Prove the wepp3-specific compose defines one process consuming only
`fork-archive`, with minimal required volumes/secrets/startup gate and no
Docker socket or dependency on normal workers, `f-esri`, or `weppcloudr`. Keep
the repurposed HPC compose a non-consumer. Update existing WEPPpyo3 and worker-
startup contract tests where the new service is a consumer.

Update wctl, job-listing, rq-engine Admin, and RQ info-details tests so default
queue order is `default`, `batch`, `fork-archive`. Add and test
`wctl rq-info --service rq-worker-fork-archive`; retain the current default
service when the option is omitted. Document host-local Compose, PID, and
process-state inspection for wepp3 so D-state triage does not depend on Redis.
Add exact render assertions
for the user guidance in `tests/weppcloud/routes/test_pure_controls_render.py`
and focused client assertions only if dynamic queued-state text changes.

This milestone is accepted when the new tests fail for the current precise
reasons: unnamed default queues, missing worker services, omitted operator
queue, absent guidance, and missing queue-specific cancellation enforcement.

### Milestone 3: Implement the smallest accepted cutover

Define one module constant in
`wepppy/microservices/rq_engine/fork_archive_routes.py`, then construct
`Queue(FORK_ARCHIVE_QUEUE, connection=redis_conn)` at the fork, archive-create,
and restore enqueue sites. Preserve submission authorization, response payloads,
timeout, arguments, job metadata, archive markers, and downstream jobs.

In `job_routes.py` and `cancel_job.py`, implement the accepted queue-specific
cancellation boundary. The non-Admin path must atomically/fail-closed remove a
job only while it remains queued and must never call the started-job stop path;
intermediate/handoff/started states return forbidden. Admin and Root retain
started cancellation. Jobs from other origins, including Culvert jobs, retain
their existing behavior.

Add `rq-worker-fork-archive` to dev and Forest using their adjacent worker
conventions and one worker process. Add a wepp3-specific compose with only the
dedicated service, its external Redis, minimal proven inputs, image, and NFS
mount contracts. Do not add the service to wepp1 or wepp2 compose. Render
default and explicitly targeted compose configurations
before starting containers.

Update the three operator queue-default implementations and their descriptions.
Regenerate the dependency graph/catalog so all three routes show queue
`fork-archive`. Update `docker/README.md`, `wctl/README.md`, the relevant RQ
operator guide, and the NFS note with the new topology and D-state/head-of-line
triage.

Add concise template guidance. The accepted wording should state that
fork/archive/restore work runs one job at a time, a request may remain queued
before it starts, and execution uses the project state available when the
worker begins. Restore guidance must state its destructive effect and the
approved restriction on edits while queued.

Apply the accepted restore dispatch-time revalidation immediately before any
destructive run-root removal. Characterize whether the existing
fork-destination registration is visible in the Runs catalog or directly
loadable while queued. Preserve the readiness-gated fork-console link. If the
accepted contract requires a fix outside the registered boundary, stop and
amend/review the checkpoint before editing that surface.

This milestone is accepted when focused tests pass, graph artifacts are
current, all compose variants render, and no out-of-scope route/worker behavior
changes.

### Milestone 4: Prove local serialization and safe rollback

Start the development stack with the dedicated service. Confirm `wctl rq-info
--detail` shows `fork-archive` and one registered worker. Use disposable run
copies, not valuable projects. Submit a long-running representative fork or
archive, then a second in-scope action. Capture job IDs, origins, statuses,
worker names, and times showing the first `started` and the second `queued`.
After the first finishes, show that the second starts on the same one-worker
service. Confirm an ordinary default-queue job can start independently.

Exercise queued cancellation as an authorized project user, started
cancellation rejection as the same user, and started cancellation success as
Admin/Root. Confirm other queues retain existing behavior and no destination or
archive marker is left stale. Exercise
a queued restore with a dispatch-time conflict matching the accepted contract
and prove it fails before removing current files. Confirm UI reload recovery and
queued-state guidance for both consoles.

For rollback, put the three submission routes behind the ordinary maintenance
fence, then let `fork-archive` queued/started/deferred/scheduled registries
drain while the dedicated worker remains online. If the worker is D-state,
keep admission fenced until wepp3 is fenced or the old process is proven dead.
Only after zero in-scope executable jobs remain may operators restore enqueue
selection to `default`, stop the dedicated service, and reopen admission. Prove
no job remains stranded or concurrent across the two queues. Do not flush Redis
DB 9 as a substitute for rollback evidence. This is an operational drill, not
a simulated D-state test.

### Milestone 5: Execute Forest and wepp3 rollout with containment

Forest rollout is two-stage. First deploy/start the new worker service while
the live rq-engine still sends work to `default`; verify the new consumer is
idle and healthy. Inventory all queued/started/deferred/scheduled
`fork_rq`/`archive_rq`/`restore_archive_rq` jobs on `default` and wait for them
to become terminal. Then recreate the rq-engine/UI services with the new route.
Run the two-job serialization, operator visibility, UI, cancellation, and
rollback drills. Record exact commands and output in a rollout artifact.

Repeat the guarded sequence on wepp3 only after Forest acceptance and an
independent security/correctness review. Before startup, verify external Redis
reachability and firewall restriction, required secrets, image provenance,
canonical NFS mounts and permissions, time synchronization, and a tested
out-of-band host fencing path. Verify the worker hostname/container maps to
wepp3, that no unrelated compose service started there, and that wepp1/wepp2
have no registered `fork-archive` consumer. Run one small canary followed by
two-job queued-state evidence if NAS health permits.
Do not create artificial heavy concurrency merely to prove serialization.

Observe for at least 14 days. Record queue depth, worker count/location,
started-job concurrency, ordinary default/batch health, NFS `STAT`/`WCHAN` for
long jobs, and representative `nfsiostat`/benchmark evidence when safe. A
queued job with zero workers, overlapping in-scope started jobs, default-queue
drift, or destructive restore conflict is a release-blocking danger signal.

## Concrete Steps

All commands run from `/home/workdir/wepppy` unless stated otherwise.

Before production edits, record the checkpoint ancestor:

    git rev-parse HEAD
    git log -1 --oneline
    git status --short

Run focused implementation tests during iteration:

    wctl run-pytest tests/microservices/test_rq_engine_fork_archive_routes.py
    wctl run-pytest tests/docker/unit/test_rq_worker_startup_contract.py tests/docker/unit/test_wepppyo3_interchange_startup_contract.py
    PYTHONPATH=/home/workdir/wepppy pytest tools/wctl2/tests/test_rq_info_command.py
    wctl run-pytest tests/rq/test_job_listings.py tests/weppcloud/routes/test_rq_info_details.py
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/test_fork_console_template_contract.py

Render compose contracts without mutating running services:

    docker compose -f docker/docker-compose.dev.yml config --quiet
    docker compose -f docker/docker-compose.prod.yml config --quiet
    docker compose -f docker/docker-compose.prod.yml -f docker/docker-compose.prod.wepp1.yml config --quiet
    docker compose -f docker/docker-compose.dev.hpc.yml config --quiet
    RQ_REDIS_URL=redis://127.0.0.1:6379/9 docker compose -f docker/docker-compose.prod.worker.yml config --quiet
    RQ_REDIS_URL=redis://127.0.0.1:6379/9 docker compose -f docker/docker-compose.prod.wepp3.yml config --quiet

Regenerate and verify RQ dependency documentation after enqueue edits:

    python tools/check_rq_dependency_graph.py --write
    wctl check-rq-graph

Run frontend and broad gates before Forest:

    wctl run-npm lint
    wctl run-npm test
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref <checkpoint-ancestor>
    wctl run-pytest tests --maxfail=1

Validate all changed documentation and spelling before handoff:

    wctl doc-lint --path docs/work-packages/20260803_fork_archive_serial_queue
    wctl doc-lint --path docs/infrastructure/ui-rcds-nfs-vs-dev-nfs.md
    wctl doc-lint --path PROJECT_TRACKER.md
    diff -u docs/work-packages/20260803_fork_archive_serial_queue/package.md <(uk2us docs/work-packages/20260803_fork_archive_serial_queue/package.md)
    git diff --check

Expected focused evidence after implementation includes three graph entries
whose `queue_name` is `fork-archive`, compose services whose command contains
worker count `1` and queue `fork-archive`, and RQ output with exactly one worker
registered for that queue.

## Validation and Acceptance

Automated acceptance requires exact route tests for all three queue origins;
queued cancellation, queued-to-intermediate race, started role-boundary, and
other-origin/Culvert compatibility tests; Docker tests for dev/Forest one-
worker topology, dedicated wepp3 activation, and
wepp1/wepp2 non-consumption;
wctl/listing tests for the new default queue; exact actual-template guidance;
current RQ graph artifacts; full frontend lint/tests; and the repository pytest
gate. Do not replace targeted assertions with broad string-presence checks when
the queue name, count, or service placement can be asserted structurally.

Behavioral acceptance requires a live first job in `started` and second job in
`queued`, followed by second-job dispatch only after the first becomes
terminal. Job origins must be `fork-archive`, and both jobs must identify the
same dedicated worker service. An ordinary default job must not wait behind the
serial queue. A queued restore conflict must fail before file deletion according
to the ratified contract.

User acceptance requires both full-page and embedded console renders to show
the same queue-wait guidance without relying on JavaScript, and job polling must
continue to treat queued as active rather than failed. Fork success must retain
readiness-gated destination navigation. Archive/restore completion must retain
the current list refresh and project link behavior.

Operational acceptance requires normal tools to include the queue by default,
one wepp3 worker and zero wepp1/wepp2 workers for it, a documented D-state triage
path, drain-first deployment, and rollback without DB 9 flushing or stranded
jobs. The security review and independent correctness review must have no
unresolved high or medium finding before wepp3 rollout.

## Idempotence and Recovery

Source/config/test changes are ordinary version-controlled edits and can be
rerun. Compose `config` and test commands are read-only. Disposable acceptance
runs must use unique run IDs and preserve artifacts until their job-tree
evidence is recorded.

Starting the dedicated worker before route cutover is safe because its queue is
initially empty. Recreating rq-engine is the dispatch cutover. If the cutover
fails, fence admission to the three actions and leave the worker service
running so accepted `fork-archive` jobs can finish. Inspect and drain queued,
started, deferred, and scheduled registries before reverting enqueue selection
or removing the service. Never move jobs between queues by editing raw Redis
lists and never flush DB 9 merely to make a rollback appear clean.

If the dedicated worker is in uninterruptible `D` state with an NFS/RPC wait
channel, cancellation or container restart may not release it. Follow the
read-only NAS/NFS triage in
`docs/infrastructure/ui-rcds-nfs-vs-dev-nfs.md`, restore the storage/network
path first, then take the smallest worker recovery action. Do not start a second
worker as an incident shortcut; that can recreate the NAS contention this
package is intended to contain.

## Artifacts and Notes

Keep the accepted contract and reviews under `artifacts/`. Add a Forest rollout
artifact containing compose render hashes, worker registration, legacy default
queue inventory, two-job timestamps/status/origins, cancellation and rollback.
Add a separate wepp3 artifact containing host identity, worker/container
mapping, wepp1/wepp2 non-consumption, proof that no unrelated container started,
Redis/firewall/secrets/image/mount/fencing preflight, NAS health, canary results,
and the observation log.

Do not paste secrets, Redis passwords, full environment dumps, or large worker
logs. Use job IDs, queue names, container IDs, timestamps, bounded process
samples, and redacted status summaries.

## Interfaces and Dependencies

At the end of implementation,
`wepppy.microservices.rq_engine.fork_archive_routes` must expose one internal
constant with value `fork-archive` and construct all three top-level queues from
it. No public response schema changes. `job_routes` and `cancel_job` must expose
the approved origin/state/role cancellation behavior without changing other
queue or Culvert behavior.

Dev and Forest must expose service `rq-worker-fork-archive` with one RQ worker
subscribed only to `fork-archive`. The wepp3-specific compose must expose only
the dedicated production service, using the production image, native
interchange entrypoint, external Redis DB 9 credentials, minimal proven mounts,
and startup readiness contract without unrelated dependencies. Wepp1 and wepp2
compose must not define it.

`DEFAULT_QUEUES` in job listing/summary code and `_RQ_DEFAULT_QUEUES` plus the
registry-repair snippet in wctl must resolve in order to `default`, `batch`,
`fork-archive`. Custom explicit queue query parameters remain supported and are
not filtered to this default set.

The queue change adds no external dependency, secret, port, proxy route,
database migration, project schema, model parameter, or scientific output.

Revision note (2026-08-04, Codex): Created from current source, deployment,
UI, operator, test, and NAS/NFS evidence. Added restore, explicit repurposed-HPC
non-consumption, dedicated wepp3 isolation, wepp1/wepp2 non-consumption,
fork-destination characterization, dispatch-time restore safety, operator
visibility, and drain-first rollback because each is required for a genuinely
single and operable queue.
