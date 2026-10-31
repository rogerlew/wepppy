# Make RedisPrep snapshots atomic and ordered

Work in `/home/workdir/wepppy`. Execute a comprehensive, bounded repair of this failure class:

> RedisPrep recovery snapshots must publish complete JSON atomically and must not regress because an older capture finishes after a newer one. Recovery must not expose partially restored metadata or overwrite newer live state through competing initialization/restoration.

This is an implementation task. Trace writers/readers and lifecycle variants, establish the contract, implement the smallest adequate correction, run deterministic concurrency and failure regressions, and retain evidence. Atomic rename alone is not a complete ordering fix.

## Baseline and preserved work

At prompt authoring, HEAD was `967627f4c` (`Recover reusable NoDb state after failed mutations`), following checkpoint `2b998e08d`. Record the actual starting branch, revision, and working-tree status. Preserve unrelated Roads, SSURGO, tracker, and research changes. Ignore dirty `wepppy/weppcloud/routes/usersum/generated/docs_index.json` as instructed. Do not create/switch branches, install dependencies, deploy, or submit production jobs.

Preserve landed corrections:

- WAM-01: WEPP admission before input mutation, continuous lifecycle/submission leases, receipts, batch/base saves, and webhook replay.
- MRS-01: reject malformed requests before business side effects while preserving valid empty/default requests.
- NFMS-01: failed high-level NoDb mutations recover or fence reusable memory while preserving committed disk state and low-level retry contracts.

Current authority lives in `docs/schemas/wepp-run-input-contract.md`, `docs/schemas/request-payload-contract.md`, `docs/schemas/nodb-persistence-concurrency-contract.md`, and relevant response/webhook/domain contracts. Completed work packages are historical evidence, not places to revise current governance. Create a new package for this repair.

## Starting evidence — verify against current source

`wepppy/nodb/redis_prep.py` currently:

- Uses a run-scoped Redis DB 0 hash as live metadata. The usual key is derived from the working-directory leaf; `.redisprep-run-id` provides a validated profile-fork namespace. Trace every supported namespace rather than assuming `runid == basename(wd)` everywhere.
- `dump()` captures `hgetall`, filters `locked:*`, and writes `redisprep.dump` with `open(..., 'w')` and `json.dump`.
- An interrupted write can leave truncated JSON. Concurrent snapshots can capture A then B but publish B then A. Atomic replacement addresses the first defect but not the second unless capture/publication are coordinated.
- `lazy_load()` checks `attrs:loaded`, reads JSON, restores fields one by one with `hset`, then sets `attrs:loaded=true`. Concurrent readers/loaders/writers and a snapshot already containing a loaded marker need careful analysis.
- `__init__` may set the loaded flag and dump when no snapshot exists. `getInstance()` constructs a fresh wrapper and invokes `lazy_load`; RedisPrep is not a `NoDbBase` singleton and must not blindly inherit its mutation machinery.
- Flag, timestamp, job ID, and archive receipt methods mutate Redis before dumping. Missing run directories currently cause `dump()` to return without writing. Preserve or explicitly resolve these semantics in the contract.

Confirmed related paths to inspect:

- `wepppy/rq/project_rq_fork.py::_rewrite_fork_redisprep_dump`: already writes a temp file, fsyncs, and atomically replaces a copied snapshot, with regular-file/no-symlink checks and destination-specific job-marker removal.
- `wepppy/rq/project_rq.py::_reset_forked_omni` and inherited-job-marker cleanup: direct hash deletion/field writes and snapshot rewriting.
- `wepppy/weppcloud/routes/weppcloudr.py`: direct receipt deletion followed by `prep.dump()`.
- `wepppy/nodb/mods/omni/omni_state_contrast_mixin.py`, archive/restore/skeletonize flows, profile namespace creation, and postfire report/preflight consumers.
- WEPP/RHEM submission and finalization, shared `submission_recovery`, and preflight/status consumers of the live hash.
- `tests/rq/test_project_rq_fork.py`: existing copied-snapshot preservation, namespace, and symlink tests.

These are starting points, not an exhaustive inventory. Establish current reproducible behavior; do not claim production corruption has been observed without evidence.

