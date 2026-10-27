# Upgrade forest to RQ 2.12.0 with preserved task behavior

Completed 2026-10-27: exact RQ 2.12.0 is installed across forest; API/model/artifact acceptance, complete isolated regression and independent reviews pass. Production unchanged; webhooks disabled.

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current.

## Purpose / Big Picture

Users must retain existing submission, status, dependency, cancellation, recovery and output behavior after moving from RQ 1.16.2 to exactly 2.12.0. Deliver a faithful migration wired into rebuilt local forest containers, with fresh generated model outputs and report retrieval. Scaffold-only work cannot close this package. Native webhooks remain disabled and unexposed.

## Progress

- [x] (2026-10-27 19:10 UTC) Read onboarding and standards; verified local forest Docker context and development preset.
- [x] (2026-10-27 19:10 UTC) Scaffold package and record unchanged behavior/small complexity budget.
- [x] (2026-10-27 19:12 UTC) Two independent checkpoint reviews passed; standalone ancestor `b1054fac7` committed.
- [x] (2026-10-27 19:24 UTC) M1 inventory/provenance, baseline 363+122+51 tests and actual API/model/report baseline retained.
- [x] M2: pin exact dependency and implement only evidenced compatibility repairs.
- [x] M3: direct Redis/process regressions, metadata and historical-state coverage.
- [x] M4: rebuild/recreate safe local services and complete API/artifact/rollback acceptance.
- [x] M5: required gates, independent review closure, durable docs and archive.

## Surprises & Discoveries

Released2.12 removes utcnow and Job.get_redis_server_version, returns status enums and string dependency IDs, and uses composite started entries. Status consumers include generated manifests, CLI, admin Jinja and external dashboard, not just API JSON. Actual stopped1.16 jobs released strict as well as tolerant children; preserve the canonical strict block while restoring only approved tolerant finalizers. Metadata post-enqueue writes raced actual Redis publication and leaked profile-only hashes before pipeline commit; regression-first repair joins the original transaction.

The first canonical build resolved four unrelated newer packages from loose inputs. Retain actual forest FastAPI0.143.1/narwhals2.27.1/pkginfo1.13/dateutil2.9.0.post0 through exact input pins, then rebuild. Original fixture binary lacked resolvable libgfortran; normal API selecting installed wepp_261026 produced a valid paired baseline without bypass.

The repository already has unrelated Roads edits. Preserve them and distinguish their baseline failures. Host resolves to forest; Docker context default points to unix:///var/run/docker.sock. Installed wctl selects development Compose. All 17 affected forest containers were rebuilt/recreated at 19:36–19:39 UTC; installed RQ is 2.12.0. Unrelated services and data were preserved.

## Decision Log

2026-10-27 19:10 UTC, operator/primary: exact 2.12.0 with unchanged application contracts; webhooks excluded. Limit complexity to dependency inputs/transitives, required fixes, tests and docs. User explicitly requires the ancestor revision, authorizing the checkpoint commit without branch change or push. Historical compatibility and rollback are evidence obligations, not assumptions.

## Outcomes & Retrospective

Implementation and forest cutover complete. Actual API acceptance passed the 18-node model graph, 155 byte-identical consumed inputs, 25 scientific Parquet comparisons, three CSV reports, ownership/cancellation/resubmission and archive/download/restore of 417 files. Installed targeted validation passed 598 tests plus 13 lifecycle cases without skips. Complete isolated committed-source regression passed 11,948 tests with 226 skips in 3,304.46 seconds. Correctness and security reviews closed with no open medium/high findings. The original working-tree run failed only on separately reproduced unrelated Roads provenance drift; no unrelated files or historical publication metadata were altered.

## Context and Orientation

Work from `/workdir/wepppy` (alias `/home/workdir/wepppy`). `docker/requirements-uv.txt` feeds the shared Python image. `wepppy/rq/rq_worker.py` subclasses RQ workers, while auth_actor and profile runtime wrap enqueue/context propagation. job_dependencies, cancel_job, project_rq, job_info and job_summary implement orchestration and presentation. rq-engine exposes actual authenticated submissions; Redis DB 9 stores RQ state. Query catalog, fork/archive and run-sync consumers recover persisted jobs. Read nearest AGENTS before editing each subtree.

