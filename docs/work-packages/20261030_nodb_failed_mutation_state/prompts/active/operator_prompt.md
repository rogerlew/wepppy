# Make failed NoDb mutations leave clean reusable in-memory state

Work in `/home/workdir/wepppy`. Execute a comprehensive, bounded repair of this failure class:

> A failed NoDb mutation must not leave rejected or uncommitted changes available to later reads, unrelated successful mutations, or generated-input preparation through a reused controller.

This is an implementation task. Investigate shared boundaries and confirmed consumers, establish the contract, implement the correction, validate with real persistence and representative consumers, and retain review evidence. Do not stop after a parser-only workaround or cache eviction that leaves previously returned controller references unsafe.

## Baseline and landed repairs

At prompt authoring, HEAD was `2f2bd0ef4` (`Reject malformed requests before business side effects`). Reverify current revision, branch, and working-tree status. The generated usersum docs index was dirty; ignore it as instructed. Preserve any additional pre-existing work. Do not change/create branches, install dependencies, deploy, or submit production jobs.

Preserve these completed corrections and their current canonical contracts:

- WAM-01: admission before proposed WEPP input mutation, including bootstrap/no-prep endpoints, continuous leases, batch/base configuration-only saves, and callback replay. Current authority: `docs/schemas/wepp-run-input-contract.md`.
- MRS-01: malformed requests rejected before business side effects while intentional empty/default requests remain valid. Current authority: `docs/schemas/request-payload-contract.md` plus applicable response/webhook/domain contracts.

Historical evidence lives in `docs/work-packages/20261030_wepp_admission_before_mutation/` and `docs/work-packages/20261030_malformed_request_side_effects/`. Do not reopen/amend completed packages. Create a separate package for this repair. Confirm claims against git and actual artifacts: a retained package sentence may predate the final implementation commit.

## Starting evidence — reverify and reproduce

In `wepppy/nodb/base.py`:

- `nodb_setter` delegates to `self.locked()`.
- `locked()` acquires the lock, yields the live object for mutation, and calls `dump_and_unlock()` on success. Exceptions in the body or persistence path release the owned lock and propagate, but do not restore live state.
- `getInstance()` returns the cached singleton when its tracked disk signature still matches. Failed mutations commonly leave disk unchanged, so ordinary signature checks do not detect dirty in-memory state.
- On actual signature drift, hydration updates the cached object's `__dict__` in place to preserve controller identity. Existing references therefore matter.
- `dump()` has a real commit boundary at atomic replacement, followed by signature/metadata/cache/notification work. An exception is not proof that nothing committed.
- `__getstate__` excludes logging objects and declared `TRANSIENT_FIELDS`; indiscriminate copying of `__dict__` is not an established safe snapshot mechanism.

The original review example was `Wepp.parse_inputs`: assign an early valid field, then fail on a later invalid option; the next same-process save could persist the rejected field. MRS-01 may now reject that HTTP payload before mutation. Do not weaken its validation or use an unreachable historical route as the sole reproduction. Establish a current reachable failure after mutation begins, such as a domain operation error or pre-commit serialization/filesystem failure, and exercise direct/internal callers as applicable.

Existing `tests/nodb/test_base_boundary_characterization.py::test_locked_releases_lock_and_does_not_persist_on_exception` verifies unlock and absence of a disk write, not clean memory or later reuse. Inspect its current version and all newer tests before designing coverage.

An existing precedent is the `Batch job receipt compatibility mirror` section of `docs/schemas/nodb-persistence-concurrency-contract.md`: failed acquisition must not alter an owner's mutation signature; an acquired failed transaction invalidates only its own instance signature for next-read hydration; never clear global caches. Inspect `BatchRunner.set_rq_job_id_fresh` and its tests. This precedent is useful but does not automatically establish safety for held references, nested mutable values, or all mutation paths.

## Governance and scope

Read root and nearest `AGENTS.md`, including NoDb and tests; read guidance for route/RQ/controller domains actually touched. Apply relevant `docs-maintainer` and `wepppy-tester` skills.

