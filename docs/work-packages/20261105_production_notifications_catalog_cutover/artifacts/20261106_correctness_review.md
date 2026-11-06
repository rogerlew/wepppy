# Correctness and User-Experience Review — Production notifications/catalog cutover

## Metadata

- **Package:** `docs/work-packages/20261105_production_notifications_catalog_cutover/`.
- **Reviewer:** independent `production_cutover_correctness` agent.
- **Date:** 2026-11-06 UTC; initial pre-activation review.
- **Scope reviewed:** package/ExecPlan, canonical deployment fence and recovery,
  actual wepp2 batch readiness, notification migration/activation, catalog routing
  and acceptance. This is not a fresh line-by-line review of every feature.
- **Commit context:** candidate base `2111d0eb2`; local scheduler repair and package
  edits were in progress. Production inspected read-only; no mutations performed.
- **Contracts:** `docs/dev-notes/rq-2-12-migration.md`, sections Historical jobs,
  Recovery and Production planning; `docs/schemas/user-notifications-contract.md`,
  Persistence/Nightly producer/Bell and listing; `docs/schemas/query-engine-catalog-refresh-contract.md`,
  Lifecycle, reconciliation, bounded admission and acceptance;
  `docs/dev-notes/query-catalog-refresh-operations.md`.
- **Related review:** independent security artifact is owned by another reviewer.

## User Outcome

Users retain existing projects, accepted jobs and reports while receiving a
private, persistent inbox and asynchronous catalog updates. Read notifications
remain read across repeated sweeps. Deployment is not accepted from container
health alone: actual submissions, native outputs, reports, inbox interactions and
catalog/query artifacts must pass.

The proposed minimal transition briefly makes web/API submissions unavailable.
Once new web/API services start, traffic can resume using only RQ 2.x consumers;
remaining remote pools stay stopped until upgraded. Normal work may wait for
reduced capacity, especially fork/archive until wepp3 returns. A strict traffic
hold until all acceptance is complete is a different requirement and is not
implemented by the present canonical script.

## Findings

| ID | Severity | User/state surface | Description and evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| COR-01 | High | Partial fleet activation/failure | ExecPlan M3 initially specified remote holds and an unspecified admission mechanism. The canonical script resumes its global fence after errors, including partial recreation (`scripts/deploy-production.sh:862`, `:888`, `:932`), and after success (`:1422`). It refuses externally owned suspension (`:694`). A per-host fence cannot establish fleet version isolation. | Before first RQ 2.x writes, stop all old worker pools and old web/API/scheduler producers, retain exact identities, and verify absence. Preserve holds after failed deployment and prohibit old worker restart after 2.x writes. | Design resolved in revised M3; live stopped-process/drain evidence remains an execution prerequisite |
| COR-02 | Medium | Batch capacity and notification execution | wepp2 container `bf9adc613a7b` has no live worker registrations although Docker reports running. Read-only evidence below confirms retired workers and stalled child processes. Process count is not readiness. | Preserve logs/diagnostics; replace the container during the authorized canonical wepp2 deployment. Require four genuine batch registrations from its new hostname, alongside the six default registrations. Do not fabricate registrations or claim the old pool healthy. | Open: production recovery/verification pending |
| COR-03 | Medium | Scheduled catalog admission | Original `docker/scheduled-tasks.yml:13` passed batch into a reconciler whose shared admission requires default. The prior stub test did not test that boundary. Parent's working tree now selects default. | Publish the queue correction with actual-YAML, real-admission regression evidence; verify the deployed scheduler emits real default maintenance work and resulting catalog content. | Source/regression resolved; publication and production acceptance pending |
| COR-04 | High | Old-runtime pre-build gate | The initially proposed `get_job_ids(cleanup=False)` repair was incompatible with actual installed RQ 1.16.2: its method accepts only `start`/`end` and unconditionally invokes cleanup. The stub accepted a keyword absent from that runtime. | Use direct non-cleaning Redis cardinality through the registry key, retaining stale entries conservatively. Validate the extracted deployment probe against both actual runtimes and update its regression. | Resolved: raw ZCARD and both-runtime direct execution passed |