Canonical contracts are rq-response, NoDb persistence/concurrency, scoped mutation cache guards and domain contracts identified in the compatibility inventory. Retain strict required-output prerequisites, explicitly approved failure-tolerant observers/finalizers, enqueue acknowledgment recovery, current IDs and API payloads. Do not change scientific parameterization or run schemas.

## Plan of Work

### M1 — baseline and compatibility

Inventory every pin/image/producer/worker/status/registry/stub and raw Redis assumption. Download the actual 2.12.0 distribution into temporary storage and inspect its versioned source/metadata, including execution IDs, statuses, timestamps, custom IDs, worker override signatures and croniter dependencies. Distinguish confirmed failures from test risks. Capture installed versions and safe configuration without secrets. Run existing targeted tests under 1.16.2. Select available bounded model fixture, clone using supported lifecycle, and establish actual API/model/report baseline before changing runtime. Capture six historical states: queued, deferred, scheduled, running, completed, failed. Do not promise unsupported transitions.

### M2 — exact dependency and minimal repair

Obtain two read-only checkpoint reviews and commit only package/current contract/index changes as an ancestor. Pin rq==2.12.0 in authoritative inputs; inspect repository generation tooling and regenerate derived inputs if any. Resolve the full pinned environment and justify only required transitive changes. Reproduce incompatibilities before fixes. Preserve all public behavior, queue names, identities, locks and serialization boundaries. Update durable operator/developer guidance alongside source. No broad fallback wrappers.

### M3 — direct regression evidence

Use unique package-owned queue/job names and isolated Redis where possible, actual worker subprocesses and existing test entry points. Cover success/result retention/strict release; strict failure and approved tolerant finalizers; deferred reconciliation, obsolete graph cancellation and duplicate-free resubmission; immediate/scheduled retries and attempt versus terminal failure; queued cancellation, running stop, timeout, killed workhorse and abandonment; descendant cleanup and refusal to unlock with live writers; actor/correlation/profile propagation and isolation; enqueue wrappers and ambiguous acknowledgments; started execution IDs, discovery/current job/status; aware timestamps and real producer IDs; worker-pool replacement/scheduler; query catalog, fork/archive and run-sync; all promised historical states; and absence of webhook activity. Record unsupported states with a safe preservation/drain procedure.

### M4 — forest cutover and acceptance

Read `scripts/deploy-production.sh` and deployment guidance before selecting canonical wctl commands. Inspect actual service image, identity, mount and queue configuration, active jobs and ownership. Preserve unrelated work; drain workers practically and never silently terminate unrelated jobs. Rebuild the dependency image and recreate all relevant producers/workers without deleting Redis state or volumes. Restarting the old image is insufficient. Verify rq.__version__ inside each running container and retain image/build identity. Repeat multistage and fan-out/fan-in API/auth workflows with installed pools. Exercise failure, cancel, retry/recovery, resubmit, live trees/status and report retrieval. Parse fresh consumed inputs and outputs against baseline; explain nondeterminism. Prove rollback in disposable isolation; never assume 1.x understands 2.x-written Redis. Leave healthy upgraded forest running unless acceptance requires recovery.

### M5 — gates and closeout

Run targeted tests, `wctl run-pytest tests --maxfail=1`, stub checks for changed surfaces, `wctl check-rq-graph`, broad exception enforcement, code quality observability, doc lint and diff checks. Frontend gates only for frontend edits. Update dependency catalog and inspect live trees if wiring changes. Independent correctness/security reviewers must inspect actual evidence and close medium/high findings. Promote durable constraints outside package, update tracker/package/root board/index and move completed plan to prompts/completed only after all acceptance gates pass.

## Concrete Steps

Run canonical commands from repository root. Initial observations: `hostname` = forest; `docker context show` = default; context endpoint = unix:///var/run/docker.sock; `wctl ps` shows running default/batch/fork-archive workers, rq-engine, scheduler and web services. Exact selected test/build/acceptance commands and their outputs will be retained in artifacts as inventory resolves them. Never print environment files, tokens or connection credentials.