This shared persistence repair requires a dedicated work package and active ExecPlan. Read `docs/prompt_templates/codex_exec_plans.md` and the work-package process; identify the plan and keep progress, discoveries, decisions, outcomes, and tracker current.

Read:

- `docs/schemas/nodb-persistence-concurrency-contract.md`
- `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`
- `docs/standards/contract-first-change-standard.md`
- `docs/standards/hardening-lifecycle-standard.md`, especially failure-class assessment
- `docs/standards/generated-artifact-validation-standard.md`
- Current WAM-01/MRS-01 contracts and relevant domain contracts.

The operator authorizes this bounded consistency outcome and equivalent confirmed consumers. Classify existing-contract conformance versus a normative behavior change. Follow required checkpoint sequencing and independent reviews. This prompt does not independently grant commit authority: prepare concrete authorized checkpoint work before asking for any genuinely missing ancestor-commit authority. Do not ask again for permission to pursue the outcome already requested, and do not manufacture an exemption from the contract-first gate.

Assess security and compatibility impact from the actual persistence/ownership changes and retain required review artifacts. Obtain independent contract and final reviews as required by the repository process. Do not change scientific defaults, schemas, authentication, permissions, deployment identity, queue topology, or lock TTL policy as incidental cleanup.

## Required discovery and consumer matrix

State the broken assumption: disk non-persistence and lock release do not imply that a shared mutable object reverted its failed changes.

Inventory real mutation boundaries, following wrappers and collaborators:

- `NoDbBase.locked`, `nodb_setter`, `dump_and_unlock`, direct `dump`, and manual lock/mutate/dump/unlock paths.
- Controllers/parsers that mutate nested dictionaries, lists, option objects, caches, or derived fields before raising.
- Multi-controller grouped updates and existing rollback/snapshot mechanisms, including WEPP/Soils/Watershed grouped payload updates.
- Fresh-hydration mutation helpers, BatchRunner receipts, RQ scoped cache guards, detached controllers, initialization, readonly/ignore-lock readers, and signature refresh paths.
- Existing callers that explicitly retry a failed direct `dump()` on the same object, versus failed high-level mutations that must discard proposed state.
- Request/worker consumers that catch a mutation error and continue or perform a later save in the same process.

Record boundary/caller, controller identity, durable file, exception/commit stage, lock owner, reference lifetime, existing recovery, test evidence, and disposition (`confirmed defect`, `verified unaffected`, `unresolved`). Inspect at least two real controller consumers and both decorator/context and manual mutation patterns before generalizing. Search subclasses/overrides and implicit setters, not just same-name calls.

Repair every confirmed instance within this failure class, with explicit unresolved boundaries when unavailable evidence or different authority blocks closure. Do not assume all instances are covered merely because the base context manager changed. Conversely, do not mechanically rewrite every controller when shared behavior safely covers it.

## Contract and design requirements

Specify the state machine and recovery behavior before implementation. Preserve atomic persistence, disk authority, coherent bytes/signatures, stale-write rejection, owner-token release, current singleton identity expectations, and legacy hydration behavior.

