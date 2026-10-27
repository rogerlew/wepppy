# RQ 2.12 migration correctness review

## Metadata

- Reviewer: independent `checkpoint_correctness` agent, reviewer role.
- Review phase: final installed implementation and artifact acceptance; isolated committed-source full suite passed, with unrelated working-tree provenance failure retained separately.
- Date: 2026-10-27 UTC.
- Starting implementation revision: `9231f2427d33b64f971992ac969fd9420c49afd3`.
- Accepted ancestor: `b1054fac7` (`docs: ratify RQ 2.12 migration checkpoint and execution plan`).
- Installed implementation: `b5cac8166eaf067ac2ef79c440a82314c114111b`; dashboard sibling `91f62b9c1d71918c9ecd173e2eea5e383d624687`.
- Scope: migration changes after the ancestor, including shared image/dashboard dependency inputs, enqueue metadata hooks, status/timestamp/registry consumers, direct Redis/worker regression tests and historical-state fixtures.
- Excluded: unrelated Roads NoDb/template/test/documentation edits present before this package.
- Canonical authorities: checkpoint's Applicable contracts and discrepancy classification section; particularly RQ response, directory maintenance ownership, batch task boundary, catalog recovery, fork readiness and run-sync replacement contracts.
- Related reviews: `20261027_checkpoint_correctness.md`, `20261027_checkpoint_security.md` and final security review when available.

## Findings

| ID | Severity | Surface | Finding and evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | Separate dashboard dependency detail | `/workdir/rq-dashboard/rq_dashboard/web.py:617` decodes each `job.dependency_ids` member as bytes. The running dashboard's RQ 2.0 property returns bytes, verified by `wctl exec rq-dashboard python` source inspection. The verified RQ 2.12 distribution returns `list[str]` (`rq/job.py:1767`). A dashboard detail request for a dependent job therefore raises `AttributeError` after its image upgrade. | Repair the actual sibling dashboard source/integration path while preserving bind-mount behavior. Exercise dependent-job detail through the rebuilt dashboard HTTP boundary with real RQ dependencies. Retain the required sibling change as part of the delivered change set. | Resolved: exact string IDs preserved and legacy byte-key prefix removed; retained `docker/patches/rq-dashboard-rq212.patch`. Both 2.0 and 2.12 real HTTP detail return 200, and two focused dashboard regressions pass. Installed RQ 2.12 dashboard JSON and HTML detail return 200 for two actual dependent model jobs, with exact dependency IDs and source hash (`dashboard-installed.json`). |
| COR-02 | Medium | Admin job details rendered status | `wepppy/rq/job_listings.py:154,236` return raw enums. `wepppy/weppcloud/routes/rq/info_details/templates/info_details.htm:62,178` interpolate `job.status` directly, yielding `JobStatus.FINISHED`/`JobStatus.FAILED`. JSON compatibility and equality-only tests miss this indirect consumer. | Normalize both shared listing status fields to plain values. Add actual template rendering and exact plain-string assertions for finished/failed listing rows; retain active listing shape. | Resolved: 2026-10-27 19:21 UTC; exact value extraction and real template tests reviewed; `compat-listings-before.log` fails before repair, `compat-listings-after.log` records 15 passed. |

## User outcome and unchanged error policy

Users retain existing task submission, exact IDs, acknowledgments, status and dependency behavior, cancellation authority, recovery and generated results. Expected absent/expired jobs retain not-found behavior; blocked strict graphs remain blocked and may be reconciled before a new submission. Terminal observer edges must not consume failed scientific prerequisites. Invalid ownership or malformed task identity must fail within the existing authorization boundary. This dependency migration authorizes no new user-visible failure policy.

## Failure-class assessment

The confirmed class includes removed RQ clock APIs, enum string conversion, timezone-aware arithmetic/serialization and composite started-registry IDs. Review traced shared listing outputs into real Jinja consumers and inspected the independently built dashboard's actual dependency API use, exposing COR-01 and COR-02 beyond the initial inventory. Main repository dependency traversal helpers already accept bytes or strings and strip only the known `rq:job:` prefix. Existing string equality and JSON encoding remain valid for RQ's string-valued enum; explicit string formatting is the changed boundary.

The migration retains exact worker success/failure override signatures, matching the released 2.12 distribution rather than master. The metadata repair attaches actor/correlation/profile fields before actual enqueue publication, preserving caller-owned transaction boundaries and existing explicit metadata precedence. The tests read Redis before outer wrappers could repair metadata and exercise aborted/committed pipelines, lost acknowledgment, positional arguments, real root/child workers and unrelated-job context isolation.