These are execution gates, not claims that the feature implementation is
otherwise defective. Missing final migration/browser/model/cycle evidence remains
an acceptance gap even after the plan controls are resolved.

## Minimal transition and recovery controls

Use the existing script and existing containers; no new queue, service, proxy
policy or firewall policy is necessary for RQ version isolation.

1. Complete source publication, migration rehearsal, additive migration and
   private image/config backups. Keep both new feature schedules disabled.
2. Verify host identity and current process/container IDs. Gracefully stop old
   wepp1 `weppcloud`, `rq-engine`, and `scheduler`, allowing accepted requests to
   finish. Stop all old default/batch pools on wepp1 and wepp2 and fork/archive on
   wepp3 with the existing warm-stop semantics. Never force-kill active jobs.
   The script's existing worker timeout is 216,000 seconds; an unresponsive pool
   requires an explicit observed disposition, not silently reducing that timeout.
3. Verify all five old worker containers are stopped, old producers are absent,
   and default/batch/fork-archive have no started executions. Retain queue,
   dependency, scheduler and historical records. Take the quiescent recovery
   snapshot after these checks; an earlier live backup alone is not that point.
4. Run the reviewed canonical full deployment on wepp1, then worker deployment on
   wepp2 and fork/archive deployment on wepp3. Keep remote old containers stopped
   throughout. Do not set an external `rq:suspended` value or interfere with the
   script's owner/heartbeat/resume keys. Manually stopped inspected containers use
   `unless-stopped`; verify this again for the exact stopped IDs.
5. New wepp1 services may accept ordinary traffic and process supported preserved
   1.x queued records. This is forward migration with exclusively 2.x consumers,
   not mixed-version execution. Full acceptance still requires production
   workflow checks. Gate each subsequent deployment on current active jobs; do
   not terminate new work to obtain an empty registry.
6. Require six default and four batch consumers on each main host and one
   fork/archive consumer on wepp3, with intended images and actual imports.
   The canonical main-host check only requires counts greater than zero
   (`scripts/deploy-production.sh:1413`); it does not prove full configured
   capacity. The dedicated wepp3 path also needs explicit registration evidence.
7. On failure before any 2.x state writes, original-runtime restart requires
   verified original state/source/images. After any 2.x writes, retain remote
   old holds, stop package-owned admissions and use a bounded forward repair.
   Do not attach a 1.x pool to live state or restore an old Redis dump over it.
   The script's CAP recovery does not constitute whole-application rollback.

This sequence has a longer web/API interruption if services are stopped before
the canonical no-cache build. There is no reviewed build-only phase in the
present entry point. Do not claim a short cutover outage without measured evidence
or a separately reviewed canonical phase boundary.

An alternative Caddy-only maintenance response would not establish admission
isolation: wepp1 publishes Flask on `0.0.0.0:8000` and IPv6, and direct local
`http://127.0.0.1:8000/health` returns 200. External reachability was not tested.
Stopping the old Flask/API processes covers their direct and proxied paths.
Public `/weppcloud/health` is an unconditional Caddy response
(`docker/caddy/Caddyfile.wepp1:14`); independently inspect real application health
and functional routes even when that endpoint passes.

## Read-only production evidence: wepp2 batch

At 2026-11-06 05:11:45 UTC, raw Redis inspection through the running batch
container found 17 live worker hashes: six default workers on each main host,
four batch workers on wepp1, one fork/archive worker on wepp3, and none from
wepp2 batch hostname `bf9adc613a7b`. Batch ready and started counts were zero;
global suspension was absent. Reads used hash/list/zset operations without
registry cleanup. These are observation-time facts, not a later drain gate.

Filtered Docker logs show worker retirement for uncertain/residual writers at
2026-10-29 06:11:05 UTC, 06:13:15 UTC, and 2026-10-30 04:38:08 UTC, followed by
stop/unsubscribe messages. The last log entry is the October 30 unsubscribe.
`wepppy/rq/rq_worker.py:509` requests retirement when residual writer containment
cannot be proved; this is intentional exclusion, not permission to clear locks.

