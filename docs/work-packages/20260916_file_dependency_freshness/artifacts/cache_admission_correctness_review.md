# Cache-admission amendment correctness review

Reviewer: independent `freshness_correctness`, 2026-09-17 UTC.
Reviewed `docs/adrs/20260917-file-digest-cache-admission.md`, the canonical
freshness contract's “Timestamp-quantum cache admission amendment,” and
`artifacts/cache_admission_amendment.md` before implementation of the guard.
Original ancestor: `43317704fd046faffac39e114634bb155213c547`.

**Checkpoint gate: PASS. Runtime/release gate remains HOLD.** The amendment
responds to a demonstrated defect and defines a bounded strategy whose residual
filesystem assumptions are explicit. It does not prove the implementation
already works; FWC-01 stays open until the revised code passes direct probes and
regressions. Commit this amendment and review disposition before implementing
the strategy.

## Evidence and scope

The retained `first_wave_ctime_collision_probe_nfs.json` extends the original
probe to disposable files under `/wc1/runs`. It reproduced stale hash-cache
reuse on container `/tmp` at iteration 1 and repository storage at iteration
192. The NFS path produced no full-identity collision in 1,000 attempts. This
absence does not prove NFS can never collide; it is the bounded observed result.
The mount is NFSv4.2 with ordinary close-to-open defaults (no `nocto`), soft RPC
failure behavior, and 32 KiB read/write sizes. No user project was changed.

The one-second **monotonic observation** interval avoids comparing client wall
time with server ctime. Under the stated requirement that filesystem version
quanta are no coarser than one second and metadata is coherent on open, waiting
before cache admission prevents a digest from becoming reusable within the
version's original timestamp quantum. Fresh hashing on the first eligible read
avoids admitting a digest computed while collisions were still possible.

This is a cache-admission threshold, not scientific parameterization. The ADR
nevertheless records the exact behavior change, one-second value, evidence,
decision ownership, alternatives and rollback risk. Rejecting immediate reuse
and retaining the original rapid-mutation probe are justified by real evidence.

## Required implementation precision

| Requirement | Correctness reason | Acceptance evidence required |
| --- | --- | --- |
| Hash every read before the observation interval expires | The same metadata key may still identify different bytes | Original real-clock rapid preserved-time rewrite probe, without sleeps or stat mocks |
| First mature read must freshly hash | An early digest may have become stale before the timestamp quantum ended | Deterministic clock branch test changes real file bytes while preserving the test version and checks the first admitted digest |
| Observation eviction must also prevent old digest resurrection | Two independent LRUs can diverge: an old digest may remain after its observation is evicted, then be reused when a new observation matures | Keep a digest entry alive while evicting/recreating its observation; verify fresh hashing after the new interval. Couple invalidation or include an observation-generation discriminator in the digest key |
| Preserve per-access read/path/descriptor checks | Age does not authorize a path, permissions or changed descriptor | Existing unreadable/symlink/replacement tests plus dedicated security review |
| Never cache a failed hash | A failed/mixed read cannot establish content identity | Mutation-during-read test followed by successful fresh read |
| Define mature/admitted warm measurements explicitly | During the guard, repeated hashing is intended; settled reads must meet the original zero-byte gate | Admit each measured file after the guard, then assert zero content reads on 100 unchanged state reads; include interleaved projects |

The proposed text states eviction restarts observation and uncached verification;
the implementation must enforce that for **both** cache populations. Merely
using the same nominal 512-entry size for independent LRUs does not establish
the required behavior. This is a design constraint, not a new abstraction request.

## Valid states and residual risks

Absent files, present-empty files, legacy source snapshots, ordinary same-byte
replacement, previous accepted results and failure artifacts retain first-wave
behavior. New or changed files may incur repeated cold hashing for one second;
the user should see accurate readiness/currentness rather than a fabricated
old digest. No sleep, acquisition or state rewrite is permitted in a status read.

The strategy does not repair stale NFS attributes, clock/version behavior beyond
the stated bound, disconnected filesystems or privileged restoration of the
complete identity tuple. The ADR explicitly excludes those guarantees. Keep
coherent-open and filesystem-granularity assumptions visible in the canonical
contract; do not claim that nanosecond-valued fields alone prove them.

One-shot probes cannot establish all NFS behavior. Final acceptance still needs
normal read/write/replace operations on disposable NFS runs, rebuilt/restarted
service identities, actual UI/RQ/WEPP currentness and archive/restore propagation.
Warm-state performance must be rerun after no-follow opening and admission-guard
changes; previously retained timings predate those changes.

No new project artifacts or exclusions are proposed, and rollback must not
remove the guard while retaining content-currentness backed by immediate cache
reuse. That would knowingly restore FWC-01. All other first-wave and repository-
wide findings remain tracked independently.