## Governance and scope

Read root and nearest `AGENTS.md` for touched subsystems, NoDb/tests guidance, work-package process, and `docs/prompt_templates/codex_exec_plans.md`. Use applicable `docs-maintainer` and `wepppy-tester` skills. Execute through a dedicated active ExecPlan and keep tracker/progress/decisions/discoveries/outcomes current.

Read applicable current contracts and:

- `docs/standards/contract-first-change-standard.md`
- `docs/standards/hardening-lifecycle-standard.md`, including failure-class assessment
- `docs/standards/artifact-observability-standard.md`
- `docs/standards/generated-artifact-validation-standard.md`
- `docs/schemas/nodb-persistence-concurrency-contract.md`
- `docs/schemas/rq-response-contract.md` and `docs/schemas/rq-webhook-contract.md`
- Current fork/archive/restore and run lifecycle contracts identified by nearest guidance.

The operator authorizes atomic and ordered RedisPrep snapshot publication and the necessary coherent recovery behavior across confirmed consumers. Follow required contract-first checkpoints and independent reviews. This prompt does not independently grant commit authority; prepare concrete authorized checkpoint work before asking for a genuinely missing ancestor-commit approval. Do not repeatedly ask permission for the bounded correction already requested.

Assess actual security/compatibility impact and produce required review artifacts. Do not change auth, privileges, runtime identity, file accessibility, scientific parameters, queue wiring, deployment topology, or unrelated Redis policy as incidental hardening. Do not introduce a new service/database/dependency or general distributed transaction framework.

## Required authority and consumer inventory

Retain a compact matrix for all relevant writers and readers, including direct Redis users and direct snapshot writers. Record:

- Run/namespace identity, physical path, alias/copy relationship, Redis DB/key, and lifetime.
- Fields owned by RedisPrep versus unrelated fields sharing the hash; persisted exclusions and authoritative live coordination state.
- Mutation, capture, publication, and restore order, current coordination, and failures.
- Normal, fresh, empty, legacy, partially restored, archived/forked, missing-directory, and concurrent lifecycle states.
- Actual consumers and observable consequence of stale job receipts, missing timestamps, resurrected deleted fields, or partial restore.
- Disposition (`confirmed defect`, `verified unaffected`, `unresolved`) and concrete test evidence.

State the source of truth explicitly for healthy live operation and for restoration after Redis loss. A recovery snapshot cannot reconstruct lost RQ job records merely because it contains job IDs; preserve missing-job reconciliation rather than inventing completion. Inspect run-hash fields used by NoDb, locks, lifecycle, preflight, and other components before proposing whole-hash deletion or replacement.

Repair every confirmed instance in this failure class within scope. Preserve intentional fork reset semantics; copied snapshots are not simply newer/older generations of the source run. Do not claim direct/out-of-band writers participate in a protocol until traced and covered.

## Contract and design requirements

Define guarantees and linearization points before implementation:

1. **Atomic file publication:** capture valid state, serialize, write a uniquely named temp file in the destination directory, flush/fsync as appropriate, then atomically replace. Readers see the complete prior or next snapshot. Clean failed temp files without deleting someone else's staging file or the last good snapshot.
2. **Ordering:** state exactly what “newer” means. After a newer participating capture is published, an older participating capture must never replace it. Coordinate capture and publication, not just the final rename. A per-process mutex cannot coordinate worker processes. Mtime alone is not an ordering token; Redis counters alone are insufficient without reset/restore semantics. Evaluate existing coordination before adding metadata or locks.
3. **Lease/fencing correctness:** if using expiring Redis leases, show how a paused writer that loses ownership cannot publish stale bytes after another writer finishes. A token check followed by an unprotected filesystem rename has a race. If using filesystem coordination, establish semantics on the actual supported local/shared/NFS mounts and across rename, fork, and restore. Do not silently assume a single host or local filesystem.
4. **Mutation coverage:** distinguish ordering of snapshots from atomicity of Redis mutation plus file persistence. Define the guarantee at successful method return and what happens if a process dies after Redis changes but before dump. Handle direct `hset`/`hdel` plus dump callers and multi-field operations. Do not advertise zero-loss cross-store commits or full transactions without implementing/proving them.
5. **Coherent restore:** validate a complete snapshot before changing live metadata. Serialize/conditionally publish restoration so readers/loaders cannot mistake a partial hash for loaded state, and a delayed restore cannot overwrite newer live changes. Include the loaded marker in the atomic visibility decision. Do not delete unrelated hash fields or reintroduce removed receipts/timestamps without an explicit restoration policy.
6. **Initialization:** define absent snapshot, empty valid object, absent/false loaded marker, existing live hash with missing snapshot, and cold-start concurrent constructors. Preserve intentional fresh-run/default behavior. Do not bootstrap a false “loaded” state on partial restore, fabricate defaults from malformed JSON, or create directories during late writes to deleted runs unless the existing contract requires it.
7. **Failure classification:** distinguish pre-publication failure, committed replacement followed by parent-directory fsync/cleanup failure, Redis mutation success with snapshot failure, restore transaction uncertainty, and coordination loss. Preserve observable errors and ownership-safe cleanup. Never silently bless corrupt snapshots, reset metadata to empty, or roll a committed snapshot back because a later mirror/cleanup step failed.
8. **Field safety:** retain legacy flat JSON and existing key/value meanings where feasible. Preserve `locked:*` exclusion and audit other live coordination fields before round-tripping them. Do not serialize tokens/lease ownership or restore obsolete ownership as active. Record and test field-specific compatibility changes rather than silently broadening exclusions.
9. **Namespace/lifecycle isolation:** coordinate by an identity that matches both Redis namespace and filesystem scope. Cover ordinary runs, profile forks, batch/pup/scenario contexts actually supported, archive/restore, and delete/recreate at the same path. Do not permit a delayed pre-delete writer to overwrite a new run incarnation. Preserve existing lifecycle ordering and avoid lock-order deadlocks with WAM-01 or fork/archive guards.
10. **Filesystem compatibility:** preserve required modes, ownership/access, umask behavior, and existing no-symlink protections. Atomic replacement changes inode identity and may change ownership; verify normal web/worker/archive readers under representative identities. Do not impose new path or permission restrictions on working workflows without authority.
11. **Recovery/retention:** keep the last valid published snapshot on precommit failure. Decide explicit behavior for already-corrupt legacy files; retain evidence and fail clearly if recovery is impossible. Do not invent an automatic salvage or backup retention scheme unless required by retained evidence. Normal project browse/archive/restore must retain the snapshot as intended; staging/coordination files are not replacement project records.
12. **Bounded cost:** measure common setter/dump and startup costs. Avoid repeated full scans, global cache resets, broad Redis key scans, unbounded retries, or locks held across model execution. Choose the smallest protocol that satisfies real cross-process requirements and document its operational/recovery cost.

Write a compatibility/regression plan before changing persisted JSON or Redis field/schema contracts. Prefer preserving readers without a new envelope; if metadata/versioning is truly needed, demonstrate why the simpler coordinated approach misses acceptance, and update all readers/writers, fork rewriting, restore, and legacy handling together.

## Required regression and integration evidence

Tests are authorized. Use canonical `wctl` tools, isolated disposable runs/Redis keys, real filesystem writes, and real Redis for claims about cross-process atomicity/order. Never flush shared Redis databases or remove unrelated locks. Use barriers/events and deterministic fault injection, not timing-only sleeps.

### Atomic publication and failure stages

- Repeated readers while publishing a large snapshot observe complete old/new JSON, never truncation or mixed content.
- Inject serialization, temp creation/write, short-write, fsync, and replace failures. Prior snapshot remains byte-valid and owned temp files are cleaned according to the contract.
- Interrupt/kill a disposable writer before publication and verify a fresh process can restore the previous snapshot. Show orphan temp files do not become authoritative.
- Inject post-replace directory-fsync/cleanup failure and verify honest committed-state classification; no automatic rollback to old bytes.
- Verify mode/umask/access behavior for first creation and replacement, plus existing symlink/non-regular-path protections where applicable.

### Ordering and mutation preservation

