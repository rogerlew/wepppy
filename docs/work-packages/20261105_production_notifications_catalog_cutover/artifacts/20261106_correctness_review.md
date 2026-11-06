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
| COR-01 | High | Partial fleet activation/failure | ExecPlan M3 initially specified remote holds and an unspecified admission mechanism. The canonical script resumes its global fence after errors, including partial recreation (`scripts/deploy-production.sh:862`, `:888`, `:932`), and after success (`:1422`). It refuses externally owned suspension (`:694`). A per-host fence cannot establish fleet version isolation. | Before first RQ 2.x writes, stop all old worker pools and old web/API/scheduler producers, retain exact identities, and verify absence. Preserve holds after failed deployment and prohibit old worker restart after 2.x writes. | Resolved: retained eight-container hold receipt precedes activation; old wepp3 pool still held at stage readback |
| COR-02 | Medium | Batch capacity and notification execution | wepp2 container `bf9adc613a7b` had no live worker registrations although Docker reported running. Read-only evidence below confirms retired workers and stalled child processes. Process count is not readiness. | Preserve logs/diagnostics; replace the container during the authorized canonical wepp2 deployment. Require four genuine batch registrations from its new hostname, alongside the six default registrations. Do not fabricate registrations or claim the old pool healthy. | Resolved: canonical recreation and fresh four-batch/six-default registrations verified at 07:01:47 UTC |
| COR-03 | Medium | Scheduled catalog admission | Original `docker/scheduled-tasks.yml:13` passed batch into a reconciler whose shared admission requires default. The prior stub test did not test that boundary. Published candidate now selects default. | Publish the queue correction with actual-YAML, real-admission regression evidence; verify the deployed scheduler emits real default maintenance work and resulting catalog content. | Source/regression/publication resolved; actual scheduled production acceptance pending |
| COR-04 | High | Old-runtime pre-build gate | The initially proposed `get_job_ids(cleanup=False)` repair was incompatible with actual installed RQ 1.16.2: its method accepts only `start`/`end` and unconditionally invokes cleanup. The stub accepted a keyword absent from that runtime. | Use direct non-cleaning Redis cardinality through the registry key, retaining stale entries conservatively. Validate the extracted deployment probe against both actual runtimes and update its regression. | Resolved: raw ZCARD and both-runtime direct execution passed |
| COR-05 | Medium | Fresh catalog pilot/general admission | Two final reservations from the completed October 27 pilot remained in the shared ledger after their RQ hashes expired. `execution_uncertain(..., None)` is always true (`wepppy/rq/_query_catalog_admission.py:49`), so `prepare` denied all new admissions (`:132`); pilot observation also stopped on them. | Perform only the proof-gated two-binding reconciliation below after catalog pause and old-runtime holds. Preserve ledger identity, all pilot records, receipts and historical evidence. | Resolved: exact two-binding removal, preserved metadata/history and live byte hashes verified; catalog remains paused |
| COR-06 | Medium | Source checkout/deployment preparation | wepp1's cached repository-local LFS basic-access setting selected a path that stalled both installed clients; identical cold-cache requests succeeded without that setting. | Remove only the isolated setting and prove ordinary cold-cache filter checkout plus recovered candidate source. | Resolved: exact one-key config diff, repeated cold fetch and normal filter checkout passed; deeper authenticated-request failure mechanism remains unproved |
| COR-07 | Medium | General catalog observation acceptance | Prepared collector could accept an older completed cycle, a preactivation ordinary job or a concurrently admitted maintenance job as evidence of ordinary arrivals; it also omitted observed terminal maintenance failures. Separate reads and old heartbeat timestamps weakened completion/monitoring. | Bind completion to a fresh observed cycle and new started arrival; classify canonical maintenance correctly; retain all-job wait/failure stops; establish a coherent final checkpoint and timestamp heartbeat after sample completion. | Resolved in prepared source: 18 real-Redis local boundary checks pass; live activation/observation evidence remains pending |

