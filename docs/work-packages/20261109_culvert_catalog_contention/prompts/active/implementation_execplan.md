# Restore parallel catalog and RedisPrep metadata writes

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Parallel culverts must finish ordinary metadata work without a sibling's catalog
publication causing failure. The existing batch-owner lifecycle guard protects
children from whole-tree replacement/deletion. RedisPrep setters take a short
serializer (a process-held file lock), then probe lifecycle ownership without
waiting, avoiding reverse-lock-order deadlock. Ordinary catalog writers bypass
that serializer and cause avoidable conflicts. Make them participate while
preserving genuine lifecycle conflict behavior and stale-wrapper fencing.

## Progress

- [x] 2026-11-09: Reproduced sibling contention and audited current contracts.
- [x] 2026-11-09: Independent design consultation identified the bounded repair.
- [x] Real-process regression reproduced exact EAGAIN before the patch.
- [x] Catalog critical sections and pilot receipt wrapper use the serializer.
- [x] 122 focused tests pass; independent review finds no correctness/security blocker.
- [x] 91 real-Redis pilot, worker and inventory peer tests pass.
- [x] Run broad sanity and fresh parallel forest payload/artifact acceptance; baseline failure disposition below.
- [x] Update tracker and operator/developer evidence before handoff.

## Surprises & Discoveries

The clone-identity replay recovered 33/33 only after three serial retries.
Its handler logged exception text without a traceback. A disposable managed-root
probe reproduced the same error in `RedisPrep.getInstance` while another process
held a sibling's lifecycle lock. Both use the batch owner. Historical holder
identity cannot be reconstructed. The existing serializer allows missing paths
for RedisPrep compatibility; catalog operations must retain strict path existence.

## Decision Log

Restore existing ordinary setter/publication coordination rather than changing
lock ownership or adding model retries. Applicable unchanged contracts are
`docs/schemas/redisprep-snapshot-contract.md` (participating setter serialization)
and `docs/schemas/query-engine-catalog-refresh-contract.md` (owner fencing).
Keep existing lockfiles/order and nonblocking lifecycle probes. Candidate collection remains outside locks; existing final inventory/schema
revalidation stays inside publication ownership. No locks across model execution; no scientific, schema, authorization or deployment
change. This is conformance work, not a new lifecycle protocol.

## Context and Orientation

`wepppy/query_engine/catalog_refresh.py` implements guards, incarnation identity,
receipts and publication. `wepppy/nodb/redis_prep.py` snapshots flat Redis metadata.
`tests/nodb/test_redis_prep_snapshots.py` uses disposable real Redis/processes;
`tests/query_engine/test_catalog_refresh.py` covers real files and lifecycle races.
`wepppy/rq/query_catalog_rq.py` has a pilot receipt wrapper that also bypasses the
serializer. Other outer guards protect actual lifecycle operations and stay.
Preserve the earlier uncommitted clone fix and unrelated user changes. No branch
creation or production deployment is included.

## Plan of Work

Pause an ordinary catalog critical section in one process and attempt a sibling
RedisPrep mutation in another. Prove kernel contention and correct durable bytes
after release. Cover initialization, publication, receipts, status, refresh
success/failure and fresh clone identity rotation. Keep destructive lifecycle
rejection, missing-directory refusal and nested lifecycle-owner reentrancy tests.

Then make the smallest serializer integration and audit outer callers. Retain
full tracebacks at the existing culvert failure boundary without changing its
response/status contract. Obtain independent correctness/security review of lock
order, reentrancy, absent/empty/legacy/populated state and stale writers.

Reload only the idle forest batch worker if required. Submit the unchanged
production ZIP through normal admission, check first-attempt parallel completion,
parse all outputs, and download/compare the normal archive. Preserve failed
attempts; serial recovery is not parallel acceptance.

## Concrete Steps and Acceptance

From `/home/workdir/wepppy`, run `wctl run-pytest
tests/nodb/test_redis_prep_snapshots.py tests/query_engine/test_catalog_refresh.py
tests/culverts/test_culverts_runner.py --maxfail=1`. New races fail before the patch
and pass afterward. Run `wctl run-pytest tests --maxfail=1`, recording the known
baseline template failure separately if encountered. Run scoped doc lint and
exception/stub checks where applicable.

Payload: `/tmp/culvert-catalog-regression-20261109/payload.zip`, SHA-256
`d679299ebcfd12cde4a20a6b14479d21ee63ce21bcd59435049678db5a74f392`.
Prior probes/validators are in that temporary directory; adapt batch IDs and
retain fresh evidence in this package. Credentials stay in private temporary
files. Verify normal forest worker identity, mounts, model inputs and outputs.