1. **Acquire failure:** if lock acquisition fails, this caller has no mutation ownership. It must not restore, clear, invalidate, or replace an object/signature being used by the legitimate owner, and must not unlock another token.
2. **Acquired, pre-commit failure:** discarded changes must not reappear through `getInstance`, a held controller reference, an unrelated setter, or subsequent artifact preparation. Establish a clean durable-state base or explicitly make the affected instance unusable until safe recovery. An unchanged disk signature is not sufficient evidence of clean memory.
3. **Durable authority and concurrent writers:** recover from an authoritative version under appropriate coordination. Do not restore an old entry snapshot over a newer committed generation, stamp dirty memory with a fresh disk signature, or silently merge whole objects. Preserve `NoDbStaleWriteError` behavior and reapply-from-fresh-state requirements.
4. **Commit-aware failures:** after atomic replacement succeeds, memory must reflect the committed state or require explicit authoritative refresh. Never rewrite old disk state or restore pre-mutation memory merely because unlock, validation, post-dump hooks, version metadata, mirror updates, or notification fails. Preserve existing warning/best-effort classifications and honest commit outcomes.
5. **Recovery failure:** missing/corrupt/unreadable durable data, Redis failure, decoding failure, or lost ownership cannot authorize dirty reuse. Preserve the primary operation failure and observable cleanup/recovery context without silently masking either. Do not add unbounded retry loops or depend on cache availability for recovery truth.
6. **References and nested state:** top-level cache eviction alone does not repair references already handed out. Shallow copies do not undo nested mutations. Specify handling of controller identity and aliases to mutable nested values; audit actual consumers retaining those aliases. Do not promise transparent repair of arbitrary external Python references that the implementation cannot enforce.
7. **Resource lifecycle:** preserve or correctly rebuild logger handlers/listeners, transient fields, collaborators, and derived caches. Avoid duplicating threads/handlers, leaking descriptors, or copying locks/Redis clients. Do not persist new runtime-only recovery metadata accidentally through jsonpickle.
8. **Initial/optional/readonly state:** define behavior for a controller without a prior file, absent optional controller, detached object, readonly/ignore-lock paths, and supported legacy payloads. Do not convert a valid initialization failure into an unrelated missing-file error or invent a partial authoritative record.
9. **Direct persistence and retries:** distinguish the public low-level `dump()` retry contract from high-level aborted mutations. Existing replace-failure tests may deliberately retry the same payload. Preserve valid explicit retries or obtain/document a narrowly justified contract change; do not accidentally erase intended data on every low-level I/O error.
10. **Composite operations:** determine whether a failure happened before any commit, after one controller committed, or after an explicit intermediate dump. Clean memory must match the appropriate durable state. This task does not grant distributed rollback across multiple files or rollback of already-published artifacts/external actions.
11. **Exception classes:** assess cancellation, `BaseException` subclasses, and cleanup during unwinding. Use narrow handlers except deliberate minimal cleanup boundaries with documented rationale. Do not claim recovery from SIGKILL/process death in memory, and do not swallow cancellation/system-exit signals.
12. **Performance:** choose the smallest adequate existing mechanism. Do not add serialization/deep-copy/disk-reload work to every successful setter without measuring representative controller costs and explaining necessity. Keep expensive recovery off healthy paths where feasible; no new dependency, service, datastore, or generic transaction framework.

Evaluate eager in-place restoration, explicit invalidation plus enforced refresh, and existing controller-local staging as implementation options, not predetermined requirements. Select on demonstrated correctness for actual consumers and ownership boundaries. Do not combine multiple redundant mechanisms without evidence.

## Required regression matrix

Tests are authorized. Use canonical `wctl` commands and real `.nodb` serialization/filesystem state. Fault injection is appropriate at named boundaries; mocks that bypass the changed persistence/hydration mechanism are not proof.

### Core state and references

- Persist baseline A; mutate scalar and nested state to B; raise inside `locked()`; verify clean memory through both the original reference and repeated `getInstance`, and disk still A. Perform an unrelated successful update C; verify B does not appear in the new disk record.
- Repeat through `nodb_setter` and a confirmed manual mutation path, plus at least two real controllers. Include newly added/deleted attributes, list/dict changes, and an option object rather than only an integer dummy field.
- Retain two references to the same singleton and, where actual consumers do so, nested-state aliases. Verify the ratified supported-reference behavior.
- Successful mutations, sparse/default/legacy reads, and serialization round trips retain existing behavior and identity expectations.

### Failure stage and authority