These are execution gates, not claims that the feature implementation is
otherwise defective. Missing final migration/browser/model/cycle evidence remains
an acceptance gap even after the plan controls are resolved.

## Minimal transition and recovery controls

Use the existing script and existing containers; no new queue, service, proxy
policy or firewall policy is necessary for RQ version isolation.

1. Complete source publication, migration rehearsal and private image/config
   backups. Keep both new feature schedules disabled. Apply the live additive
   migration only after the old-runtime holds below, before candidate readers.
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
   Apply the guarded live migration now and retain exact count/revision readback;
   if a post-migration assertion fails, inspect committed state before retrying.
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

### Retired-container shutdown assessment

A read-only refresh at 2026-11-06 05:29:01 UTC found the same exact container
`bf9adc613a7bf87ecb607dd6626c0ab9ce80996e4f564b7f2322fb707d7664f4`,
zero registrations and zero started entries on all three queues. Its only live
process tree remained init → supervisor PID 7 → four futex-waiting retired child
processes. Each child had one zombie descendant. The live processes had no open
`/wc1` or `/geodata` descriptors or file mappings. Zombies have exited and do not
constitute running scientific work. These observations must be refreshed at the
actual disposition boundary; they are not standing permission to kill a pool.

Installed RQ 1.16.2 `WorkerPool.request_stop` sets the pool state to STOPPED and
sends SIGINT to its worker children. Its main loop then waits for every child to
exit. A retired child blocked in a native futex may not execute its Python signal
handler, so warm shutdown can remain stuck despite no active job. The exact mutex
cause is still unproved; a 216,000-second wait would not resolve that uncertainty.

The smallest bounded disposition for this already-approved container recreation
is: initiate the normal warm stop asynchronously; observe approximately 30 seconds;
if it has not exited, retain shutdown-request/STOPPED logs and refresh the entire
process tree, worker registrations, started registries and project descriptor/map
checks. Only if the unchanged exact container still contains solely these retired
idle processes and zombies may the operator terminate that exact container with
SIGKILL to finish the stop. An automatic short timeout for arbitrary worker pools
is not this procedure. Any new execution, descendant, registration or project
writer blocks escalation and requires diagnosis. Preserve Redis records, project
files and lock inodes; verify the old container and host PIDs are gone, then leave
it stopped until canonical candidate deployment. No signal was sent by this reviewer.

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
- **Highest supported claim:** wepp1/wepp2 canonical activation, capacity restoration,
  additive migration and scoped notification job/browser evidence are verified.
  The stage review below does not assert completed fleet or feature acceptance.
- **Outstanding:** operator/parent owns remaining fleet activation, real scheduler,
  model/report/archive acceptance, full-root catalog cycle and ordinary-arrival measurements.
  A 48-hour observation cap is not evidence that a full cycle will finish. A pilot
  without ordinary arrivals does not establish ordinary-work delay.

## Review Checks

- [x] Canonical intent, valid states and recovery boundaries named.
- [x] Local/source facts distinguished from live-production acceptance.
- [x] No image-health/job-success substitute for generated artifact readback.
- [x] Partial activation and unsupported reverse compatibility identified.
- [x] Exact plan controls incorporated; retained old-runtime hold evidence reviewed.
- [x] Live additive migration and genuine wepp2 batch restoration verified.
- [ ] Migration and real worker/browser/output checks pass in production.
- [ ] Catalog complete-cycle and ordinary-arrival gates pass.

## Artifact Observability Gate

Canonical inventories are the notification contract's account listing and query
contract's authenticated project refresh records. Private backups and operator
logs supplement those surfaces; they do not replace user-visible project records.
Archive/restore, browser/download and retained failure-artifact evidence must be
linked from final acceptance. No new exception or hidden project record is approved.

## Verdict

- **Gate status:** pass for reviewed design, prerequisite repairs and completed
  wepp1/wepp2 stage. Production feature/fleet acceptance remains pending.