## Validation and Acceptance

A passing import/install or mocked suite is insufficient. Close only with runtime 2.12.0 readback, fresh actual API-submitted generated inputs/output semantics, user-facing retrieval, required real process lifecycle evidence and resolved reviews. Unrelated baseline failures require retained before/after attribution; missing environment/project evidence leaves package open with precise blocker. Test IDs and resources must be uniquely attributable to this package.

## Idempotence and Recovery

Do not flush Redis, erase queues, delete volumes or unrelated run data. Record package-owned resources for bounded cleanup. No remote environment operations. Drain running 1.x work before cutover; queued/deferred/scheduled/terminal compatibility must be proven or preserved until handled safely. Mixed workers and rollback against newer state are unsupported until direct evidence says otherwise. Retain original image/build and prove old runtime against isolated original-state fixtures. Recovery must not discard newer accepted user work; preserve state and use forward repair when reverse compatibility is unproven.

## Artifacts and Notes

Store compatibility matrix, dependency provenance, baseline/post-change logs, environment record, job trees, generated content manifests and semantic summaries, historical-state/rollback evidence, contract reviews and final correctness/security review in this package's artifacts directory. Credentials remain outside evidence.

## Interfaces and Dependencies

Keep current application API and worker public signatures unless the released 2.12.0 distribution requires a specific repair. Do not port unreleased master/3.x execution-parameter signatures. RQ execution tracking changes Redis internals; inspect public APIs before interpreting raw started-registry members. Required croniter dependency tax and full pinned environment compatibility must be established before adoption.

Revision note: 2026-10-27 19:10 UTC — initial authorized execution plan; investigation and review precede implementation and cutover.

Revision note: 2026-10-27 19:24 UTC — record baseline completion, confirmed repairs and actual-runtime dependency drift; final environment gates remain open.

Revision note: 2026-10-27 — implementation `b5cac8166` and dashboard `91f62b9` installed; see artifacts/forest_cutover.md, rebuilt_targeted_validation.md and lifecycle_evidence.md. Scheduler inherited idle sockets reproduced on both versions and repaired without disconnecting active pubsub. Final full-suite/review gate remains open.

Revision note: 2026-10-27 — reviewer requested a destructive sentinel check on one disposable output to prove restore effect. The repeat restore failed before extraction with NFS EBUSY from web-worker-held run log descriptors after report reads. M4 is reopened until graceful owned-environment recovery and actual file restoration pass; full pytest remains running. No unrelated process or state may be discarded.

Revision note: 2026-10-27 — deleted-output restore now passes after documented graceful web reload and idle rq-engine restart closed stale log descriptors; the full pytest exec survived. An RQ-free FileHandler/NFS reproduction and unchanged archive/NoDb/report source establish an existing lifecycle limitation. Retain this limitation and recovery in durable operator guidance, without expanding the migration into a logging refactor.

Revision note: 2026-10-27 20:31 UTC — required working-tree full run stopped after 6,810 passes/61 skips on preexisting Roads source-provenance mismatch, reproduced under original RQ 1.16.2. Preserve unrelated uncommitted accessor and historical staleness record. Start complete isolated full suite using exact rebuilt image and all five committed counterparts mounted read-only. This avoids endorsing unrelated drift or claiming a failed invocation passed. A partial continuation was deliberately interrupted before isolation; retain its SIGINT/StopRequested receipt.

Retrospective observation: run inexpensive publication/source-hash guards before long scientific matrices when the starting tree is dirty. The existing Roads guard first surfaced after 46 minutes; early attribution would have selected committed-source isolation before that cost. This is a workflow lesson, not a new service, dependency or testing framework.

Revision note: 2026-10-27 21:28 UTC — complete isolated full suite passed (11,948 passed, 226 skipped), final review sign-offs retained, 17 installed runtimes healthy and 11 workers idle. Owned test container cleanup preserved shared Redis and all unrelated work. Durable contract and recovery guidance promoted; archive this completed plan.
