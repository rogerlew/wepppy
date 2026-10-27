# RQ 2.12 implementation security review

## Findings and current verdict

**Source and rebuilt forest security-boundary review: no actionable security regression found.**

- Code findings: high 0; medium 0; low 0.
- **Final security gate: PASS for this local migration package.** Rebuilt-runtime security tests, installed API/artifact acceptance, the complete isolated committed-source suite and independent correctness closure pass. The original dirty-working-tree invocation remains a separately retained failure, not a passing run.
- Reviewed installed candidate: WEPPpy `b5cac8166eaf067ac2ef79c440a82314c114111b`, dashboard `91f62b9c1d71918c9ecd173e2eea5e383d624687`. Later runtime-source edits require reassessment.

## Metadata and scope

Reviewer: independent `checkpoint_security` agent, `security_reviewer` role, 2026-10-27 UTC. Baseline checkpoint: `b1054fac7`; starting implementation: `9231f2427d33b64f971992ac969fd9420c49afd3`.

Reviewed upgrade diff after the checkpoint: dependency/Docker inputs; `auth_actor.py`; profile runtime; status/timestamp changes in job info/listings, Roads/AgFields/batch, Culvert manifest, run catalog, run-sync and WEPPcloudR consumers; pilot registry discovery and `wctl` RQ utility; new real Redis/process metadata, lifecycle and historical fixtures; operator documentation and existing ownership/containment probes. Unrelated Roads NoDb/template/render-test/docs edits and generated code-quality outputs are excluded. No code or runtime operation was performed by this reviewer.

Canonical authorities: the checkpoint's complete contract matrix in [contract decision](20261027_contract_decision.md), especially RQ response/disclosure, agent API/auth, directory maintenance ownership, NoDb persistence, batch task boundaries and query-catalog contracts. Scope remains a faithful behavior-preserving migration with no native webhook integration.

## Security triage and threat model

High security impact remains appropriate because the runtime interprets serialized jobs and supervises run-scoped processes. The existing Redis/job serializer trust boundary remains unchanged; this package does not claim safe execution of untrusted Redis payloads. HTTP callers must retain current scopes, run ownership and restricted-feature checks. Auth actor metadata is audit/context data and must not become a substitute for those checks.

Authorized operational scope is only local forest development. Existing identities, groups, mounts, queue topology and permissions must remain stable. Fault injection may target only uniquely owned test work. No live-state flush, destructive snapshot restoration, unrelated-job termination or remote rollout is authorized.

## Source assessment by surface