## Idempotence and Recovery

Use disposable test roots/Redis and fresh replay UUIDs. Never replace production
batches. Stop only task-owned diagnostics. Rollback reverts only this package's
source changes and reloads the idle forest worker; preserve earlier user work.
Never weaken pre-mutation lifecycle/stale-writer rejection to obtain success.

## Outcomes & Retrospective

Implementation passes 122 focused tests, including ten real-process sibling
races and seven deleted-directory refusal cases. Disposable Redis is required:
container-only execution initially skipped these tests, so a marked test-only
Unix socket was supplied and all cases executed. Independent review identified
no code blocker. Fresh parallel replay `dd79b0a7-9fb6-4ba2-97f2-7275fcbf0cd7`
(root `3771a02e-bf68-457f-bb24-ab5006299de5`) completed with 32/33 successful children. The remaining failure is a WhiteboxTools constructor settings JSONDecodeError. Broad sanity failed after 6,891 passing tests: HTTP catalog callers must wait through lifecycle contention; the first repair incorrectly made them fail immediately. Claims remain forest-only until separately
authorized production deployment and verification.


## Expanded acceptance: stateless WBT execution (2026-11-09)

Operator explicitly requests a generally robust stateless web-app design after
inspection showed every tool's working-directory options can rewrite shared
installation settings. Private binary copies are a verified workaround, rejected
as the general solution. This plan remains active for both repositories.

- [x] Restore catalog callers' historical waiting behavior without holding the
  serializer while waiting on lifecycle ownership; RedisPrep still fails on
  genuine lifecycle conflicts. Retry lock acquisition only, never operation bodies.
- [x] Implement WBT invocation-local configuration and eliminate wrapper cwd mutation.
- [x] Add deterministic concurrency and executable raster regression coverage.
- [x] Build/test WBT, retain prior dirty binary, install only on forest using the
  canonical WBT release runbook, and verify under normal worker identity.
- [x] Add an opt-in real batch regression test and rerun exact payload end-to-end.

WBT source is `/workdir/weppcloud-wbt`. Its only initial dirty file is
`WBT/whitebox_tools`; preserve that binary before any installation. Read its
AGENTS.md and docs/release-build-install.md. No branch changes or production
rollout. Runtime behavior authority is `docs/stateless-execution.md` in WBT.

Implement `Configs: Clone` and immutable process-local configuration in
`whitebox-common/src/configs/mod.rs`; tool/raster readers must use effective
invocation values, including existing WBT_MAX_PROCS precedence. In
`whitebox-tools-app/src/main.rs`, tool execution installs these values without
saving defaults. Explicit no-run configuration commands retain persistence with
atomic publication and explicit failures. All three Python wrappers must read stable
installation defaults, keep setters instance-local, forward all runtime options,
and pass subprocess cwd without changing the hosting process cwd. Preserve
process-tree cancellation, outputs, algorithms, and configured parameter values.

Use existing libraries only. Check caller expectations and configuration readers
across tools and raster code. Preserve malformed configuration as evidence and
fail explicitly; never use JSON retries or silent defaults for corrupt files.
Atomic explicit configuration writes prevent readers observing truncation;
concurrent administrative updates are not a new transactional settings API.

Validation: cargo check/test -p whitebox-tools-app; cargo test -p whitebox_common;
Python wrapper unittest discovery; real concurrent raster outputs through both
bindings; readonly/no-settings installation; malformed settings; unchanged
settings bytes and cwd; existing timeout/cancel containment tests. Build with
cargo build --locked -p whitebox-tools-app --release. Record source, Cargo.lock,
prior/built/installed binary hashes. Retain independent correctness/security
review. Run WEPPpy targeted races/HTTP tests and broad sanity. Final acceptance
requires fresh parallel 33/33 batch success without retries and all generated
artifacts plus authenticated download validated; RQ finalizer status is not enough.

Revision rationale: full-suite and real replay evidence disproved the first
repair's completeness. Scope now includes the confirmed WBT shared-settings race
and the operator-authorized general solution, retaining original acceptance.


## Current acceptance run (2026-11-09)

Installed and hash-verified main binary plus all 25 bundled plugins on forest,
after retaining the prior dirty binary and settings/plugins in
`/tmp/culvert-catalog-regression-20261109/wbt-before-stateless.tar.gz`.
Provenance: `wbt-release-provenance.json` in the same directory. Main SHA-256 is
`28208e075a51f37d254a51b2a9f27c0ef7e5f273344c8665a0749b4714766777`.
Normal batch worker identity: uid1000, gid993, groups993, umask0022. Discovery
passed after reloading the idle batch worker. No production host changed.

