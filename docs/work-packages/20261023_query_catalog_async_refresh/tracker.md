# Query catalog refresh tracker

## November 22 Rocket refresh phases and completion hints

Two matched NFS fixtures reproduced the asset mix of a climate-heavy run. The replay used the earlier eight production ticks and verified all eleven eligible publications on wepp2. At the same 200-visit budget, two completion hints per tick yielded 23 modeled cursor exits versus 14 observed FIFO exits. Two otherwise observed clearances slipped past the replay window. Production worker and scheduler configuration stayed in place. Fleet-capacity acceptance remains open. [Phase timings, peer validation and replay results](artifacts/rocket_refresh_phases_and_completion_replay.md)

## November 22 reconciliation visit experiment

From 16:41:03 to 16:45:03 UTC on Rocket, eight consecutive production scheduler ticks made 200 visits. **186 visits (93%) sent the locator to the back of the list.** The pending count fell from 4,878 to 4,864. Worker records independently showed 11 successful refresh jobs during those four minutes. This was the reconciliation tail of the November 21 cycle.

| Measurement | Observed result |
| --- | --- |
| First visits and confirmations | All 200 visited cycle entries had already passed their initial reconciliation step. Fourteen left the cursor. Immediate follow-up reads covered seven of those exits. All seven scopes existed, were managed and writable, and had no pending receipt. The other seven exits were visible only in the cursor. |
| Admission | The scheduler reported 11 visits returning a job ID, zero owner-cap deferrals and zero errors. Among 186 retained visits, 175 returned no job ID. The release lacks per-visit reason codes in its checkpoint, so the split among global capacity, contention, backoff and other outcomes is unknown. |
| Actual worker throughput | Across the two default-worker hosts, log identities and retained RQ timestamps showed 10 refresh enqueues and 11 successful finishes inside the wall-clock window. A tick can return an existing job ID and can enqueue after its recorded start time. Cursor exits, enqueue timestamps and job finishes each measure different events. |
| Permit occupancy | In the overlapping 43 four-second samples, six jobs stayed started throughout. The seventh permit was occupied in 15 samples and available in 28. Each sampled default queue was empty and each reservation had a known execution state. |
| Slow workers | Three persistent jobs belonged to `wc1:runs`. At 16:43 UTC two had been running for about 45 minutes and one for 21 minutes. Their worker child processes were in `rpc_wait_bit_killable` on all 15 observations across wepp1 and wepp2. Each used 0.68–0.78 CPU seconds over 12 seconds. A separate 80-success sample from roughly the preceding half hour had median runtime 8.3 s and maximum 1,314 s. Ongoing jobs are excluded from that duration sample. |

**What the measurements explain.** The scheduler maintained its 30 s cadence. After a visit at this queue depth, about 4,850 older entries still stand ahead of a requeued locator. At 25 visits per tick, another turn takes roughly 97 minutes under the observed FIFO ordering. A worker can publish promptly and its cursor entry can still wait that long for confirmation. Independently, three long-lived run jobs occupied permits while repeatedly waiting on RPC. The per-client `/wc1` mount counters also advanced during this window, but those counters include ordinary workloads and cannot attribute a specific operation or server bottleneck to a catalog job.

**Next discriminating test.** On a production NFS test project representative of the slow run scopes, time directory enumeration, metadata/schema reads and publication separately while recording the same worker CPU and RPC evidence. Match the input and cache conditions and verify the catalog digest, schema and query on the peer. For scheduler changes, use a read-only replay of worker-finish hints against FIFO at the same visit and permit budgets and measure finish-to-confirmation delay separately from receipt-to-publication delay. This window supports testing those mechanisms. Fleet-wide capacity and the effect of raising concurrency remain open.