| Surface | Review evidence | Preliminary assessment |
| --- | --- | --- |
| Metadata publication | `auth_actor.py` and profile runtime now merge metadata before `enqueue_call`; position 11 matches both supported released signatures | Metadata joins RQ's transaction. Actor/correlation explicit precedence and profile replacement behavior are retained; no new best-effort post-publication hash write |
| Transaction and acknowledgment | New `test_rq212_metadata.py` reads real Redis at publication, tests commit/abort, lost acknowledgment, positional metadata and input immutability | Relevant direct boundaries are tested in source; final executed results required |
| Worker context | New real `WepppyRqWorker` subprocess test submits root, child and unrelated job | Covers actor/correlation/profile propagation and context isolation; final runtime result required |
| Cancellation authorization | Existing `job_routes.py` enforces scope/run and restricted-feature checks before mutation; fork/archive stop authority remains Admin/Root | No changed authorization logic found. Final actual API unauthorized/authorized cancellation evidence required |
| Process and directory locks | `rq_worker.py` and directory-lock implementation remain unchanged; existing real probe exercises detached writers and production worker-pool orchestration | No source weakening found. Exact RQ2 containment, retention-on-uncertainty and replacement results remain required |
| Serialization/disclosure | Changes normalize status enums and UTC timestamps; reserved catalog classifiers and sanitized result/error paths remain in place | No new deserialization entry point or public field exposure found; historical and protected-disclosure regressions required |
| Registry discovery | Pilot uses `StartedJobRegistry.get_job_ids(cleanup=False)` instead of treating execution members as job hashes | Avoids composite-ID confusion and does not introduce cleanup mutation into observation |
| Webhook exposure | Python producer/API search found no `webhooks` argument/configuration or generic request-to-enqueue keyword forwarding; submission recovery builds an explicit options dictionary | No application webhook activation found. Upstream defaults to empty job webhook list; runtime no-delivery proof remains mandatory |
| Webhook observation | Lifecycle test checks absent stored webhook configuration; subprocess audit hook records every TCP `socket.connect`, including failed delivery, and fails teardown on any record | Instrumentation exercises actual workers and descendants over Unix Redis. Must retain successful upgraded execution, not only test source |
| Supply chain | Exact `rq==2.12.0`, mandatory `croniter==6.0.0`; versioned wheel/sdist hashes in compatibility inventory; dashboard RQ pin replacement asserts expected sibling input | Minimal dependency intent is explicit. Dashboard Python floor repair is necessary; final resolved/build/runtime identity evidence required |
| Historical records | Frozen typed/base64 1.16.2 fixtures and real Redis/scheduler/worker replay; original-state rollback log | Evidence supports a bounded original-state replay, not mixed workers or an in-place downgrade of newer Redis state |
| Secrets/evidence | Inspected metadata keys and scanned retained artifact text for JWT, credential-bearing Redis/Postgres URI and private-key patterns | No matching secret pattern found in current retained artifacts. No claim of exhaustive secret detection |

The existing enqueue-recovery check still requires matching function, queue, args and kwargs before accepting a lost acknowledgment. New metadata publication avoids adding metadata after a caller-owned transaction has aborted. Explicit metadata precedence remains unchanged; there is no new trust in client-selected actor fields.

The new test harnesses select explicitly marked disposable Unix-socket Redis databases or spawn their own server. Historical replay refuses any preexisting DB4 key besides its marker. Lifecycle jobs use unique queue/job names, and worker teardown targets test-owned process groups. No Redis flush is present in the added tests.

## Validation reviewed so far

Historical evidence reports 2 tests passing under original 1.16.2, candidate 2.12.0 and restored original-state replay. The actual fixtures cover six readable lifecycle states and drained queued/deferred/scheduled execution. Running 1.x work must drain before cutover. These results do not validate 1.x execution against 2.x-written state.

The first candidate RQ-suite log records 5 failures, 1,094 passes and 134 skips. It is diagnostic evidence, not a release pass. Final targeted suites must replace that result with retained successful coverage and explain baseline-only failures. Fresh candidate/rebuilt-runtime logs were not yet available during this review.

No acceptance claim is drawn from old-runtime baseline results, dependency resolution, test source or import success.

## Final evidence required before sign-off

1. Exact RQ/version/image readback in every relevant running forest producer, worker, scheduler and observer; effective identity/groups/mounts/umask and original-job preservation evidence.
2. Executed real metadata publication/isolation, immediate/scheduled retry, failure, stop/timeout/crash/abandonment and pool replacement tests under the rebuilt candidate.
3. Existing real directory-lock and detached-writer probes, including retained locks when termination/ownership is uncertain, and actual API authorized cancellation plus unauthorized rejection.
4. Protected query-catalog disclosure, run-sync/fork/archive recovery, status/timestamp and historical-fixture results; no raw execution ID replacing an application ID.
5. Persisted webhook configuration checks and no TCP webhook delivery evidence from ordinary upgraded success/failure workflows. No endpoint or worker option enabling native webhooks.
6. Fresh actual API/auth multistage and fan-out/fan-in artifact readback/report retrieval, failed/resubmitted workflow evidence, and review of any changed final diff.
7. Required repository gates and independent correctness review with medium/high findings closed. Package/plan claims must match the achieved evidence boundary.