## State matrix

| State | Validity and required behavior | Evidence inspected | Gate |
| --- | --- | --- | --- |
| Job absent/expired | Valid absence; existing not-found result | Installed status/disclosure/recovery selection | Pass |
| Empty queues/new work | Valid; submit and execute normally | Installed real-Redis lifecycle suite and actual API/model workflow | Pass |
| Populated strict graph | Valid; success releases dependents once | Installed lifecycle/reconciliation suites and 18-node actual model graph | Pass |
| Failed prerequisite and approved terminal observer | Strict work blocked; observer runs only terminally and cannot consume missing output | Real failed/stopped/interrupted-dequeue cases; installed batch tests; actual failed graph and obsolete cancellation | Pass within documented direct stopped-parent scope |
| Immediate/scheduled retry | Attempt failure is not terminal; no early strict release | Actual worker/scheduler, retained result and attempt-count assertions | Pass |
| Stop/timeout/SIGKILL/abandonment | Existing terminal states, containment and inspectable failure | 13 installed lifecycle tests and 17 directory-lock/containment tests without skips | Pass |
| Historical six-state records | Readability plus proven supported transitions; old running jobs drain under old runtime | Genuine 1.16.2 records, original-state rollback and installed replay | Pass for stated bounded matrix |
| Malformed/hostile identity | Existing authorization/ownership rejection | Installed auth/cancel suites; actual missing-bearer 401 and wrong-run 403 preserve queued state | Pass; independent security review also finds no regression |

## Historical-job and rollback limits

The retained historical evidence uses genuine 1.16.2 writes. Actual forked workers and the scheduler execute drained queued/deferred/scheduled fixtures under 2.12, while completed/failed records remain readable. Old running entries are intentionally not treated as 2.x execution leases. The documented prohibition on running handover and mixed-version execution is appropriate.

The isolated rollback proof restores original frozen records and runs 1.16.2 again. It does not establish reverse compatibility with 2.12-written state, arbitrary historical function imports/custom IDs, whole-stack snapshot consistency or live rollback. Keep these limits explicit in final operator documentation; inventory actual retained records and require empty old started registries before cutover.

## Generated artifact evidence chain

| Stage | Required evidence | Current review disposition |
| --- | --- | --- |
| Request intent | Actual API/auth payload and bounded disposable project provenance | `acceptance_upgraded.json` records fork, expected failure, normal API recovery, ownership rejection and same-target resubmission |
| Persisted state | Normal-reader durable state matches accepted intent | Independent baseline/candidate readback agrees on executable, pass family, config and climate mode |
| Generated intermediate | Content hashes and semantic fields | Exact file sets and SHA256 readback; generated decks specify actual consumed paths |
| Consumed model input | Actual paths and parsed content used by model | All 155 non-diagnostic files are byte-identical; 29 `.err` files differ only as documented diagnostics |
| Execution output | Fresh outputs, exact job tree and rebuilt runtime | 18-node finished graph; all 25 Parquets written during candidate run, exact values and decoded metadata, one order-only rank table difference |
| User-facing result | Actual report/output retrieval under normal authorization | Three authenticated CSV reports agree exactly; archive/download hashes agree. Deleted-file restoration passes after documented NFS descriptor recovery; independent post-retry check verifies all 417 hashes and 25 exact Parquet schemas/values |

No job-status-only, import-only or mocked acceptance is approved. New lifecycle tests use real Redis, subprocess workers, execution registries, scheduler and pool replacement. Their outbound audit detects attempted TCP delivery in ordinary worker descendants; it supplements source/configuration checks but does not alone establish every installed workflow's egress behavior.

## Verdict

**Gate status: PASS for the RQ migration.** Zero unresolved high or medium migration source findings. Both source findings are closed with regression and installed-runtime evidence. The implementation, historical replay, worker lifecycle, containment, API/model outputs, recovered restore and installed dashboard have passed their reviewed gates. The complete isolated committed-source suite passed **11,948 tests, with 226 skipped and 5,826 warnings**, in **3,304.46 seconds**. This closes the required broad-regression gate for the migration source and rebuilt runtime. The original `wctl run-pytest tests --maxfail=1` invocation on the preserved user working tree remains **1 failed, 6,810 passed, 61 skipped** in 2,798.93 seconds: its independently reproduced Roads source-provenance mismatch is not an RQ regression and is not relabeled as a passing invocation. The existing NFS retained-log-handle restore limitation and bounded recovery must remain in the handoff. Production rollout is outside this package's authority; native webhooks remain disabled and unexposed.