Container PID 7 remains a supervisor. Child PIDs 258–261 each have one thread
waiting in `futex_wait_queue`, each has one zombie child, and none has an open
`/wc1` file at inspection. No running scientific descendant was observed. RQ
1.16.2 pool code replaces exited processes; these processes have not exited.
This supports a stranded-pool diagnosis, but does not identify the exact mutex
or prove why each child became stuck. No debugger/signal/process mutation was
used. Three corresponding historical job hashes have expired naturally, so their
full metadata cannot be recovered from current Redis. Do not claim a complete
historical root cause or scientific-output validation from these observations.

## Failure-Class Coverage

The scheduler defect is the shared assumption that omitted/default queue routing
overrides an explicitly supplied YAML queue. Review covers its actual YAML,
scheduler handoff, admission queue validation and consumer/output path. Notification
population remains batch; unrelated scheduler tasks and paused GC remain unchanged.
The fleet risk separately spans both main-host worker pools, fork/archive,
web/API producers and scheduler. Retiring batch workers are a confirmed existing
capacity issue; a global pool-retirement repair is not claimed by this deployment.

## Valid-State Matrix

| State | Valid? | Required behavior | Evidence/status |
| --- | --- | --- | --- |
| Notifications never enabled; schema absent | yes, before activation | Add schema before candidate web readers; leave sweep disabled | Migration is additive; live rehearsal pending |
| Migrated empty inbox | yes | Empty listing and no numeric badge; reads do not enqueue population | Contract; production browser pending |
| Populated inbox with read/unread items | yes | User-scoped content; pagination/bulk limit 100; retry preserves read state | Contract; production fixture/readback pending |
| Preserved queued/deferred/scheduled RQ 1.x work | yes | Preserve IDs/dependencies; run with exclusively new workers | Durable synthetic replay evidence; live inventory/acceptance pending |
| Running 1.x work | yes, before transition | Drain under old runtime; no running handover | All-pool process/registry gate required |
| Mixed old/new worker execution | unsupported | Prevent it through stopped old containers | COR-01 |
| Missing/corrupt TTL or catalog source | exceptional or unknown | Explicit unavailable/failed state; no false protection/currentness | Contracts; production failure cases pending |
| Catalog absent/empty/legacy/populated/readonly | yes | Correct initialization or noninterference; retain source/guards | Fresh pilot and full-root observation pending |

## User-Reachable Error Policy

| Condition | Classification | Required visible result |
| --- | --- | --- |
| Transitional web/API shutdown | expected deployment interruption | Unavailable response; never claim submission acceptance |
| Inbox database unavailable | exceptional | Explicit unavailable state/503, not empty inbox or zero badge |
| Catalog maintenance failure | exceptional | Preserve last-good/pending evidence; sanitized public job failure |
| Maintenance capacity exhausted or ordinary work waiting | expected | Durable pending work and bounded deferral, not inline scan |
| Old/missing notification membership | expected authorization state | Hide content and exclude it from unread count |

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| User intent | Authorized release plus five new-project defaults | User commit `2111d0eb2`, ADR-0138 | Reviewed |
| Reloaded persisted state | Existing selections retained; fixture read state/TTL unchanged | Production fixture/state/hash evidence | Pending |
| Intermediate | Receipt/inventory/source identity and fresh model inputs agree | Real worker/pilot and model artifact parse | Pending |
| Executable input | Intended vendored native binaries and valid prepared files | Installed hashes and exact consumed files | Pending |
| Execution output | Fresh matched model output; catalog/schema acknowledge intended source | Native/output/query readback | Pending |
| User-facing result | Report/download/inbox match authorized fresh state | Authenticated production browser and downloads | Pending |

- **Direct unmocked boundary:** scheduler actual-YAML regression being added;
  production first scheduled executions still required.
- **Actual environment:** read-only wepp1/wepp2 checks above. Forest evidence is
  precedent, not production acceptance.