- Lock busy/acquisition failure: another owner's live mutation and token/signature remain untouched.
- Domain exception, serialization failure, temp write/fsync failure, and failed `os.replace`: no rejected mutation leaks into later reads/saves; partial temp files are cleaned as contracted.
- Stale-write rejection after another writer commits: recovery retains the newer durable generation and never redumps B.
- Ownership lost/TTL expired: no release or rollback of a replacement owner's work.
- Atomic replace committed, then post-commit failure: no rollback of committed bytes and no stale pre-commit memory advertised as current. Include existing parent-directory fsync warning semantics, mirror failures, unlock and post-dump hook failures as applicable.
- Exception after an explicit intermediate commit: preserve that committed generation; do not assume the entire context was uncommitted.
- Recovery itself fails on absent/malformed/unreadable data or Redis outage: original failure remains diagnosable and dirty state cannot be silently reused or later persisted. Demonstrate safe subsequent recovery when the external fault clears.
- Direct `dump()` failure/retry retains the ratified low-level contract, including signature behavior.

### Compatibility and concurrency

- First initialization with no durable file, optional absence, detached, readonly/ignore-lock and legacy controllers.
- Existing grouped update rollback and BatchRunner fresh-receipt helper interoperate with shared recovery; no double rollback or owner-signature corruption.
- Controlled competing readers/writers and same-process references around failure/refresh; ensure any new in-process locking introduces no lock-order deadlock or owner interference. Include real Redis coordination if the lock boundary changes, isolated to unique disposable run IDs.
- Logging/transient-cache cleanup remains correct; repeated failures do not grow listeners/file descriptors, and test processes exit cleanly.
- Representative performance comparison for any new healthy-path overhead; do not use a tiny dummy object as the sole cost evidence.

### Real consumer consequence

Choose a currently reachable WEPP or other model-controller mutation failure after a field changes, using a disposable fixture and preserving MRS-01 validation. After failure, carry out an unrelated valid edit and real preparation. Parse the exact generated file under `wepp/runs/` (or the corresponding model consumer path) and prove it contains accepted values, not rejected B. Reloaded NoDb state alone is insufficient for the downstream consequence. Avoid a full model run if generated executable-input readback establishes this boundary.

Re-run relevant WAM-01/MRS-01 integration regressions so clean-memory recovery does not weaken early rejection, default/false handling, no-prep prepared-file preservation, leases, or replay. Do not recreate a malformed request leak just to exercise the new recovery path.

## Validation, review, and closure

Starting test sources include `tests/nodb/test_base_boundary_characterization.py`, base unit/misc tests, controller parsing and grouped-update tests, BatchRunner receipt tests, RQ mutation guards, and `tests/microservices/test_wepp_admission_persistence.py`. Discover current paths and read nearest test instructions. Expand fixtures carefully without polluting global module/class caches.

Run focused tests first, then required NoDb and substantive-code full-suite gates. Run stub/API checks for changed public surfaces and stubs, changed-exception checks, relevant documentation lint, and other applicable repository gates. Explain blocked tests and split-run evidence honestly; do not report an uninterrupted full pass unless one occurred. Do not mutate caches/locks for unrelated jobs to clear test failures.

Retain a compatibility/regression plan before any persistence-contract/schema edits. Prefer no on-disk schema change; any proposed addition requires explicit justification and serialization/legacy-reader evidence. Keep current canonical documentation and proportionate user/operator/developer documentation aligned, with rationale and precise non-goals.

Obtain required independent correctness/security/QA review for the actual change scope, resolving findings before closure. Reviews must inspect commit-stage classification, held references, lock ownership, recovery-failure behavior, direct-dump retries, and successful-path cost; happy-path tests alone are insufficient.

Final handoff must state:

- Root cause and the exact failed-mutation/commit-state guarantee now enforced.
- Files and canonical contract sections changed, with decision rationale.
- Consumer/failure-stage coverage matrix and unresolved cases.
- Executed tests, real persisted and prepared-input evidence, performance/resource observations, and gate limitations.
- Preservation of WAM-01, MRS-01, stale-write/atomic-write behavior, valid retries, and supported legacy workflows.

Do not claim full transaction rollback, process-crash recovery, or arbitrary external-reference repair. Close the specific contamination-of-reused-NoDb-state class across confirmed consumers, without redesigning the persistence architecture.