Current gates: 296 focused WEPPpy tests passed, one opt-in live skip; 207 Rust
unit/doc tests and 23 Python executable/binding tests passed; independent Linux
metadata and security review clear. Stub and broad-exception gates pass.

Live pytest now owns fresh batch `99ee4497-6214-44be-b9ff-519d3390b84f`, root job
`501e3f76-bd11-4352-aaf2-d0e7516c4c4e`; no retries allowed. Container evidence root:
`/tmp/culvert-stateless-acceptance-20261109`. Host logs `stateless-live.log` and
`stateless-full.log` are under the incident temporary directory. Both gates are
running; do not claim final acceptance until artifact and full-suite results
are recorded. Credentials remain private and must not be copied to documentation.


### Acceptance harness correction

Batch `99ee4497-6214-44be-b9ff-519d3390b84f` completed 33/33 without retries.
The new live pytest passed identity and model-artifact checks, then failed because
its `redis.Redis` connection was replaced by the repository autouse recorder.
Actual RQ root and all34 children/finalizer exist and finished. Corrected the gate
to use the existing real-integration convention `redis.StrictRedis`; added parent
status assertion and persisted identity evidence before final verification.

A fresh full automated gate now owns batch `733f8579-099c-4fff-bf9f-e41d9cb66416`,
root `71dc91d9-0c00-4bd6-a552-be8f2898faf9`, container evidence directory
`/tmp/culvert-stateless-acceptance2-20261109`, host log `stateless-live2.log`.
This is a fresh submission, not child retries. Broad sanity continues separately.

First clean replay comparison: all33 daily and event model-output tables match
the earlier successful replay exactly. Hillslope/channel IDs and areas match
when keyed by topaz_id; hillslope row order is not stable across runs. WBT settings
bytes remain identical to pre-installation. Read-only archive verification passed: authenticated browse/download HTTP 200,
2,137,377,679 bytes, and all 2,877 member hashes equal source files. Retained
evidence: `artifacts/first-archive-evidence.json` and
`artifacts/first-model-comparison.json` in this package.


### Parallelism assertion review

Independent review found that a single-worker stack could pass the live test.
Added actual child execution interval overlap assertion (excluding finalizer),
requiring peak concurrency >= 2 and retaining it in evidence. First replay peak
is 4; a serial/touching-interval probe is rejected. The second replay had already
loaded its test module, so execute this same new assertion separately against its
completed jobs and retain that supplemental result before handoff.


### Final live acceptance

Fresh batch `733f8579-099c-4fff-bf9f-e41d9cb66416` passed the live pytest in
1,943.10 seconds: 33/33 successful children, no failures/skips/retries, 34 unique
base/child identities, 2,364 hillslopes, 858 readable Parquet files, valid daily
and event outputs, all child/finalizer jobs finished, authenticated browse and
download, and all 2,877 archive members matching generated source files.
Archive SHA-256: `e76c3841e46edd573ccd81f09f288ca1d7f257c9ceceff0e9cd8e6b024bd9664`.
Retained `artifacts/second-live-evidence.json`; supplemental same-code assertion
confirms four overlapping child jobs in `artifacts/second-concurrency.json`.
Both clean replays left installation settings SHA-256 unchanged at
`9bf6d068f29a8b4607df86722ce4a2e10fbdb32ab21cb34ed800dc8dde5263bc`.


## Final disposition (2026-11-09)

Forest acceptance complete. Full sanity: 13,236 passed, 435 skipped, 15 passed
subtests; stopped at the known baseline failure
`tests/weppcloud/test_usersum_template_wiring.py::test_runs_template_uses_the_ttl_deletion_usersum_doc_id`
after 3,895.78 seconds. Both test and `templates/user/runs2.html` are unchanged;
HEAD already asserts `runsTtlDeletionHelpUrl` while the HEAD template lacks it.
The suite is not fully green, and maxfail=1 leaves the remaining tests unexecuted.
Focused real-Redis/HTTP/catalog/culvert checks: 296 passed, one opt-in live skip.
WBT: 207 Rust tests and 23 Python executable/binding tests passed. The separate
live gate passed, and both clean replays prove four overlapping child jobs.

Scope: forest batch-worker runtime reloaded and verified; other resident service
processes were not restarted. Production rollout/recovery and other-platform
validation are outside this completed task. Both repositories retain uncommitted
changes; the prior dirty WBT runtime is backed up. No model defaults changed.
