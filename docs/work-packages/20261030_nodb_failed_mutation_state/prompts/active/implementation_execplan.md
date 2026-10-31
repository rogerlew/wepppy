# Make failed NoDb mutations safe to reuse

This living plan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain
Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective.

## Purpose / Big Picture

After a mutation fails, later reads, successful edits and executable-input
preparation must not reuse its rejected state. A persisted A, rejected B and
unrelated accepted C must produce A+C, never B+C. Disk is authoritative, including
commits that occurred before a later error. Held controller identities remain
useful after recovery; when safe recovery fails they must explicitly refuse use.

## Progress

- [x] (2026-10-31 UTC) Read operator prompt, guidance and skills; verify HEAD and dirty tree.
- [x] (2026-10-31 UTC) Inspect shared boundary and manual/nested consumers; run existing 70-test boundary suite.
- [x] (2026-10-31 UTC) Reproduce held/cache contamination and later persistence with real serialization.
- [x] (2026-10-31 UTC) Draft canonical contract amendment, compatibility plan and consumer matrix.
- [x] (2026-10-31 02:23 UTC) Two independent contract reviews approved after medium findings resolved.
- [x] (2026-10-31 UTC) Operator authorized checkpoint commit; ancestor `2b998e08d` created before implementation edits.
- [x] (2026-10-31 UTC) Implemented shared recovery, manual/grouped and prelock producer repairs after ancestor.
- [x] (2026-10-31 UTC) Final 36-case actual-Redis matrix, real prepared inputs, resources and performance observations complete.
- [x] (2026-10-31 UTC) Focused/WAM/MRS/API gates and independent correctness/security/QA reviews pass.
- [x] (2026-10-31 UTC) Split broad gates complete: 12533 passed/371 skipped; disposable server removed and closeout documented.

## Surprises & Discoveries

The existing exception characterization only asserts unlock and no file creation;
all 70 base characterization tests pass while the discovery probe proves later
contamination. WEPP option-map helpers mutate aliases before acquiring a lock;
shared context recovery alone cannot close the class. Derived and Batch helpers
invalidate signatures, leaving held references unsafe. Atomic replace precedes
metadata and notification work, so an exception is not a no-commit signal.

Broad sweeps exposed the existing unknown-commit exception-class contract and two
outdated test doubles (separate TTL writer and filesystem-only cleanup). Restore
the exception wrapper for ordinary failures; preserve cancellation. Use detached
writer and explicit no-op fixture contexts respectively. Independent reviewers
approved these bounded compatibility fixes.

## Decision Log

2026-10-31 UTC, Codex: classify as normative extension; current contract does not
promise immediate held-reference safety. Respect the standalone ancestor gate.
Prefer coherent failure-only disk recovery over successful-path deep copies;
reserve enforced unusability for unsafe recovery, and stage prelock option edits.
Do not silently reinterpret manual direct-dump retries as aborted transactions.
No schema, auth, scientific or deployment changes.

## Outcomes & Retrospective

Implemented and focused locally validated; accepted prepared-file values, resource
lifecycle and performance tradeoffs demonstrated. Independent local code reviews
approve. Split broad coverage completed: 12533 passed/371 skipped, with compatibility
followups independently reviewed and affected paths rerun; no uninterrupted full
pass claimed. Closeout evidence and source hashes are retained. The checkpoint
was accepted and committed before implementation. No deployment or affected-run
recovery is authorized.

## Context and Orientation

Work in `/home/workdir/wepppy` on existing master; do not switch branches.
`wepppy/nodb/base.py` owns singleton loading, distributed Redis locks and atomic
jsonpickle files. A singleton is one shared Python object per controller/run.
A tracked signature is file mtime plus size, not proof that live memory is clean.
`locked` and `nodb_setter` mutate that object then persist. `dump` publishes by
atomic replacement, then runs additional work. Fresh hydration helpers and manual
producers listed in `artifacts/consumer_matrix.md` bypass parts of this boundary.
The user prompt is retained beside this plan and supplies the full required matrix.

## Milestone 1: ratify state and compatibility

Read `docs/schemas/nodb-persistence-concurrency-contract.md`, RQ scoped-cache
standard, WAM/MRS contracts and nearest domain instructions. Record all normative
deltas in `artifacts/20261030_contract_decision.md`, with compatibility and security
impact. Two independent read-only reviewers inspect authority, ownership, commits,
held references, failed recovery, direct retries and performance. Resolve findings.
Request commit authority only for the concrete reviewed checkpoint if still absent;
commit that checkpoint and contract amendments alone, record SHA in tracker.
Do not edit production implementation or conformance tests before that ancestor.

## Milestone 2: implement bounded recovery

First add failing real-persistence regressions for baseline A, failed scalar and
nested B, and unrelated C through both held and cached references. Implement the
NFMS-01 state machine at high-level acquired mutation boundaries in base.py.
Use existing coherent disk-read and legacy decode primitives, excluding cache
truth and logging allocation. Restore state in place under safe coordination;
prevent ordinary reads/mutations/dumps when recovery cannot be completed. Keep
runtime state out of jsonpickle. Preserve primary exceptions and annotate cleanup
failures without swallowing BaseException cancellation. Failed acquisition must
not alter another owner's token, memory or signature. Preserve direct dump retries.