## Additional worker and dependency review — 2026-10-27 19:26 UTC

Reviewed `rq_worker.handle_job_failure`, `job_dependencies.release_deferred_job_if_ready`, `project_rq._enqueue_serial_subcatchment_tree`, their real Redis/process regression additions and `worker_compatibility_repairs.md`.

The stopped-job flag is captured before RQ 2.12 clears it. The compatibility path visits only explicitly failure-tolerant dependents and verifies the exact stopped parent at a WATCH-protected promotion. It watches the dependent hash/dependency set and all prerequisite hashes/dependent sets, rejecting strict edges, canceled observers, missing prerequisites and unfinished/canceled/stopped siblings. Repeat promotion observes non-deferred state and cannot duplicate enqueue. This restores approved direct stopped-parent observers without introducing broader fan-in behavior. The existing limitation for a stopped prerequisite followed by an unfinished sibling remains explicit and unextended.

The shared helper previously permitted failed prerequisites without checking the dependent's strictness. The new condition restores the unchanged strict-output contract. The removed Job version-cache method is replaced by the existing queue's cached value before MULTI; actual serialized-tree tests cover both runtimes. The inline test-worker executor change explicitly restores its intended SimpleWorker execution after the RQ class hierarchy changed, while separate process tests retain actual fork/stop coverage.

Retained evidence: 64 worker/dependency/WBT tests pass on both runtimes; 26 batch-boundary tests pass on candidate RQ; stubtest and stub completeness pass; the independent actual-stop test confirms tolerant completion, strict blocking and successful subsequent supervisor work. Final rebuilt-runtime reruns remain necessary.

Four additional dependency pins retain the installed forest versions of FastAPI, narwhals, pkginfo and python-dateutil after a canonical rebuild exposed unrelated resolver drift. This is within the behavior-preserving migration budget. The final installed-distribution comparison must still establish that only RQ and required croniter differ; fresh old/new resolution alone cannot establish that.

The dashboard agent additionally found and repaired its old `StartedJobRegistry.remove` call for missing job hashes. The new branch uses public execution removal on the exact parsed job ID, while other registry behavior remains unchanged. Real owned-queue HTTP cleanup tests return 200 and leave zero started members on RQ 2.0 and 2.12. This is a bounded consumer repair, not authorization to empty any live queue.


## Scheduler socket review — 2026-10-27 19:34 UTC

Reviewed the new `_start_scheduler` and `run_maintenance_tasks` overrides against the released RQ 2.12 worker and scheduler implementation and pinned Redis 6.2 pool implementation. The scheduler override signature and logging defaults match upstream. `ConnectionPool.disconnect(inuse_connections=False)` holds the pool lock and disconnects only available connections; it leaves the checked-out pubsub connection and thread intact. RQScheduler creates a separate pool for lock acquisition, so startup does not reopen the worker's available dequeue connection before forking. Maintenance scheduler replacement also crosses a fork boundary and receives the same bounded cleanup.

The change preserves queue topology, scheduler lease behavior, maintenance cadence, job timeout and runtime identity. Reconnection of ordinary idle Redis clients is the intended local effect. The reported failure was reproduced under both old and new runtimes; fixing it restores the requested pool-replacement behavior rather than attributing a baseline defect to 2.12.

Direct probe logs inspected at this review show initial pool replacement completing the next job with an empty intermediate queue, and maintenance takeover creating a replacement scheduler, successfully running a scheduled job, then removing the killed supervisor's blocked client before a new worker executes subsequent work. These probes and their supporting runners must be retained in package artifacts, not only temporary cache paths. Full lifecycle and final rebuilt-runtime results remain separate gates. No new source finding was identified.

The final installed-distribution comparison now records exactly two differences: RQ 1.16.2 to 2.12.0 and added croniter 6.0.0 (`installed-dependency-delta.json`). Durable dashboard sibling-patch check/apply/already-applied instructions are now present in `docs/dev-notes/rq-2-12-migration.md#dashboard-source-patch`, closing that documentation obligation.

## Installed forest review — 2026-10-27 19:49 UTC