**Reproduction and evidence.** In the wepp1 worker, sample the small health key every two seconds. On each tick change, read the ordered cursor, health and stream length in one Redis transaction. Hash the lexical paths. For adjacent cursors verify identical cycle and stream acknowledgment, an empty stream, exactly the expected unvisited suffix at the front, and the surviving visited head in order at the tail. Join bounded `docker logs --timestamps` from both default-worker hosts to RQ job function and timestamps. Use the deployed admission predicate for permit occupancy. Sample `/proc` CPU counters and wait channels for same-PID worker children with the same live job binding. The raw job IDs, scripts and captures are private under `/home/workdir/query-catalog-studies/visits-uIh1OAiT`. The ordered snapshot SHA-256 is `5351ec202c624bad2e099312039833c015b9a53f8ca31abd3100e85861839337` and the RQ timing capture SHA-256 is `5430a53c3d3967b46f90d3e22bc7a89b068a3214e63b6d007731bf0db250f163`.

## November 22 fleet-capacity acceptance

**Failed for the natural cycle that started November 21 at 00:51:28 UTC.** At November 22 16:30:39 UTC it had run for 39 h 39 min with 4,928 cycle locators pending against a 24-hour target. The deadline had already passed before release `dfc1eaa74` activated. This observation establishes the production miss. A cycle wholly under the new owner cap and matched large-batch windows are still needed to assess the cap.

| Production check | Evidence |
| --- | --- |
| Discovery | The matching discovery generation completed in 46 min 20 s after 53,880 directory visits and 181,380 entries. The retained set held 42,681 lexical locators, including possible aliases. Both frontier and stream were empty. |
| Reconciliation | A single Redis transaction read the cursor, discovery and queue lengths. The cursor had no completion or cycle errors. Pending fell from 10,440 at 09:50:59 to 4,928 at 16:30:39, about 827 net locators/hour. This measures backlog change, including confirmation visits. |
| Freshness | On wepp2, stable double reads of 24 distinct writable scopes found 74 pending receipts. At least 21 scopes had a current-incarnation receipt older than 24 h. The oldest observed was created November 6 at 09:25:03 UTC, at least 16.29 days before readback. Old receipts occurred in all four namespaces. |
| Ordinary default queue | Six identifiable, finished non-catalog jobs enqueued and started after 08:42 UTC waited 0.040–0.134 s, below the 300 s threshold in this sample. The admission panel showed 12 compatible workers, 7 of 7 permits occupied, zero uncertain reservations and zero ordinary jobs waiting at the checkpoint. Whole-window maxima remain unknown. |
| Published artifact | Three live wepp1 refreshes supplied paths for an independent wepp2 read. One was current at readback. Its catalog digest and required schema passed verification, and the query planner and DuckDB returned the same 1,096 rows as the Parquet footer. The other two had outstanding work. Only the successful `wc1:runs` example contributes artifact evidence. |

**Observation method.** Sort the cycle-pending paths and take indices `floor(i × N / 24)` for i from 0 through 23. This yielded 12 batch, three culvert, four wc1 run and five legacy run scopes. Use the existing acceptance helper's `scope_readback` and `artifact_readback` under the worker identity. Sample ordinary arrivals from the first 4,000 reverse-ranked finished default registry entries using retained enqueue/start timestamps. These are bounded samples. The precondition for the full-union receipt census, a completed cycle, was unmet. The sample proves a freshness violation but cannot estimate fleet prevalence or the fleet's oldest receipt.

**Capacity implication.** The live scheduler allows 25 pending visits every 30 s, an optimistic 72,000 visits/day at continuous cadence. Every discovered locator needs an initial visit. A surviving writable locator that creates a full-reconciliation receipt needs another visit to confirm it drained. After 42,681 initial visits, only 29,319 visits/day remain for confirmations and retries at this cadence. The writable count is unknown. Measure first visits, clean confirmations, permit deferrals and repeated pending visits per tick alongside worker completion rate before choosing between scheduler tuning and more NFS concurrency. The observed long tail followed discovery and crossed the Rocket batch-cap boundary into three other namespaces.