- **Highest supported claim:** deployment planning reviewed with concrete open
  prerequisites; no production deployment or feature acceptance asserted.
- **Outstanding:** operator/parent owns migration, fleet activation, real job and
  browser acceptance, full-root catalog cycle and ordinary-arrival measurements.
  A 48-hour observation cap is not evidence that a full cycle will finish. A pilot
  without ordinary arrivals does not establish ordinary-work delay.

## Review Checks

- [x] Canonical intent, valid states and recovery boundaries named.
- [x] Local/source facts distinguished from live-production acceptance.
- [x] No image-health/job-success substitute for generated artifact readback.
- [x] Partial activation and unsupported reverse compatibility identified.
- [x] Exact plan controls incorporated; live stopped-process/drain evidence pending.
- [ ] Migration and real worker/browser/output checks pass in production.
- [ ] Catalog complete-cycle and ordinary-arrival gates pass.

## Artifact Observability Gate

Canonical inventories are the notification contract's account listing and query
contract's authenticated project refresh records. Private backups and operator
logs supplement those surfaces; they do not replace user-visible project records.
Archive/restore, browser/download and retained failure-artifact evidence must be
linked from final acceptance. No new exception or hidden project record is approved.

## Verdict

- **Gate status:** pass for revised design and prerequisite patches, conditional
  on live stopped-process/drain evidence and the other stage prerequisites before
  activation. Production feature/fleet acceptance remains pending.
- **Unresolved findings:** High 0; Medium 1; Low 0. COR-01 is resolved as a design
  finding but its live evidence is mandatory before transition; COR-03 source
  repair is accepted without claiming deployment acceptance.
- **Release recommendation:** ship-with-conditions. COR-02 requires genuine wepp2
  capacity after its canonical recreation; it does not prohibit the preceding
  wepp1 transition while every old wepp2 worker is verifiably held stopped.
- **Reviewer sign-off:** `production_cutover_correctness`, 2026-11-06 UTC.
  Re-review after concrete controls and actual deployment evidence are available.

## Follow-up: plan and prerequisite patch review

Revised ExecPlan M3 names all old web/API/scheduler processes and five worker
containers, explicitly includes direct port 8000, preserves stopped old services
on failure and accepts normal 2.x traffic plus the build-length outage. This
resolves COR-01's design ambiguity. Traffic can actually return as newly started
services become reachable, before the script finishes its post-start health
checks; wording must not imply an unimplemented admission barrier at health pass.

The scheduler regression reads shipped YAML, invokes actual reconciliation and
admission against disposable Redis, runs real SimpleWorker tasks and parses
catalog content/receipts. Eleven companion registrations are test fixtures; this
does not prove production pool capacity. The parent reports its old-YAML failure,
corrected-YAML pass, 186 focused tests, 72 deployment tests and current RQ graph.
The broad suite remains running. These are attributed test results; this reviewer
inspected the implementation and tests rather than rerunning the same suites.

The new deployment probe test executes extracted script code, which is a useful
boundary, but its fake `get_job_ids(*, cleanup=True)` does not match RQ 1.16.2.
Independent read-only inspection inside wepp2's running old container returned
`(self, start: int = 0, end: int = -1)` and source calling `self.cleanup()` without
an opt-out. This is direct runtime evidence for COR-04. Prefer raw Redis `zcard`
using `StartedJobRegistry(...).key`; it needs no destructive cleanup or
version-specific keyword. A stale registry entry should block for diagnosis,
not authorize automatic cleanup during a migration gate.

The parent replaced the incompatible keyword with direct `connection.zcard` and
changed the regression to reject any `get_job_ids` call. At approximately
2026-11-06 05:19 UTC this reviewer extracted the exact embedded program from the
updated deployment script and executed it read-only in both actual runtimes:
wepp2 container `bf9adc613a7b` reported RQ 1.16.2 and count 0; forest weppcloud
reported RQ 2.12.0 and count 0. Both exited successfully. This closes COR-04's
runtime compatibility/read-only concern; it is not a later production drain
certificate. No production queue records were created, cleaned or changed.