- **Unresolved findings:** High 0; Medium 0; Low 0. COR-01/COR-02/COR-05 live
  closure evidence is recorded below. COR-03 source repair is accepted without
  claiming actual scheduled production acceptance.
- **Release recommendation:** ship-with-conditions. Complete wepp3 registration,
  actual scheduled notification/catalog execution, model/report/archive workflows,
  fresh catalog pilot and full-cycle/ordinary-arrival gates before final acceptance.
  COR-07 source review is closed; populate the observation manifest and meet its
  live launch prerequisites before releasing the owned catalog pause.
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

## Expired completed catalog bindings: bounded reconciliation

Read-only inspection at 2026-11-06 05:41:44 UTC confirmed exactly two reservations
in `query-catalog:batch-admission:v1`, both from `qcat-20261027-shared01`.
The current ledger SHA256 is
`bef8d251c310df87872dcd569dc2784f3cd5d698e6cc334b374442930abd2474`;
`initialized_at` is `1793120006.7626648`, and its TTL is -1. Both job hashes are
absent (TTL -2). Both bindings are claimed with execution-exit timestamps
`1793120185.796539` and `1793120185.9182475`. SHA256 digests of their exact job IDs
are, respectively,
`a8700dfc8f0a6f95ab03d84bae23a518d913023c580193153464f896712311ab` and
`48e58df373448cb5fb2b574afdb95d359785e6969ef6088033fb89054e183216`.
Keep exact IDs, bindings and scope locators in the protected execution snapshot.

Independent evidence establishes completion rather than merely expired status:

- The private original `result.json` on wepp1 has SHA256
  `a940ebc78d12d43970feb3916f80b00c925506a234679c0974b82dcab8bc8710`, matching
  `20261023_query_catalog_async_refresh/artifacts/20261027_shared_pilot/summary.json`.
  It records completed acceptance, zero outstanding/uncertain/failures, and both
  exact jobs finished at 2026-10-27 16:56:25.797801 and 16:56:25.920027 UTC.
- Each complete current ledger binding equals its historical result binding
  after removing only the result's derived `status` field. It also equals the
  corresponding live pilot binding; the immutable manifest still matches.
- The live pilot is paused for `acceptance_readback_complete`, with counters
  16 refresh/one inventory, no failures, completed artifact/receipt phases,
  persistent TTL and no observer lease. Its current raw SHA256 is
  `1c525ccb0670e0ad4370e52cbefdb9dd055b2bb893d52b7b309c5007b9e686c5`.
- Original inventory/receipt readbacks and cleanup files also match the hashes
  committed in that summary. The historical acceptance explicitly records the
  missing original status-byte snapshot; this reconciliation does not recreate it.
- Neither exact ID occurs in default/batch/fork-archive ready lists or their
  started, deferred or scheduled registries. This was a raw read without cleanup.

There is no existing targeted operator release command. `initialize_admission`
preserves an existing ledger; normal admission prunes provably terminal bindings
but intentionally refuses absent job hashes; pilot `drain`/observation does not
reconstruct expired history. Do not weaken `execution_uncertain` globally, restore
fake job hashes/statuses, restart the expired pilot or replace the ledger with a
new initialization. The durable contract allows explicit operator recovery
against retained evidence (query refresh contract, Bounded admission).

The reviewed mutation boundary is one WATCH transaction affecting only this
ledger value:

1. Preserve the full original private result, readbacks and cleanup evidence
   before container replacement. They reside on existing host storage under
   `/geodata/wc1/query-catalog-validation/20261027/shared-pilot-01/` (container
   `/wc1/query-catalog-validation/20261027/shared-pilot-01/`). Verify their committed
   hashes rather than trusting copied filenames.