## Residual risks and sign-off

No release risk is accepted by this preliminary review. Original-state restoration remains limited to disposable proof; production was not upgraded and production rollout requires separate authorization. Native webhooks were not enabled by the reviewed source.

**Security reviewer**: `checkpoint_security`, preliminary review 2026-10-27. Final sign-off by `final_security` is recorded in the closure section below.

## Incremental review — worker repairs and dependency drift

Reviewed 2026-10-27 19:25 UTC. No new actionable security finding; final gate remains pending rebuilt-runtime and API/artifact evidence.

`WepppyRqWorker.handle_job_failure` captures whether the exact parent was stopped before the superclass clears that field. It invokes the existing release helper only for explicitly failure-tolerant dependents. The helper watches the deferred job hash, its dependency membership, every prerequisite hash and the dependent sets; refreshes the current job; requires exact stored/hash dependency-set agreement; and commits removal/enqueue together. The stopped-parent exception requires `allow_dependency_failures`, membership of the exact parent, and its current STOPPED state. Other prerequisites must be FINISHED or, only for tolerant jobs, FAILED. CANCELED, missing, active and other STOPPED prerequisites remain blocking. A canceled observer or repeated promotion cannot enqueue again. No filesystem lock is released by this transition.

This is bounded restoration of the batch contract's approved terminal observer, not permission for scientific consumers to execute on failed/stopped required outputs. The real baseline showed RQ 1.16 could also release a strict child after stop; the repair correctly preserves the canonical strict block instead of restoring that defect. The source-only property checks are supplemented by 64 candidate worker/dependency/WBT passes, 64 same-source baseline passes, 26 candidate batch-boundary passes and the independently repeated actual stopped-workhorse case in [worker compatibility evidence](worker_compatibility_repairs.md). Final installed-image reruns remain required.

The `project_rq` repair primes the same Redis version cache property from the queue before MULTI; it introduces no new transport, serializer, authority or fallback behavior. The extra four dependency pins retain the recorded running forest FastAPI, narwhals, pkginfo and python-dateutil versions after the first rebuild exposed unrelated resolver drift. This narrows, rather than broadens, the installed-distribution delta; final image comparison remains required. See [dependency drift evidence](dependency_runtime_drift.md).

The current sibling dashboard diff was also inspected: dependency IDs retain exact strings under 2.12; orphan started-record cleanup uses the public execution removal method, preserving the existing delete-enable decorator and registry scope. No authorization route/configuration change was found. The sibling source revision and full dashboard acceptance must be retained in final evidence; this preliminary observation is not a claim that its in-progress patch is complete.

## Incremental review — scheduler fork connection ownership

Reviewed 2026-10-27 19:33 UTC. The two new worker overrides disconnect only idle supervisor Redis connections immediately before the upstream startup/maintenance paths can fork a scheduler. No actionable security finding in this bounded repair; final takeover and installed-runtime results remain pending.

Direct inspection of pinned redis-py 6.2.0 `ConnectionPool.disconnect(inuse_connections=False)` confirms it acquires the pool lock and iterates only `_available_connections`. It does not close `_in_use_connections`, including the worker's live pub/sub subscription. Normal `get_connection()` reconnects an idle disconnected object before reuse. Released RQ 2.12 `RQScheduler` creates its own Redis pool; its lock acquisition and fork do not reopen the supervisor's pool between the override and fork. The maintenance path similarly invokes scheduler takeover through that separate pool before normal registry cleanup uses the worker connection.

The repair changes descriptor lifetime at an existing fork boundary. It does not alter Redis configuration, queue ownership, cancellation authorization, scheduler interval, maintenance interval, process identity, directory-lock release or containment policy. Failures are explicit rather than hidden behind a broad fallback. It addresses the retained deterministic finding that a scheduler can keep a killed supervisor's blocking dequeue socket alive; the earlier apparent 1.x/2.x distinction was disproved and is correctly documented as a baseline defect.