Reviewed the installed implementation commit and current working-tree diff; only unrelated Roads source edits are outside the reviewed committed runtime. [Cutover evidence](forest_cutover.md) establishes the canonical rebuild/recreate and warm-stop sequence. [Drain readback](cutover-drain.json) has no registered workers or started/intermediate members before new consumers start. [Runtime readback](forest_runtime.json) records 17 running containers, each importing installed RQ 2.12.0, with no restart count. Main services retain Redis 6.2.0 and dashboard retains Redis 5.2.0. Identity, groups, mounts and umask are recorded; the main image is `88a982e44d316824f493c99d0c3a9a3db3e4800feef86ff2c65693677039162b`, dashboard `019fbdf6ba5c5027149115e30818a8542b6bf33c78be43bc8e77fe841beb2087`.

The [rebuilt targeted selection](rebuilt_targeted_validation.md) passes **598 tests without skips**: 10 historical/metadata, 73 batch/query, 498 existing recovery/API/worker tests and 17 containment tests. The separate [installed lifecycle suite](rebuilt-lifecycle.log) passes **13 tests** in 201.70 seconds. These totals describe separate selections, not a deduplicated full-suite count. The initial retained external-Redis abandonment failure is explained by prior package-owned DB0 fixtures; the exact-scope cleanup receipt and clean full 73-test repeat are retained. No assertion or production fallback was weakened to obtain that result.

Reviewed actual [acceptance](acceptance_upgraded.md), request receipts, normal-reader harness, exact comparator and archive/restore harness. The comparator checks original readback hashes against current files, identical file sets, byte equality for consumed inputs, exact Parquet schemas/values, and exact HTTP CSV rows. Supplemental encoding evidence checks decoded schema metadata, explaining serialized `ARROW:schema` order differences. The rank table differs only in row order; sorting every column yields exact values. All 25 candidate Parquet mtimes fall between 19:40:23 and 19:40:40 UTC, within the actual completed run rather than inherited source outputs. Existing climate fixture files retain their old dates; their identical bytes are appropriate supplied inputs, not claimed freshly generated climate data. The `.run` decks name the consumed management/slope/climate/soil and watershed-pass files.

The actual failed preparation leaves strict downstream work blocked; a normal API binary selection and resubmission cancels 12 obsolete descendants and finishes the new 18-node graph. Unauthenticated cancellation returns 401 and signed wrong-run cancellation returns 403 without changing the queued job; authorized cancellation succeeds before start, followed by successful same-target fork resubmission. The baseline source remains separate from both disposable targets. Instrumented lifecycle workers report no attempted TCP delivery, and all 39 inspected API graph/fork jobs carry actor/correlation metadata with zero configured webhooks. Profile propagation/isolation is established separately by actual subprocess tests, not inferred from the unprofiled model run.

The [installed dashboard HTTP record](dashboard-installed.json) closes COR-01 against real completed dependent model jobs. The retained sibling source hash is `6b72ffffa2b8fb504a21132eac5aef8fbaded49d4b06df738c0cd8a060134c34`; both JSON and rendered HTML return 200 and retain exact dependency IDs. Loopback service evidence is not a claim of a new proxy authorization boundary.

Worker/dependency stubtest, test-stub completeness and dependency-graph checks pass. The changed-file broad-exception check against `origin/master` passes; code-quality observability is retained and explicitly observe-only. Its Python cyclomatic-complexity values are unavailable because `radon` is absent, a disclosed measurement limit rather than a failed correctness gate. Source growth is concentrated in targeted real-process regressions and bounded worker compatibility hooks; no unrelated refactor is required by those metrics.

Residual compatibility limits remain explicit: no mixed-version workers or running-job handover; no in-place downgrade on 2.x-written Redis; historical fixtures do not certify arbitrary imports/custom IDs; stopped-parent fan-in with a still-running sibling retains its existing limitation. The isolated original-state rollback proof does not certify live whole-stack restoration. Production was not upgraded and native webhooks were not enabled.

## Restore-effect follow-up — 2026-10-27 19:50 UTC

The initial archive harness compared generated files before and after restore without modifying them. This establishes retention and archive readback but would also pass for a no-op restore. The reviewer requested a stronger disposable-only check: delete or change one generated file after archiving, run the canonical restore API, then prove the archived hash and ordinary report readers recover. The parent reports that deletion was confirmed, but the next restore failed before extraction with NFS busy-file `Errno 16`. The acceptance agent is investigating the exact package-owned file descriptor and supported recovery without terminating unrelated work. Preserve this failed observation and do not use the earlier matching-file test to mask it. Restore acceptance remains open until actual recovery and complete file/report readback are retained.