- Force writer A to capture older state and pause; writer B attempts/publishes newer state; resume A. The protocol must prevent stale final publication, either by preventing B's overlap or rejecting/refreshing A. Assert final bytes and restored semantics, not merely lock calls.
- Exercise two processes, not just threads. Include unrelated fields and deletes, especially job receipts and completion timestamps; latest applicable deletion must not be resurrected.
- Include direct Redis mutation plus dump consumers, multi-field resets, repeated rapid dumps, and simultaneous fresh constructors.
- Exercise coordination loss/timeout, paused owner, release failure, and ownership replacement. Old owners cannot publish or release replacement-owner locks. Check existing lock ordering under submission and archive/fork flows.
- Include a run deletion/recreation or supported lifecycle replacement interleaving so stale writers cannot contaminate the new incarnation.

### Restore and namespace safety

- Round-trip a real snapshot into an empty isolated hash; verify all allowed fields and excluded locks, field types, timestamps, and receipt identity.
- Race two loaders and a live writer; no partial loaded state, overwritten newer value, or resurrection of a deliberate deletion under the ratified policy.
- Simulate an interrupted legacy restore, including `attrs:loaded` already present in snapshot data. Verify the chosen repair does not treat a partial restore as complete.
- Test absent file/hash, populated hash with missing marker, valid `{}`, legacy files, malformed/truncated/non-object files, and unreadable paths. Corruption must remain observable and must not silently create usable empty state.
- Restore must not clear unrelated live coordination fields or overwrite active lock ownership. A snapshot job ID with missing RQ data must remain a recoverable missing-job case, not synthetic success.
- Test standard run and profile namespace separation, copied fork snapshot reset, archive/restore round-trip, and actual supported batch/pup variants. Prove source and destination isolation.

### Consumer consequences and previous repairs

- Exercise real RedisPrep setters/readers for task timestamps, `rq:*` receipts, archive IDs, and flags through representative WEPP and RHEM or another existing consumer.
- Validate that a successful submission's persisted receipt survives isolated RedisPrep metadata loss and is discoverable again without duplicate expensive execution; do not delete the RQ DB to simulate only metadata loss.
- Exercise fork marker stripping and direct receipt-removal consumers; preserved unrelated state and removed job markers must survive dump/reload.
- Verify preflight/status or a real existing consumer observes a coherent restored state, not just that the JSON parses.
- Re-run relevant WAM-01, MRS-01, and NFMS-01 regressions. Preserve early rejection, lease ordering, callback replay, clean NoDb state, and successful normal operations.

The generated artifact under review is `redisprep.dump`: parse its contents, restore it through the real normal reader, and inspect the downstream receipt/timestamp consumer. A full scientific model run is unnecessary unless this implementation actually changes scientific preparation/execution. Local unit tests do not prove production mount/identity parity; retain representative integration evidence and state any unavailable environment honestly.

## Execution and handoff

Run focused tests first, then required substantive-code full-suite and relevant static/stub/documentation gates. Queue graph/live-tree requirements apply if queue wiring changes; avoid unnecessary queue wiring changes. Do not expand testing indefinitely after required checks pass without new evidence. Record skipped/blocked tests and split-run results accurately.

Update canonical contract(s), proportional operator/developer documentation, active ExecPlan, and tracker. Retain diagnostics describing uncertain publication, corrupt restore, contention/lost ownership, and safe operator recovery without exposing secrets. Independent reviews must assess the ordering proof, restore races, namespace/lifecycle identity, modes/mounts, failure classification, and successful-path noninterference.

Final handoff:

- Root causes and exact atomicity/ordering/restore guarantees, including linearization points and explicit limits.
- Changed files and canonical contract sections with rationale.
- Consumer/state/failure coverage matrix and unresolved boundaries.
- Executed concurrency/fault-injection tests, actual restored consumer evidence, access/mount parity, and performance observations.
- Compatibility impact and preservation of WAM-01, MRS-01, NFMS-01, fork/archive semantics, and normal fresh-run behavior.

Do not claim atomic Redis-plus-filesystem transactions, recovery of lost RQ jobs, or full power-loss durability without evidence. Do not close with atomic rename alone while stale captures can still publish last or restoration can clobber newer live state.