**Disposition.** Fleet capacity remains unaccepted. For a retest, retain ordinary arrival observations from the first tick of a natural cycle under the deployed cap, then run the stable full-union census and namespace artifact matrix at completion. The scheduler waits 86,400 s after a completed cycle before starting the next. Release and cap-specific performance evidence remain separate. [Fleet acceptance procedure](../20261105_production_notifications_catalog_cutover/artifacts/general_catalog_acceptance_procedure.md)

Private raw evidence is retained under `/home/workdir/query-catalog-studies/fleet-capacity-OsieApDa`. SHA-256 of the cursor/arrival capture is `e529addfaa363b93c1c85c478e30aec22a631f1f71cdf4978e81b4b33b0a2ca5`, of the receipt readback `229561ed3499ff1508e447014f0d5d3f12c256c553674d4d4ab60a8490f6c1b0`, and of the peer artifact sample `a996a9793746ddd658495140b3a813db60450dadabd70271e0a1be01ff67f512`.

## November 22 production rollout closeout

Release `dfc1eaa74` is active on wepp1, wepp2 and wepp3. The same wepp1-built image passed all three host identity checks. On Rocket NFS, the candidate admitted two siblings, deferred a third and admitted another owner. All four test receipts drained and wepp2 queried all four Parquet artifacts. The final focused catalog suite passed 74 tests.

At the 09:50:59 UTC production scheduler tick, admission was open with 12 compatible default workers, a global ceiling of seven and a cap of two in `wc1:batch`. The tick reported zero reconciliation errors and zero unavailable namespaces. The current cycle began November 21 at 00:51:28 UTC. After about 33 hours, 10,440 locators remained pending and the scheduler had recorded no completion for that cycle. The configured target is 24 hours. The four catalog jobs stopped for deployment remained tracked in the dirty index for autonomous reconciliation.

Keep fleet acceptance open for a natural completed cycle with oldest-unreconciled age, ordinary-job delay and peer artifact readback. Matched production windows with large batch children remain the test of the Rocket cap's performance. At migration, clear the Rocket selector before redirecting the namespace, then reevaluate on wpc1 as recorded in the deployments repository's RKE2 cutover maintenance window. [Rocket cap decision](../../adrs/ADR-0156-rocket-batch-owner-admission.md)

## Historical status