### Recovery verified

[Recovery receipt](acceptance_restore_repair.json) and the resume harness confirm the sentinel output was still absent immediately before canonical retry `cb1c0901-5564-45a9-a649-5aeebe7135e5`. The installed worker finished; restored SHA256 `1a41623beb5222c62aecd740edc6de07e6a7dc1db46a0c6f06e7308394ee3af7` matches both the archived bytes and original file. Actual HTTP outlet CSV returned 200 and identical bytes. The failed job remains inspectable in [initial failure](acceptance_restore_repair_initial_failure.json).

The [NFS mechanism probe](acceptance_nfs_mechanism.json) reproduces unlink/open-file `.nfs` retention and `Errno 16` without importing RQ, at the same UID1000/GID993, and verifies closing the file removes the obstruction. Independently compared `project_rq_archive.py`, NoDb base and report handlers against starting revision `9231f2427`; those paths are unchanged. This supports an existing filesystem/logging limitation rather than a new RQ behavior. The supported local recovery gracefully recycled web/API processes holding stale package log descriptors and preserved workers and the active pytest process. The operation and limitation must remain documented; no general NFS hardening is introduced here.

The reviewer then independently executed a read-only `wctl exec -T weppcloud /opt/venv/bin/python -` check against the recovered files. It enumerated the original archive's 417 `wepp/runs` and `wepp/output` members and compared SHA256 with every actual restored file. It also reread all 25 candidate Parquets and compared schema metadata and exact values with baseline, sorting all columns only where order differed. Result:

```json
{"archive_files_checked": 417, "all_generated_hashes_match_archive": true,
 "parquet_schemas_and_exact_values_equal_baseline": 25,
 "restore_job": "cb1c0901-5564-45a9-a649-5aeebe7135e5"}
```

This independently closes the stronger restore-effect and final generated-content gate. The full repository suite remains pending.

## Broad-suite provenance failure disposition — 2026-10-27 20:28 UTC

The installed full run stopped at `tests/roads/test_roads_publication.py::test_published_results_and_sources_are_current_or_explicitly_stale`. This test checks exact published scientific evidence/provenance hashes and an explicit reviewed-staleness record. It does not import RQ to decide whether source bytes match. The only mismatched map entry is `wepppy/nodb/mods/roads/roads.py`: stored current hash `25cbde5447e20110b52e3781a3046b4dda5bc026bc10f64fed68bba150a42201`, working-tree hash `bc58f90258044a34bf4614887276735f98256a8cfc5d7d868b68523d01d16978`.

Independent `git show` hash checks confirm the stored current hash matches all three committed revisions: starting `9231f2427`, checkpoint `b1054fac7` and installed migration `b5cac8166`. The uncommitted diff adds only the ten-line `Roads.query_inputs()` accessor. It copies/default-normalizes saved form parameters and returns existing form fields; no model preparation, execution, persistence or scientific formula changes occur in that diff. The unrelated template calls this accessor to avoid result-admission locking. The existing Roads repair note and real-lock rendering tests document that separate change. This review does not adopt it into the RQ implementation.

**Do not refresh the committed staleness hash in this package.** Such a refresh would bind the record to an unrelated uncommitted source change and make clean migration HEAD fail the same test. Do not change original execution provenance, published report, results, stale notice or test assertions. The scientific record must remain explicitly stale. Its owner can review and update the exact drift record alongside the eventual Roads source change; that is separate from RQ migration correctness.

An isolated rebuilt-runtime run of this publication test with the committed Roads source is valid attribution evidence. It proves only that publication check on the migration source, not a successful full clean-source suite. Completing the remaining working-tree collection, retaining the original failure, and reproducing it under 1.16.2 can establish absence of an RQ regression; they cannot turn the failed full command into a pass. To meet the user's literal all-required-checks-pass closeout, execute the full required suite against an isolated complete committed migration source snapshot, excluding all related dirty Roads source/template/test files together while preserving the shared working tree. Otherwise retain the explicit unrelated baseline failure and the package's broad gate as open. No production source or provenance file was modified by this reviewer.

## Independent review after daemon recovery — 2026-10-27 21:13 UTC

Reviewer: `final_correctness`, reviewer role. This is an independent reassessment
of the retained record after the earlier agent sessions were lost, not a claim
to have performed their historical actions. No new medium/high migration finding
was identified. Final correctness sign-off remains pending the isolated full
suite's terminal result.