2. Establish an owned persistent **catalog admission** pause at
   `query-catalog:batch-admission:v1:paused`, preserving any pre-existing pause.
   This is not an external `rq:suspended` key. Retain the pause owner/value.
   Complete all old producer/scheduler/worker holds and verify no execution;
   catalog pause alone does not stop an already-admitted worker.
3. Save private byte-exact before snapshots and TTLs of the ledger, every retained
   pilot key and the relevant queue/registry observations; record their hashes.
   Require the expected ledger/pilot digests, exactly the two approved bindings,
   matching historical bindings, finished results, matching manifest, exit markers,
   completed phases, no failures, and absent job hashes/observer lease. Unexpected
   differences abort for review instead of broadening the target set.
4. WATCH the ledger, catalog pause, old pilot and observer keys, both absent job
   hashes, and all inspected ready/intermediate and nonterminal registry keys.
   Re-read the protected values and all membership/identity conditions after WATCH.
   Require the owned pause and persistent ledger TTL. Check entire relevant
   registry membership without invoking RQ cleanup or deserializing job payloads.
5. Construct a copy of the current ledger and remove only the two exact approved
   job-ID members from its `jobs` mapping. Preserve every other field, especially
   `initialized_at`; assert the semantic diff consists exclusively of those two
   removals. MULTI/SET with TTL preservation/EXEC writes only the ledger. Do not
   delete/reinitialize the key, modify pilot counters, clear failures or receipts,
   change any queue/registry record, or synthesize an RQ terminal status. A WATCH
   conflict aborts; reassess from fresh evidence rather than blindly retrying.
6. Save private after bytes and a diff. Require the same persistent ledger/key
   identity and initialization time, exactly the two removed bindings, unchanged
   pilot bytes/manifest/counters/receipts, absent job hashes and owned pause still
   present. Only then close COR-05. Leave catalog admission paused until the new
   default-worker pilot's normal gates and explicit release.

The historical pilot may now report unknown/outstanding jobs because its RQ
hashes expired. Preserve that truthful retained history; do not force its current
status green. The retained original result proves the old completion. A fresh
pilot uses its own authority and the reconciled global ledger. An extended future
pause past job retention can require similar explicit recovery; this bounded
operation is not a general automatic-expiry repair.

## New-scheduler hold between host deployments

After canonical wepp1 deployment completes, stopping only its newly created
scheduler while wepp2/wepp3 deploy is consistent with the bounded fleet hold.
Keep both feature flags false; restart through the approved scheduler-only
recreation after fleet convergence. This prevents access-log/docs-index admissions
from unnecessarily occupying workers during later deployment gates.

Verify scheduler start time and stop before the earliest enabled task's actual
due time. With the reviewed YAML, those tasks start after 900 seconds plus
nonnegative jitter (`wepppy/tools/scheduler.py:193`); disabled zero-delay catalog
tasks must actually be disabled. Canonical health checks expect scheduler running,
so stop after those checks rather than making them fail deliberately. If the
script itself takes beyond the earliest due time, inspect and drain any admitted
work; a later stop does not retract queued jobs. No deletion or cancellation of
accepted tasks is justified. Record the hold/recreation and actual first feature
schedule time rather than promising a fixed wall-clock execution.

## Source preparation: stalled Git LFS filter

Read-only checks at 2026-11-06 06:01:52–06:02:24 UTC found wepp1 HEAD and
ORIG_HEAD still at `0da9c9071069c37fdcf3df5a74b28d161b1af458`, with fetched
origin/master at `8d079b41db466fda5235a599c151324190393e9d`. Merge PID 2479310
waited in `pipe_read` while its `/usr/local/bin/git-lfs` child PID 2479332 remained
alive. The merge owned the zero-byte `.git/index.lock`; there was no MERGE_HEAD
or MERGE_MSG. LFS temporary object storage was empty, the cache contained 647
objects, and the filter's cumulative disk-write bytes remained zero. A later
check still showed both processes after 12 minutes. This confirms a stalled
checkout/filter boundary, not an application runtime deployment. The exact
network cause is not established by these observations.

