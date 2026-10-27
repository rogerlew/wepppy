# Query catalog refresh tracker

## Status

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