Re-read the implementation diff from checkpoint `b1054fac7` to `b5cac8166`, with
particular attention to metadata publication and lost-acknowledgment recovery,
strict dependency promotion, stopped-parent tolerance, scheduler fork ownership,
status/timestamp consumers and the delivered dashboard patch. The promotion
helper watches the dependent hash, exact dependency membership, prerequisite
hashes and dependent sets before one transaction; cancellation, missing records,
unfinished siblings and strict failed prerequisites remain blocking. The stop
exception applies only to the exact identified stopped prerequisite of an
explicitly tolerant child. The scheduler change disconnects idle connections
without closing the in-use subscription connection.

Direct inspection of the installed local RQ 2.12.0 distribution confirms the
success/failure override signatures and scheduler defaults match this release;
`meta` remains positional index 11 after `self`. No unreleased execution argument
was added. The retained installed-distribution comparison changes only RQ and
adds croniter. The targeted logs independently read back 10 + 73 + 498 + 17
passes, and the separate lifecycle transcript records 13 passes. These are
selection totals, not a claimed deduplicated repository count.

The final acceptance receipts retain the destructive restore sentinel, normal
API retry, original/archived/restored content hashes, subsequent report retrieval
and RQ-free NFS reproduction. The earlier review's direct 417-file/25-Parquet
readback and the final acceptance ledger establish the bounded recovered output
claim. Metadata evidence has since expanded to 45 owned jobs, including 44 API
jobs and the bounded blocker; keep the distinction between all-job webhook
absence and API actor/correlation coverage. No broader NFS repair or reverse
Redis-state compatibility is inferred.

Independently recomputed each of the five entries in
`clean-full-suite-source.json`: every committed content hash matches `git show
b5cac8166:<path>`, every read-only overlay copy matches that hash, and every
preserved working copy still matches its pre-run hash. The only uncommitted
executable/source/test changes remain the three disclosed Roads paths; the two
additional overlays exclude their related docs. The isolated runtime record
matches image `88a982e44d316824f493c99d0c3a9a3db3e4800feef86ff2c65693677039162b`,
RQ 2.12.0, Redis 6.2.0, UID1000/GID993, group993 and umask0022. The canonical
Compose one-off runs the complete `pytest tests --maxfail=1` command with no
selection exclusions. At this review it has reached the Roads matrix without
failure; that is progress evidence only.

The original working-tree invocation remains **one failed, 6,810 passed,
61 skipped**. Its source-provenance failure must remain visible even if the
isolated migration-source run passes. The interrupted continuation's
`StopRequested` is attributed to the deliberately delivered SIGINT, not accepted
as a new application failure or counted as a passing full run. Do not amend the
Roads staleness record, claim the dirty working-tree command passed, or close the
full-regression gate before the isolated run completes.

## Final correctness sign-off — 2026-10-27

Reviewer: `final_correctness`, reviewer role. **PASS; no open medium/high
correctness findings.** Independently read the terminal
[isolated full-suite log](rebuilt-clean-full-pytest.log):
**11,948 passed, 226 skipped, 5,826 warnings in 3,304.46 seconds (55:04)**.
The log records 12,173 collected items plus one collection skip and the complete
`pytest tests --maxfail=1` command, with no test-selection exclusions. The
one-off container is gone after its configured automatic removal.

After completion, rechecked the exact image/runtime record and recomputed all
five committed, overlay and preserved-working-copy hashes. Each still agrees
with `clean-full-suite-source.json`; the executable diff outside committed
`b5cac8166` remains only the three disclosed unrelated Roads paths. The full
suite therefore validates the intended committed migration without adopting or
rewriting the user's unrelated dirty implementation. No additional production
source edit occurred after the reviewed implementation.

This passing complete run, together with the separately executed real Redis and
process selections, installed API/model/artifact acceptance, dashboard readback
and historical replay, satisfies the correctness evidence gate. Skipped broad
cases are not claimed to have executed; the explicitly enabled targeted
historical, metadata, batch/query, recovery/API and containment selection has
598 passes and zero skips, and the separate lifecycle suite has 13 passes.

Residual boundaries remain explicit: running 1.x jobs require drainage; mixed
workers and in-place downgrade of 2.x-written state are unsupported; isolated
original-state replay is not a live rollback authorization; the NFS log-descriptor
limitation needs its documented recovery when encountered; and the current dirty
working tree retains its independently attributed Roads provenance failure.
These limits do not represent an unresolved RQ migration finding. Final package
wording must preserve them and must distinguish the two full-suite invocations.