The operator's candidate-manifest comparison identifies 11 missing objects,
2,930,288 bytes, among 653 unique published candidate objects. wepp2 completed
the same fast-forward successfully. Those inventory/completion results are
attributed to the operator; this reviewer did not repeat their entire hash audit.

The existing recovery precedent is
`docs/infrastructure/wepp1-deployment-20261012.md`, Progress and discoveries:
stop only the owned stuck filter, preserve partial-checkout evidence, and seed
committed-content-addressed objects from the verified local cache. The canonical
`safe_git_fast_forward_pull` already restores its original tracked checkout when
its merge fails (`scripts/deploy-production.sh:243`); a manually launched merge
does not inherit that recovery wrapper.

The bounded recovery is to copy only the manifest's missing objects over the
existing SSH path, with temporary-file/rename transfer semantics and SHA256/size
verification before and after transfer. Do not use in-place writes or overwrite
an unexpected different object. Allow a brief observation for the current merge
to finish; if it succeeds at the authorized candidate, no reset is needed.

If still stalled, recheck the filter PID/start identity, terminate only that
owned filter gracefully, and wait for both filter and merge to exit. Never remove
an index lock owned by a live process. Retain the partial-checkout inventory and
confirm the previously clean source has no unrelated new edits. Only under that
documented condition may the operator recover this deployment's partial checkout
directly to the exact already-published candidate:

```bash
GIT_LFS_SKIP_SMUDGE=1 git -C /workdir/wepppy reset --hard 8d079b41db466fda5235a599c151324190393e9d
git -C /workdir/wepppy lfs checkout
```

This uses the same branch and authorized target; it is not permission to reset
unrelated user changes. No stash, broad `git clean`, new protocol or registry is
needed. Installed `git lfs checkout` documentation confirms it materializes
available local objects without downloading and does not overwrite modified
files. Verify final HEAD, clean tracked/untracked state, every candidate LFS
path's actual bytes/hash/size and native vendored artifacts before the canonical
build. An unresolved pointer or unexpected local edit blocks activation.
This reviewer sent no signals and changed no production files.

### Permanent Git LFS repair: configuration discrimination

The operator subsequently requested a permanent wepp1 repair. Independent
read-only comparison confirms all three hosts select `/usr/local/bin/git-lfs`
2.3.4 (Go 1.9.1), while wepp1 also has packaged `/usr/bin/git-lfs` 3.4.1
(Go 1.22.2). The October 12 record explicitly says both client versions stalled
before cache seeding, so that precedent does not prove a client-selection fix.