Final evidence must exercise both initial scheduler startup and maintenance takeover, followed by supervisor SIGKILL and successful processing without orphan dequeue. Existing real stop-command and detached-writer tests must still pass, including scheduler survival and lock retention on uncertain cleanup. Source inspection cannot substitute for those process/Redis results. The standard intermediate-queue failure/recovery test remains relevant for failures outside this repaired descriptor path, without promising a new recovery deadline.

## Installed forest evidence review — 2026-10-27 19:46 UTC

The final reviewed source is unchanged from implementation commit `b5cac8166`; its parent is accepted checkpoint `b1054fac7`. Dashboard source is committed at `91f62b9` and matches the retained patch. No post-acceptance runtime-source changes were present when checked. The unrelated Roads edits remain outside this review.

| Security obligation | Executed evidence | Result |
| --- | --- | --- |
| Exact runtime and identity | [Forest cutover](forest_cutover.md), [17-container readback](forest_runtime.json), [installed dependency delta](installed-dependency-delta.json) | All 17 import installed RQ 2.12.0. Main Redis stays 6.2.0; dashboard Redis stays 5.2.0. Existing identities/groups/umask/mounts retained. Main distribution delta is only RQ and croniter |
| Safe old-worker transition | [Drain record](cutover-drain.json), cutover stop/recreate logs | No raw started/intermediate members or registered workers after warm drainage; original images and private snapshot retained. No live Redis flush or volume deletion |
| Actor/correlation/profile isolation | [Installed metadata/historical log](rebuilt-historical-metadata.log), [targeted summary](rebuilt_targeted_validation.md), [39 live-job metadata records](acceptance_metadata_final.json) | 10 metadata/historical tests pass; all 39 inspected API graph/fork jobs have actor and correlation. Real worker test covers profile and unrelated-job isolation |
| Cancellation authorization | [Actual request/response receipts](acceptance_upgraded.json), [harness](acceptance_upgraded_harness.py) | Missing bearer 401; signed wrong-run service bearer 403; both leave job queued. Authorized 200 cancels before start, and same-target resubmission finishes |
| Stop/crash/retry/replacement | [Installed lifecycle log](rebuilt-lifecycle.log), [scheduler ownership evidence](worker_compatibility_repairs.md#scheduler-fork-and-worker-replacement) | All 13 lifecycle tests pass, including strict/tolerant dependency behavior, actual stop, timeout, SIGKILL, abandonment, scheduled retry and worker replacement |
| Directory/process containment | [Installed containment log](rebuilt-containment.log) | 17 passed, 0 skipped, 77.28 seconds. Includes actual detached writers and real Redis cancellation/ownership/crash paths, scheduler survival, and refusal to unlock under uncertainty |
| Recovery and protected disclosure | [Installed targeted summary](rebuilt_targeted_validation.md) | 498 existing worker/dependency/cancel/status/fork/archive/run-sync/ack/auth/startup tests plus 73 clean real-Redis query/batch tests pass with no skips |
| No native webhook activation | [Lifecycle audit](rebuilt-lifecycle.log), [live execution record](acceptance_live_execution_tracking.json), [metadata records](acceptance_metadata_final.json) | No attempted TCP delivery in instrumented worker scenarios; all 39 live inspected jobs have zero webhooks; production source exposes no webhook option |
| Execution-ID separation | [Live record](acceptance_live_execution_tracking.json) | Raw started member is composite; public discovery and worker current job retain exact plain application job ID |
| Valid project outcomes and observability | [Actual-project acceptance](acceptance_upgraded.md), [paired readback](acceptance_paired_comparison.json), [archive/restore](acceptance_archive_restore.json) | 155 consumed inputs byte-identical; 25 Parquets scientifically/schema equal; 3 HTTP CSV results equal; 417 generated files survive archive/download/restore byte-for-byte |
| Dashboard observer compatibility | [Installed dashboard record](dashboard-installed.json), [dashboard evidence](dashboard_compatibility.md) | Real installed job JSON and detail pages return 200 with exact dependency IDs; existing root identity retained. This proves loopback service behavior, not a new proxy-auth claim |
| Historical and rollback bounds | [Historical evidence](historical_compatibility.md), installed historical tests | Six original statuses readable; drained queued/deferred/scheduled work executes. Running old work must drain. Original-state rollback was proved only in disposable isolation |

The actual-project acceptance exercises an expected legacy-binary preparation failure, preserves diagnostics and strict blocked descendants, then uses the normal API to select the same supported binary as baseline and resubmit. No provenance bypass or source-project mutation is used. Noninterference is established for the bounded valid workflow and authorized recovery; malformed/unauthorized input retains rejection. Fresh report and archive retrieval prove the retained artifacts remain available through existing authorization.

Private snapshot verification by this reviewer: `.pytest_cache/rq212-private/precutover.rdb` is mode `0600`, parent directory `0700`, and gitignored. Its payload was not read or published. A renewed artifact scan found no JWT, credential-bearing Redis/Postgres URI or private-key marker; this is a bounded scan, not an exhaustive secret audit.

The broad-exception gate against `origin/master` passes with net delta -7. Stub and graph checks are retained in `rebuilt-stubtest-dependencies.log`, `rebuilt-stubtest-worker.log`, `rebuilt-check-test-stubs.log` and `rebuilt-rq-graph.log`. The required full-suite log is still active at this review timestamp. Final package closure remains pending that result and the independent correctness gate.

Production was not upgraded. Native webhooks were not enabled. Mixed-version workers, arbitrary historical IDs/import payloads and a live downgrade against 2.x-written Redis remain unsupported; these are explicitly excluded compatibility claims, not silently accepted data-loss risks.

## Independent resumed review — 2026-10-27 21:13 UTC

Reviewer: `final_security`, independent security-reviewer role after daemon
recovery. Findings: **high 0, medium 0, low 0**. No source or runtime operation
was performed by this reviewer. This phase independently rechecked the source
diff from `b1054fac7` to installed `b5cac8166`, the retained dashboard patch and
the executed evidence; it does not rely solely on the earlier verdict.

The metadata hooks publish actor/correlation/profile context in the original
enqueue transaction, preserve explicit actor/correlation precedence and avoid
post-abort metadata hashes. The ambiguous-acknowledgment recovery continues to
require matching function, queue and arguments; metadata does not authorize a
request. The unchanged cancellation route checks JWT scope, run access and every
restricted descendant before side effects. Actual receipts retain 401, 403 and
authorized 200 for the same queued job, followed by successful resubmission.

The stopped-parent release path watches prerequisite/dependent records and
requires the exact stopped parent plus explicit failure tolerance. Strict,
canceled, missing and unfinished prerequisite paths remain blocking. Scheduler
fork cleanup disconnects only idle Redis sockets, preserving the active pub/sub
connection. Directory-lock release and descendant ownership checks are not
weakened. The executed 17-case containment and 13-case lifecycle logs pass;
the 10-case metadata/historical log also passes. These include actual processes
and Redis, not only source assertions.

The final metadata receipt supersedes the earlier 39-job observation:
`acceptance_metadata_final.json` contains **45 terminal owned jobs**, of which
**44 API jobs have actor and correlation metadata**; the directly enqueued
sleep blocker has neither. All 45 stored `webhook_count` values are zero.
Production/API source search found no native webhook option or enqueue argument.
The lifecycle worker audit checks attempted TCP connections, including failed
attempts, and its executed teardown passes. This supports absence of native
webhook activity in the exercised workflows, without claiming a general egress
sandbox for arbitrary trusted Redis jobs.

The strengthened restore receipts prove the sentinel Parquet was absent both
after injection and before retry, then restored with identical original/ZIP
SHA256 and an authenticated HTTP 200 CSV response. Final readback covers all
417 archive file hashes, 25 Parquets and three reports. The NFS EBUSY event is
retained in [recovery evidence](acceptance_nfs_restore_recovery.md): unchanged
archive/NoDb/report code and an RQ-free FileHandler probe establish the existing
descriptor-lifetime mechanism. Exact owning processes were inspected before
graceful local web reload and idle API restart; worker pools and the running
pytest process were preserved. This bounded recovery is not a claim that the
underlying NFS lifecycle limitation was repaired.

Independent evidence hygiene checks found 17 recorded running containers all
on RQ 2.12.0, a 0600 private snapshot under a 0700 gitignored directory, and no
JWT, credential-bearing Redis/Postgres URI or private-key pattern in retained
artifact text. The snapshot payload was not read. All five preexisting dirty
tracked files still match their recorded working-copy hashes.

The original whole-suite invocation remains **failed**: 6,810 passed, 61 skipped
and one Roads publication-hash mismatch reproduced under original RQ 1.16.2.
Neither the user's accessor nor its reviewed-staleness record was changed to
silence it. A publication-only committed-source pass establishes attribution,
not whole-suite success. The separately recorded complete isolated run uses the
same rebuilt image/identity and read-only committed counterparts for all five
preexisting dirty files. It is still running at this review timestamp.

**Current security disposition:** all assessed security boundaries pass; no
unresolved medium/high finding or risk acceptance. **Final package security
sign-off remains HOLD for the complete isolated regression result and final
correctness closure.** Production remains unchanged, and native webhooks remain
disabled and unexposed.

## Final security closure — 2026-10-27 21:27 UTC

**Verdict: PASS. Open high/medium/low security findings: 0/0/0.** No risk
acceptance or security-policy exception is needed for the reviewed local
migration. This sign-off follows the independently finalized
[correctness PASS](20261027_correctness_review.md).

Independently inspected the terminal
[isolated full-suite log](rebuilt-clean-full-pytest.log): **11,948 passed,
226 skipped, 5,826 warnings in 3,304.46 seconds**. It collected 12,173 items plus
one collection-time skip and ran the complete `pytest tests --maxfail=1`
selection. The [recorded command/source overlays](clean-full-suite-source.json)
and [runtime identity](clean-full-suite-runtime.json) retain the exact rebuilt
image and all five committed counterparts used to isolate unrelated dirty
files. After completion, this reviewer recomputed all five preserved working
hashes: each remains unchanged. The only uncommitted executable/test/template
paths remain the three previously disclosed Roads paths; no post-review RQ
implementation change was found.

The skipped broad cases are not claimed as executed. The explicitly enabled
598-test installed targeted selection and separate 13-case real-worker lifecycle
suite supply the required no-skip boundary evidence, including metadata,
historical records, cancellation/process containment and no attempted webhook
delivery. Together with installed API authorization and generated-artifact
acceptance, they satisfy the assessed security obligations.

The original working-tree invocation still has one independently reproduced
Roads provenance failure after 6,810 passes and 61 skips; neither its assertion
nor its scientific staleness record was weakened. The NFS descriptor-lifetime
limitation remains documented, as do required 1.x drainage, unsupported mixed
workers and the prohibition on assuming safe downgrade of 2.x-written Redis
state. These are bounded compatibility/operational limits, not unresolved
migration security findings or authority to discard accepted work.

Approval covers this local forest work package and its reviewed source/evidence.
It does not authorize production deployment. **Production was not upgraded;
native RQ webhooks were not enabled or exposed.**

Final [health receipt](final_health.json) confirms web/API HTTP 200 and the
isolated suite container's exit code 0. The final worker readback shows no queued
or started work. [Disposable cleanup](disposable_cleanup.json) stopped only the
owned test Redis container, retained its bind data, left shared Redis running
and performed no flush or volume deletion.
