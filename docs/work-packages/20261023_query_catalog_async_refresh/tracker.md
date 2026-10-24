# Query catalog refresh tracker

## Status

Implementation and local validation complete; full-workflow acceptance blocked. Reviewed contract ancestor: `dc2b2ddbe8cfedbd4bae024310f03447ca813c32`; clarification checkpoint: `9435cd2cb`. Runtime changes are committed with this implementation checkpoint. M4/M6 remain open after the isolated model's terminal scientific failure. No production deployment or repair performed.

## Progress

- 2026-10-23 UTC: User authorized comprehensive async-preferred contract and delegated review.
- 2026-10-23 UTC: Three analysis agents completed 79-call/41-file writer and reader/lifecycle/queue inventories.
- 2026-10-23 UTC: Canonical draft and five cross-contract amendments prepared; independent reviewers raised eight findings, all dispositioned into revised design. Both reviewers confirmed closure at 2026-10-23 20:20 UTC.

## Decisions

- Preserve synchronous consumers until evidence supports an explicit migration.
- Reuse existing infrastructure; retain durable receipt-set acknowledgment beyond queue admission.

## Review and validation

Contract and implementation correctness/security/QA reviews and post-fix confirmations are retained; all blocking code findings are closed. Local failure/race, NFS, browser/archive and segmented regression evidence is complete. Full scientific acceptance failed; final disposition below.

## Remaining gates

Resolve and revalidate the isolated model's year-100 SOURCES3 date mismatch and duplicate raw WAT observations before claiming full workflow acceptance; causal baseline remains unproved. Production identity/mount/orchestration parity and fleet capacity remain rollout preflights. The paired native build includes explicitly recorded preexisting calendar/HBP edits. Deployment and affected-project repair remain separately authorized actions; release status is HOLD.

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