wepp1's two global credential-helper entries are an empty reset followed by Git
Credential Manager with gpg storage. wepp2's global helper is credential store.
However, both hosts have identical github.com-scoped empty-reset followed by the
GitHub CLI auth helper. Git documents the empty entry as clearing inherited
helpers; their raw global helper counts are therefore not evidence of different
effective GitHub authentication. No credential values were printed or changed.
[Git credential configuration](https://git-scm.com/docs/gitcredentials).

The wepp1-only URL-scoped LFS `access=basic` entry is not inherently invalid:
LFS normally records it after an authentication challenge and obtains credentials
before the batch request. Removing it changes the initial authentication path;
it does not prove the prior path was the stall's cause.
[Git LFS configuration](https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-config.adoc),
[version 2.3.4 authentication code](https://raw.githubusercontent.com/git-lfs/git-lfs/v2.3.4/lfsapi/auth.go).

The accepted diagnostic design uses the same exact published object set with a
separate empty object store per bounded probe: current client/current config,
packaged client/same config, then the exact access-key override only if needed.
Retain sanitized duration, success/failure stage, object hashes and client identity.
A permanent fix must additionally pass a real uncached filter checkout and repeated
download without seeded objects. Preserve the successful credential topology;
do not rewrite global helpers or reorder all executables on PATH based on counts.
If client selection is proved causal, select the packaged binary consistently for
both ordinary `git lfs` and Git's filters. If the cached access setting is proved
causal, change only that repository/URL setting and verify normal challenge
negotiation does not immediately recreate the same failure. TLS verification and
credentials must remain intact. The permanent fix is unproved until those actual
boundaries pass; the earlier cache recovery only restored deployment source.

The subsequent controlled probes isolate the cached preauthentication setting:

| Probe | Client | Access setting | Result |
| --- | --- | --- | --- |
| old-configured-01 | 2.3.4 | Original basic | Timeout after 45.005 seconds; 0/11 objects |
| system-configured-01 | 3.4.1 | Original basic | Timeout after 45.009 seconds; 0/11 objects |
| old-public-first-01 | 2.3.4 | Per-command empty override | 1.582 seconds; 11/11 hashes/sizes valid |
| permanent-normal-01 | 2.3.4 | Persistently removed key; no access override | 1.632 seconds; 11/11 hashes/sizes valid |

This reviewer read the retained private receipts and probe implementation. Every
label creates a new exclusive mode-0700 directory with its own initially empty
`lfs.storage`; all probes use the same candidate and 11 object IDs. The bounded
timeouts and other probe settings are constant. No seeded cache supplies these
results. The operator then removed only repository-local
`lfs.https://github.com/rogerlew/wepppy.git/info/lfs.access` after backing up
`.git/config`, leaving client selection and global credential helpers unchanged.

Independent comparison of the parsed backup and live configuration confirms
exactly that one setting removed and zero additions. Backup SHA256 is
`13903f6324dfbfec9d1eecd5156bc8779c6b93e8fa139b0a68d7ccd2750556e9`;
current SHA256 is
`6fa0d6ad1c5f81db73420828f1decf194e6c820cd6a66dbb8412dd58a4654fa0`.
The key is absent and there is no repository `.lfsconfig` fallback. This supports
the smallest persistent repair: restore normal initial public/challenge-based
negotiation for this repository. It does not establish why authenticated requests
stalled internally, invalidate the credential helpers, or justify changing TLS,
global authentication, or installed client versions.

Remaining acceptance is a real off-tree `checkout-index` from the candidate's LFS
pointer index with a separate empty object store, ordinary PATH/filter settings,
and no skip-smudge or access override. Require all 11 output hashes/sizes, the
access key still absent afterward, and then full source-recovery LFS/clean-tree
validation. These pending gates prevent treating a fetch-only success as complete
checkout/deployment recovery.

### Permanent repair closure

COR-06 is resolved. The retained normal-filter receipt records exit 0, no timeout,
11/11 output files, 4.631 seconds, absent access key, clean worktree and an empty
initial cache. This reviewer inspected the executed probe code; its SHA256 on
wepp1 matches the reviewed local copy:
`21d090a358eebff9965cb79c75e27ab05c53be96d3a46245f3cab262c575e27e`.
It refuses skip-smudge, requires candidate HEAD, exclusively creates a new output
directory, requires the cache not to exist, and invokes `git checkout-index` with
only isolated `lfs.storage`; it does not change PATH, filters or access settings.

Independent readback parsed each selected path's LFS pointer directly from
candidate `8d079b41db466fda5235a599c151324190393e9d` and verified all 11 off-tree
outputs plus their 11 isolated-cache objects against committed SHA256 and size.
The main index matches the candidate, HEAD is that revision, and the access key
remains absent. The source-recovery log records successful materialization of all
661 LFS paths; the operator additionally reports full hash/size validation and
clean matching source on wepp1/wepp2/wepp3. This review did not repeat the entire
1.265-GB fleet hash audit.

The fix is a persistent repository-local configuration correction, not a cache
seed, binary replacement, credential rewrite or TLS change. The evidence isolates
the problematic preauthentication path; it does not establish the deeper reason
authenticated requests stalled or certify unrelated private repositories.
The parent reports the completed broad suite: 13,361 passed, 281 skipped,
3,579.24 seconds. Runtime deployment and its live acceptance gates are still
pending; source/test readiness is not production activation.

## Live stage review: 2026-11-06 07:01–07:03 UTC

The retained all-old-runtime receipt contains the exact eight expected unique
host/service identities, each exited with PID zero before the live migration and
candidate startup. The reviewed helper completed its quiescent started-registry
checks without deleting RQ records. Canonical wepp1 and wepp2 logs end with
`Deployment complete!` and resumed dequeue; the operator reports exit 0 for both.
Independent Docker readback confirms their recreated worker containers running
with zero restarts. COR-01's transition control is satisfied for this stage;
restarting any old pool after 2.x writes remains prohibited.

Fresh raw Redis reads at 07:01:47 UTC, without registry cleanup, confirm:

| Host/container hostname | Queue | Genuine workers | Minimum remaining hash TTL |
| --- | --- | --- | --- |
| wepp1 / `aea1ed905302` | default | 6 | 242 seconds |
| wepp1 / `d03741087af4` | batch | 4 | 80 seconds |
| wepp2 / `3dad921db2dd` | default | 6 | 406 seconds |
| wepp2 / `173c9c65029c` | batch | 4 | 406 seconds |

All 20 hashes are idle with no current job or death marker; default, batch and
fork/archive ready/started counts are zero. Global suspension and deploy fence
are absent. wepp2 heartbeats are at most 72.5 seconds old. Its two containers
started at 06:53:23 UTC and use image
`sha256:99386c60de96ebbebaae2eda0871293c18513cec2631ae68bbab4af6e9c2ce59`.
This closes COR-02 through actual restored capacity. It does not establish a
software fix for the old retirement/futex mechanism or guarantee future capacity.

The retained wepp1/wepp2 runtime receipts match in versions, identity
UID 1002/GID 130, source-file hashes, vendor inventories, Rosetta assets and
installed interchange bytes. Both report RQ 2.12.0 and the expected WEPP 261029
watershed/hill hashes. Both new feature flags remain false; run-catalog read/write
modes remain `legacy`/`timestamp_only` with its sweep false. The two host images
need not have identical IDs because canonical builds occur separately; the
retained content manifests establish the inspected equivalence.

Scheduler `cf0c195e5645` started at 06:42:31 UTC and exited normally at 06:45:01,
about 151 seconds later, before its earliest 900-second initial task delay.
The exact old wepp3 fork/archive container `10ecab255dae` remains exited at this
readback; its candidate build and eventual genuine registration are still gates.
Twenty current workers therefore prove restored main-host capacity, not completed
21-worker fleet acceptance.

COR-05 is also closed from independent retained-byte comparison and live Redis
readback at 07:02:37 UTC. The before snapshot has exactly two bindings; after and
intended-after bytes match with zero bindings. All other ledger fields, including
`initialized_at=1793120006.7626648`, are identical. Live ledger SHA256 is
`ebcf3f410d36ee26bf1623ccbabc9eef4ed3d09160675e99f0924f30a5f41608`;
the historical pilot retains SHA256
`1c525ccb0670e0ad4370e52cbefdb9dd055b2bb893d52b7b309c5007b9e686c5`.
Both keys and the exact owned catalog pause retain persistent TTL; the old pilot
observer is absent. No ledger reset, reconstructed job status or historical pilot
rewrite occurred. This permits the next gated pilot preparation; it does not
unpause general admission or establish a completed fresh pilot.

The guarded live migration receipt reports revision `f6b8d27a901c` on the intended
production database/server with the four existing table counts unchanged. Private
acceptance receipts show a real batch notification job creating one warning and
a repeat updating that warning without duplication. The isolated browser receipt
passes read/unread persistence, logout/login persistence, 100+1 pagination,
selection handling, failure handling, account isolation and mobile overflow checks.
These are scoped production evidence, not proof of the nightly schedule or every
user's population. Credentials and account locators remain private. Real scheduler
execution, model outputs/reports, archive/restore, fresh catalog pilot and full-root
cycle/ordinary-arrival observation remain unaccepted at this checkpoint.

## Prepared general-observation collector review

Scope: `artifacts/observe_general_catalog.py` and
`artifacts/general_observation_manifest.json`, before activation. The manifest
remains `prepared_not_activated` with configuration/image placeholders. This
review authorizes no live pause release and claims no full-root acceptance.

The initial sample function could write `completed.json` during its paused
preflight when supplied a retained completed cycle/proof and an older running
ordinary job. A local execution of that exact extracted function reproduced
success with zero new arrivals. The revised collector disables preflight
completion, records activation/baseline cycle, pins a different cycle whose start
is after activation, and requires a postactivation ordinary arrival with an
actual start timestamp. Stop-delay checks cover every observed ordinary job,
including old backlog and missing timestamps; only acceptance uses the narrower
arrival set. Direct discovery errors and observed failed/stopped/canceled
maintenance now stop observation.

The completion path now watches ledger, cursor, discovery, pause and referenced
job hashes, compares them with the sampled state and commits a read transaction.
Changed state or WatchError defers completion to a later sample. Heartbeat time
now records sample completion, retaining start separately. Previously two healthy
44-second samples plus the 10-second sleep could leave the start-based heartbeat
98 seconds old, falsely triggering the parent's 60-second stale rule.

A further real negative test exposed canonical description drift: actual refresh
and inventory jobs use `Query catalog maintenance`, not a function description
(`wepppy/rq/query_catalog_rq.py:34`, `:203`, `:333`). A concurrent admission could
therefore be retained as an ordinary arrival. Revised classification checks the
canonical prefix/description, rereads ledger ownership and retains maintenance IDs
to remove earlier ordinary candidates. Unknown maintenance-looking work stops
observation. Reconciler ticks contribute to wait-health checks but cannot satisfy
ordinary-arrival acceptance. An exclusive start marker prevents reuse of the
observation directory; a fixed manifest deadline prevents restart-based extension.
Any newly appearing admission pause interrupts the run without clearing its owner.

Eighteen current-source checks passed using a disposable Unix-socket Redis and
the production-pinned redis-py 6.2.0. They cover valid fresh-cycle/new-started-arrival
success; paused preflight, old cycle/arrival and scheduler-tick exclusion; explicit
stops for 300-second backlog, missing timestamps, failed maintenance, discovery
errors, wrong-cycle proof, new pause and unaccounted maintenance; and deferral for
changed state and an actual Redis WatchError. The canonical-description case
failed before its repair and passed afterward. Concurrently admitted maintenance
and previously misclassified ordinary entries are excluded. These tests execute
the extracted current sample/save and durable admission/wait functions. They do
not execute production mutations, the complete observer process, signal/deadline
handling or general refresh. Source review covers those outer controls; actual
production observation remains required.

Reviewed collector SHA256:
`e3f295df4ff83351731837d5195747ab7c033eb481f3bacbb467513aa600a4be`.
Local harness `/tmp/review-general-catalog-collector.py` SHA256:
`5a271ff19a85f2abdb5271c7155cabc087b93e21bbe2bf71a169a1670de0f41b`.
The prepared manifest must receive concrete configuration, image and absolute
deadline values only after actual fleet convergence. COR-07 is resolved in source;
no live general-admission release is implied by this review.

Observation remains sampled. Jobs that enter and leave between samples may be
unseen; no claim of exhaustive ordinary-arrival or transient-failure coverage is
supported. Pending/admitted scope ages do not establish the global oldest receipt
or oldest undiscovered scope. Same-cycle independent artifact and age-coverage
evidence is still mandatory. Parent monitoring must remain active through the
bounded window: SIGKILL, host loss and blocked external I/O cannot be made safe by
Python signal handling alone. Preserve any observation gap as incomplete evidence.