Audit resources and subclasses before selecting restoration machinery. Do not
copy locks/clients or leak listeners; rebuild derived caches deliberately. Keep
expensive work off successful setters. For same-process interleavings, prove no
replacement-owner mutation can be overwritten or poisoned by a stale context;
capture each transaction's acquired token: `_ACTIVE_LOCK_TOKENS` is keyed by
controller identity, so a replacement acquisition on the same singleton can
overwrite its token. Exercise that exact interleaving. If coordination changes,
use unique disposable real Redis identities and test
lock ordering. Never touch unrelated run caches or locks.

Inspect and repair confirmed manual boundaries in the matrix, reading each nearest
AGENTS and canonical domain spec before edits. Grouped operations need per-file
commit classification. Preserve existing bounded compensation only with verified
ownership and generation; never overwrite another writer's generation. Shared
recovery must not initiate or duplicate compensation.
Stage WEPP phosphorus/baseflow options locally until valid. Audit nested aliases
and consumers that catch errors; reacquire options after recovery. Mark verified
unaffected paths with evidence and retain unresolved rows honestly.

## Milestone 3: validate consequences and compatibility

Construct real Soils and Wepp controllers using disposable fixtures from
`tests/microservices/test_wepp_admission_persistence.py`. Reach a failure after
mutation starts: missing gridded SSURGO after Soils assignments, or failed replace
after valid Wepp parsing. Perform an unrelated accepted edit, real `prep_soil`,
and parse the exact `wepp/runs/p101.sol` with `WeppSoilUtil` to prove accepted values.
For option-map consumers exercise a later raster failure and actual option input
writer readback. Retain paths, hashes and semantic values. Do not weaken MRS
validation or invoke production jobs/full model execution for this evidence.

Cover new/deleted attributes, option objects, lists/dicts, held controller references
and audited nested aliases. Fault inject domain, serialization, temp write/fsync,
replace, stale generation, token loss, postcommit metadata/notification/unlock/hook,
intermediate commit, missing/corrupt/unreadable recovery and Redis outage. Clear
external faults and demonstrate safe explicit recovery. Include first initialization,
optional absence, present-empty, populated, legacy, detached, readonly/ignore-lock,
Batch receipts, grouped updates and controlled concurrent readers/writers.

Measure Wepp/Soils representative successful setter timing against baseline; do
not substitute a dummy object. Count logging handlers/listeners or descriptors
across repeated failed recoveries and ensure processes exit. If mechanism changes
normative behavior, return to a reviewed checkpoint before implementing that delta.

## Concrete Steps and Validation

From the repo root, run focused new tests first, then:

    wctl run-pytest tests/nodb --maxfail=1
    wctl run-pytest tests/microservices/test_wepp_admission_persistence.py --maxfail=1
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20261030_nodb_failed_mutation_state
    wctl doc-lint --path docs/schemas/nodb-persistence-concurrency-contract.md
    git diff --check

Discover and run current grouped-update, Batch receipt, RQ cache-guard and MRS
regressions. If public stubs/API change, run applicable `wctl run-stubtest` and
`wctl check-test-stubs`. No queue wiring change is authorized. Follow test
instructions and isolation rules. Record exact counts, skips and blockers; split
runs are not an uninterrupted full pass. No full-suite run is needed for the
current docs-only checkpoint.

## Milestone 4: independent review and handoff

Obtain independent correctness, security and QA review of actual code and evidence.
Use repository review templates. Resolve medium/high findings with confirmation.
Update NoDb developer/operator guidance and user-facing recovery policy without
leaking internal exception details. Update this plan, tracker and project board.
Class-wide closure requires all confirmed consumers repaired and tested; unresolved
boundaries preclude an exhaustive claim. No deployment or affected-run repair
claim is authorized. Report exact contract section, rationale, coverage, prepared
input readback, resource/performance observations and gate limitations.

## Idempotence and Recovery

Use disposable runs and fault injection; clean only resources created by tests.
Preserve pre-existing roads work and ignored usersum index. Never restore old disk
snapshots as generic recovery. After first-create failure, a new initialization
object is required; optional absence remains valid. No automatic retry of a stale
mutation or unbounded recovery loop.

## Artifacts and Interfaces

Retain baseline probe/results, consumer matrix, decision, two contract reviews and
disposition, then final correctness/security/QA evidence under package artifacts.
Canonical NFMS-01 governs behavior; implementation helpers remain private unless
actual consumers require a reviewed public interface. No dependency additions.

Revision note (2026-10-31 UTC): initial plan records diagnosed defect, required
checkpoint authority, confirmed prelock aliases and unfinished implementation.

Revision note (2026-10-31 UTC): implementation and focused evidence complete after
ancestor 2b998e08d; review-found ownership, identity, delayed hydration and secondary
cancellation defects were corrected with retained regressions. Final broad coverage is partitioned into NoDb and its complement; earlier pre-final-source attempts were interrupted and are not passes.