2026-11-06: operator requests production cutover alongside notifications. Combined
planning is recorded in [production readiness](../20261105_production_notifications_catalog_cutover/notes/production-deployment-readiness.md#combined-notification-and-query-catalog-production-cutover).
Production flags remain unchanged. Confirmed blocker: the shipped scheduler YAML
still selects batch, while default-worker admission rejects batch. A no-enqueue
installed-code probe reproduced the mismatch. Repair the scheduled queue and
real-YAML regression before deployment. Default-worker pilot and general-cycle /
ordinary-arrival acceptance remain open; October 27 batch results do not close
those gates. Existing merged service env files suffice for feature configuration.


2026-10-28: operator authorized moving query-catalog refresh/inventory to default workers because batch backlog can last days. Contract checkpoint `0e6302905` passed independent correctness/security reviews and was committed before runtime edits. Implementation, 129 focused real-Redis tests and local forking-worker job-tree/artifact readback pass. Broad Python sweep stopped at preexisting Roads provenance mismatch after 6,810 passed/61 skipped; not a full-suite pass. Local implementation complete; production migration pending. See [validation](artifacts/20261028_default_queue_validation.md). October 27 deployment/pilot status below is historical for batch routing.

2026-10-27 UTC: **Authorized bounded execution complete; general enablement HOLD.**
Full canonical deployment of `0da9c9071` completed on wepp1–3. The actual shared
batch pilot passed 17 jobs, both eight-scope artifact waves and 48 query checks,
receipt acknowledgment, sentinel isolation and explicit pause/resume recovery.
All nine scratch scopes are retired outside managed roots; eight compatible
batch consumers remain healthy. General async is disabled and roots are unset.
See [acceptance](artifacts/20261027_shared_pilot_acceptance.md).

Earlier undeployed/active-job-hold statements below are historical checkpoints;
the full deployment superseded source-only candidate preparation.

## Progress

- 2026-10-23 UTC: User authorized comprehensive async-preferred contract and delegated review.
- 2026-10-23 UTC: Three analysis agents completed 79-call/41-file writer and reader/lifecycle/queue inventories.
- 2026-10-23 UTC: Canonical draft and five cross-contract amendments prepared; independent reviewers raised eight findings, all dispositioned into revised design. Both reviewers confirmed closure at 2026-10-23 20:20 UTC.

## Decisions

- Preserve synchronous consumers until evidence supports an explicit migration.
- Reuse existing infrastructure; retain durable receipt-set acknowledgment beyond queue admission.

## Review and validation

Contract and implementation reviews, scientific/report acceptance, four-root
discovery, timeout recovery and HTTP responsiveness evidence remain retained.
The deployed pilot adds genuine shared-worker lineage, raw artifact-before-consumer
readback, seven-job reconstructed peak, explicit pause/resume and guarded scratch
retirement. Independent correctness and security execution reviews pass; the
secondary QA artifact records final documentation consistency. This operational
completion changed no executable code and requires no repeat of prior code suites.

## Remaining gates

No implementation, deployment or bounded-pilot execution remains pending in the
authorized slice. Whole-fleet enablement remains a distinct HOLD: establish
complete-cycle progress/oldest unreconciled age and ordinary-arrival queue delay
under an explicitly bounded rollout before enabling general async. The pilot
contract does not authorize broad enablement after success. The preexisting
legacy mount limitation remains outside scope; no routing change is planned.

Retained limitations: no new ordinary batch arrivals were observed during this pilot;
a drained controller restart created a 90.32-second observation gap; original
refresh-status bytes were overwritten by legitimate post-acceptance retirement,
so their exact independent replay is unavailable. A low-priority expired-controller
readback limitation was not exercised. These do not convert this pilot into
whole-fleet acceptance. See the independent correctness/security/QA artifacts.

## Handoff evidence

Canonical decision: `docs/schemas/query-engine-catalog-refresh-contract.md`, especially Migration policy and interfaces, Durable invalidation and no lost updates, Publication and synchronous coexistence, Reader freshness and caches. Caller matrix inventories 79 invocations/41 files plus wrappers and direct readers/writers. Five binding contracts amended with scoped coexistence/disclosure/lifecycle clauses. Runtime acceptance is intentionally pending.

## Final validation

- `wctl doc-lint` passed for all six changed/new canonical contracts, eight package documents and PROJECT_TRACKER.md: zero errors/warnings.
- `git diff --check` passed.
- Spelling previews found no changes in the new domain contract/package/matrix. Shared contracts had only preexisting wording suggestions (non-participating, warmup, Oversized); preserved to avoid unrelated edits.
- No runtime tests run: this is a documentation-only contract phase. At contract-phase validation no commit, production write, deployment or repair had been performed; subsequent authorized commits are recorded below. Unrelated dirty workspace files were preserved.

## Execution scaffold handoff

- 2026-10-23 UTC: Operator requested “commit and scaffold work-package for execution”. Committed accepted checkpoint as `dc2b2ddbe` before creating this execution scaffold.
- Active plan: [implementation_execplan.md](prompts/active/implementation_execplan.md).
- Launch prompt: [execute.md](prompts/active/execute.md).
- Evidence ledger: [execution_evidence.md](artifacts/execution_evidence.md).
- Contract plan moved to `prompts/completed/contract_execplan.md`; its historical status is superseded by this handoff.
- M0 baseline is recorded; M1–M6 implementation/validation active; M1–M3 are prerequisites for producer migration. Runtime changes are implemented and undergoing validation; deployment and repair claims remain false.
- Scaffold commit is the commit introducing this section, immediately following the standalone checkpoint. Resolve with `git log -1 --format=%H -- docs/work-packages/20261023_query_catalog_async_refresh/prompts/active/implementation_execplan.md`.

## Active execution baseline

2026-10-23 UTC: host forest, workspace /workdir/wepppy; existing dev stack running, web/batch identities uid1000/gid993, shared /wc1 NFS4 from 10.0.0.2. Contract ancestry check passed. Seven agents own native, publication core, queue/recovery, lifecycle, readers, polling privacy and producer slices; parent owns integration/evidence/docs. Native preexisting calendar/HBP/module-registry edits are preserved. Production wepp1 access in this phase is read-only diagnosis/source-copy only. Deployment and run repair remain excluded.

## Implementation validation in progress

- Native GIL release: 111 Rust unit, 17 integration and 2 Python before/after regressions passed; Python startup pin tests 10 passed. Paired build provenance is retained in `artifacts/native_release.json`.
- Stable guard: cross-host NFS client/server-local `flock` did not exclude; POSIX `lockf` plus per-owner thread coordination passed actual-core cross-host (4.375527 s) and thread (2.002313 s) exclusion.
- Producers: 162 focused tests plus 32 RUSLE/Omni tests; exact family dispositions in `artifacts/producer_migration.md`.
- Polling: 102 tests and real Redis corrupt-payload probe passed. Queue/scheduler real Redis regressions and generated dependency graph pass; fault coverage is expanding.
- Lifecycle: readonly drain and fork symlink regressions 16 passed; Roads/archive 68 passed, including process concurrency and archive bytes.
- Independent reviews required fixes for metadata symlinks, READONLY transitions, nested scope recovery, worker capabilities, parent-source precedence, schema freshness and catalog-root authority. Post-fix review remains required.
- Isolated scientific clone completed (9,270,055,877 logical bytes, 4,559 regular files) at `/wc1/runs/qc/qcat-mill-creek-20261023`; authenticated submission/model validation is starting with an isolated queue and two CPU cores.

2026-10-23 UTC final implementation reviews: correctness, security and QA confirmed closure of their blocking findings. Final permission tests preserve mode/ownership/ACL/xattrs, protected malformed history and legacy new-file umask behavior. Consolidated final-source suite293 passed,2 opt-in benchmarks skipped; full repository regression and model completion still pending.

2026-10-23 UTC: Additional reviewed contract checkpoint `9435cd2cb` preserves explicit source selection and concurrent Roads shared reads. The bounded read exception and rationale are retained in `artifacts/2026-10-23_implementation_contract_clarifications.md`; runtime remains uncommitted. Broad validation stopped6688passed/61skipped on required Roads provenance regeneration. Fresh native Roads evidence and remaining repository tests are active; no test gate is relabeled passed.

2026-10-23 UTC: Independent fresh Roads comparison passed all 516 cases and 80 project Parquet tables; canonical publication is finishing. Remaining broad tests reached 4,556 passed/95 skipped before a synthetic readonly catalog fixture failed; canonical version metadata and idempotent fixture directory creation corrected it, and all 79 route-module tests passed. Further remainder validation is active.

The isolated model completed all 1,908 hillslopes. Catalog query, authenticated summary and exact-byte live download pass. Water-balance report rejects duplicate observations already present in raw `H1.wat.dat`; original production output is absent, so baseline causality is unproved. Watershed and its scoped completion supervisor continue unchanged. This explicit scientific-output limitation prevents claiming full workflow acceptance.

2026-10-23 22:59:54 UTC terminal model result: watershed failed at simulation year 100 with `PASS components error: SOURCES3 date mismatch` and `STOP 1`. The scoped supervisor stopped on failure, leaving finalizers deferred; zero catalog receipts remain pending. No scientific repair, shortened rerun or validation bypass was performed. M4 full-workflow acceptance remains blocked; native build provenance includes preexisting calendar/HBP edits and baseline causality is not established. Final broad regression remains active after a test-only worker-supervisor isolation correction.

Final local validation: the last complete attempt passed 7,629 tests/64 skips before its teardown exposed the transaction-metadata bug. Fixed the actual enqueue hook to keep metadata inside the caller's WATCH transaction; 70 focused tests and 17 independent security cases passed. The final broad remainder passed 5,108 tests/18 skips in 546.59 seconds. Coverage is segmented, not one green full-suite result. Exact commands and results are retained in `artifacts/regression_validation.txt`; source hashes in `artifacts/implementation_source_manifest.json`. All owned model workers/supervisor exited; temporary Redis is removed after validation. Private diagnostic project artifacts are retained. M7 handoff complete; M4/M6 full acceptance remains open.

Commit/push handoff: user authorized committing and pushing the implementation. This checkpoint includes the reviewed task files and retained validation evidence; paired native commit is `47e51b8e73146872056b68934977db56d91c9119`. Earlier uncommitted-state notes are chronological. Scientific acceptance remains blocked, async rollout remains disabled, and no deployment or production repair is authorized by this push.

## October 26 resumed execution

Fresh case `qcat-mill-creek-20261026` preserves 184 years and 1,908 hillslopes;
authenticated submission returned 200 in 0.950684 s. Root job
`cfddc361-6e18-497f-becf-66d8fe496cbd` started at 17:29:04 UTC on the isolated
queue with `wepp_261021`. An inherited zero-byte failed report cache initially
blocked strict refresh; quarantining only the fresh copy's generated reports
allowed normal retry to publish and acknowledge the pending receipt. Scientific
and consumer completion remains pending. Evidence: [resumed acceptance](artifacts/20261026_resumed_acceptance.md).
Production preflight: [retained observations](artifacts/20261026_production_preflight.md).

Early raw-output check at 17:36 UTC: new `H1.wat.dat` has **67,205 unique daily
records across all 184 years**, with complete Gregorian day counts in every year
(including years 100 and 104). This first-hillslope check passes where the old
case duplicated dates. It does not establish watershed or full-run completion.
Retained result: `/wc1/query-catalog-validation/20261026/early-H1-raw-dates.json`.

17:41 UTC: Independent resumed-harness review closed all six findings. More than 530 hillslopes have completed; the scoped completion supervisor remains running. Full acceptance and production enablement remain pending.

## October 26 terminal acceptance and rollout gates

Full fresh local acceptance passed at 21:38:50 UTC: all 18 jobs finished, all five
artifact/report checks passed, 1,908 profiles contain all 67,205 unique daily keys
and pending receipts are zero. See [terminal evidence](artifacts/20261026_terminal_acceptance/acceptance-supervisor.json). Earlier running/blocked
statements describe prior checkpoints. Operator requested remaining rollout gates;
production latency, inventory/capacity and explicit namespace/workflow parity are
under measurement. Async production remains disabled pending those results.

Production gate result: **HOLD**. Representative receipt-free reconciliation
passed under uid1002/gid130 with a normal forking RQ worker (7.762 s); all 79
selected Parquet tables read back. Active legacy ownership, stalled legacy
enumeration and conditional HTTP event-loop contention prevent unrestricted
enablement. [Gate disposition](artifacts/20261026_rollout_gate_disposition.md) records
exact evidence, limitations and remaining work. M6 remains open.

## October 27 authorized remediation

Operator approved the recommended four steps. HTTP offload is classified as
conformance repair preserving synchronous freshness/auth/error contracts with
native GIL release already present. Inventory progress design is being reviewed
before edits. Runtime/mount permissions and queue topology remain unchanged.

Inventory checkpoint `09ce55d1d` is the reviewed ancestor. Implementation and
40 real-Redis tests are complete pending independent findings; production read-only
full inventory and broad regression are running. HTTP private production canary
passes; health saturation follow-up active. Legacy role finding and scoped routing
proposal are retained in `artifacts/20261027_legacy_routing_proposal.md`.

October 27 final bounded reviews: inventory 66 real-Redis/filesystem/privacy tests
passed with containment, root-loss and alias findings closed; HTTP 199 local tests
and 8 independent focused tests passed. Final source private NFS/ASGI canary
passed with a saturated test pool: `/health` 1.5–2.6 ms during 30 s guard waits.
Three-primary-root real-RQ inventory finished 15,399 directories/10,192 scopes in
2,000.7 s with zero errors. Its driver assumed an enum status on older RQ; retained
post-run assertion failure was corrected and terminal job/frontier/stream readback
verified independently. Legacy replay/full traversal and broad regression continue.

Broad regression: 11,621 passed/170 skipped before the unrelated browser test
failed because the container's Playwright path omitted a `wepppy` directory.
The installed browser was used via a process-local environment override; the
failed module and remaining current modules passed (183 tests). This is segmented
evidence, not a single green full-suite run; final-source focused inventory/HTTP
checks cover edits made while the broad run was in progress. Logs:
[initial](artifacts/remediation-broad.log), [remainder](artifacts/remediation-broad-remainder.log).

Full four-root discovery now passes: 30,891 unique scopes, zero errors, empty
frontiers and stream/set equality. Legacy consumed 4,032.650 process seconds
across a fenced restart. A separate actual RQ timeout and scheduler retry
completed three owned scratch catalogs with zero receipts. Evidence:
[full discovery](artifacts/20261027_full_inventory.md),
[timeout/retry](artifacts/20261027_inventory_rq_timeout_canary.md).
Capacity classification/profiling and the legacy routing decision remain open.

October 27 operator scope disposition: “i don’t care about the read only mount.”
The preexisting legacy mount/fork-archive limitation is outside this release and
is no longer a catalog-rollout blocker. No routing or mount change follows; all
four catalog namespaces remain included. The routing proposal is deferred.

Final bounded capacity evidence is complete: 48 selected real scopes measured,
47 first verifications complete, two process-budget censors retained; full
25-candidate scheduler admission/recheck/retirement/READONLY ticks pass. Fleet
capacity remains HOLD rather than extrapolating these probes into a guarantee.
[Current disposition](artifacts/20261027_remediation_gate_disposition.md). Final
live readback confirms original source, async disabled and roots unset across
all nine checked roles.

The final independent capacity assessment retains CAP-01/HOLD and recommends a
bounded admission guard before a shared-queue pilot. The concrete seven-job
proposal and pilot bounds are in
[bounded admission proposal](artifacts/20261027_bounded_admission_proposal.md).
Operator subsequently authorized this additional admission policy; guard and
pilot implementation are active, with no general enablement. No more component-only probes are planned.

## Historical bounded-pilot preparation
Historical pre-deployment operator decision (2026-10-27 UTC): remain on standby and use the full canonical deployment after default and batch jobs clear. No active-job exception is approved or implemented. The scoped batch candidate remains retained evidence, not the selected rollout path. Deployment and actual pilot execution remain pending; general asynchronous refresh stays disabled.
Operator instructed “execute the bounded pilot.” Admission-policy approval is
resolved. Contract checkpoint, disabled-mode owned-scope isolation, authentic
worker deployment, implementation and shared-batch acceptance are active.
General enablement remains excluded; no additional policy confirmation is needed.

Bounded-pilot contract checkpoint `5c1edb22a` committed after independent
correctness/security PASS, before any pilot runtime edits. RQ guard/operator
controller and canonical source-only targeted batch deployment implementation
are now active. Baseline production image fingerprints are retained.

Local pilot implementation is complete: 72 final RQ integration tests,
24 operator tests and 56 deployment tests pass, with independent correctness PASS.
The broad regression passed 11,862 tests with 201 skips; independent security review passes. Production is unchanged;
one default `run_watershed_rq` job still has a fresh heartbeat and blocks the
existing deployment gate. Eight batch consumers are idle. Do not bypass the gate
or represent local mechanism validation as a completed shared-batch pilot.

Security reproduction found running `Job.cancel()` could free a permit early.
The corrected claimed-canceled exit marker passed an actual-process regression
and the final 72-test RQ suite, preserving killed-worker recovery. Independent
security closure passed 86 RQ/disclosure and 80 operator/deployment checks; no
production source is installed.

All local gates are closed. Final RQ 72-test evidence follows the last cancellation
fix, which occurred after broad-test collection; this is segmented source evidence.
Production remains at clean revision 813d on both hosts and the same default watershed job
continues heartbeating. The prepared pilot is held at that explicit active-job
gate; a one-job exception requires operator approval and is not implemented.
[Current pilot disposition](artifacts/20261027_bounded_pilot_gate_status.md).

## October 27 completed shared-batch execution

The later full deployment and resumed pilot supersede the immediately preceding
standby statements. [Acceptance](artifacts/20261027_shared_pilot_acceptance.md) and
[sanitized results](artifacts/20261027_shared_pilot/summary.json) are current.
General enablement remains excluded; whole-fleet capacity is not declared passed.

## November 6 authorized combined production cutover

Execution now follows the operator-authorized
[production cutover package](../20261105_production_notifications_catalog_cutover/tracker.md).
Scheduler routing correction and full regression passed. All three hosts deployed
with twelve real default consumers and general async initially false.
The exact two completed expired permits were retired with independent review,
without resetting ledger identity or pilot history. Owned catalog admission pause
remains set. Fresh default-worker pilot qcat-20261106-default01 passed two waves
on eight scopes with actual artifacts/query readback and ordinary waits below
0.13 seconds. General enablement is staged on all hosts; wepp1's second canonical
deployment passed and wepp2 is building. Complete-cycle observation remains open.

### November 6 09:44 UTC superseding checkpoint

All three second canonical deployments completed. General async is true and
converged; scheduler root/coordination parity passed after the wepp1 mount-anchor
repair. Observation 01 failed a manual supervision interval and was contained;
its evidence cannot establish acceptance. Independently reviewed observation 02
is now running with paired machine supervision, admission released, no cycle
errors and no unavailable namespaces. Controls are published at 0c0b48dbe.

The fixed deadline remains November 8 08:39:54 UTC. Existing f63a3a51 baseline
cycle is excluded; acceptance requires a different naturally scheduled complete
cycle, new ordinary arrivals during that cycle, independent full-union age census
and artifact proof. Sample coverage gaps and owned fixture/account cleanup remain
open. See the combined package's active ExecPlan observation-02 handoff; do not
reset state, shorten cycle spacing or extend the deadline to force completion.


## November 21 admin catalog monitoring

Contract checkpoint `2dacc6b57` adds the Admin/Root snapshot. Dedicated panels
show simultaneous admission blockers and the latest committed reconciliation
summary. Route and real-Redis suites passed 58 tests. See the
[decision and reviews](artifacts/20261121_contract_decision.md).

## November 21 Rocket batch-owner admission pilot

The [implementation and retirement plan](prompts/active/implementation_execplan.md#temporary-rocket-batch-owner-admission-pilot) targets worker capacity during the remaining Rocket deployment. Implementation, live RQ validation and rollout are pending. The wpc1 migration triggers a fresh baseline with the override disabled.

The [worker continuity gate](prompts/active/implementation_execplan.md#worker-continuity-during-rollout) stages the disabled code with a routine deployment and verifies live activation and rollback with both worker pools serving jobs.

The candidate implements the optional watched namespace policy, owner counts
and last-tick deferral telemetry. Deployment and matched-window acceptance are pending.
