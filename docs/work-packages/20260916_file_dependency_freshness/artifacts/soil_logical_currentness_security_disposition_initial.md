# PF-R01 security and conformance disposition

**Recommend justified deferral of PF-R01; no runtime change approved.** The
confirmed medium false-stale limitation remains unresolved. This review supports
explicit acceptance of that narrow residual risk, subject to package-owner
acknowledgment; it does not mark the defect fixed or approve package closeout.
Reviewer: `freshness_security`; code base `36744f3b3` plus the reviewed working
tree. No runtime/test edits, new probes or named-project mutations were needed.

## Finding and retained evidence

PF-R01 embeds raw soil main/WAL/SHM and dependency metadata in accepted M3
equality. The [original review](postfire_remaining_freshness_review.md) retains
seven real SQLite cases: link, chmod, touch, byte-identical replacement, VACUUM,
committed-WAL checkpoint and unrelated-table insertion. Consumed schema and
typed logical hashes agree, yet accepted equality becomes stale. The strict
snapshot verifier rejects all seven as required during an active attempt.
The separate 300-change probe found no SQLite false-current collision; it is
bounded negative evidence, not a collision-immunity guarantee.

The [correctness proposal](soil_logical_currentness_correctness_proposal.md)
accurately distinguishes this limitation from new integrity defects. The
[QA record](soil_logical_identity_performance_qa.md) retains 21 actual snapshot
reads across three selected cases from 54 caches. Its JSON confirms all SQLite
connections targeted disposable copies, zero audit violations, identical source
states/bytes before and after, and equal repeated logical identities. Warmed
reads cost 46–209 ms and retain about 0.19–1.29 MB each. These measurements are
neither cold-storage/NFS acceptance nor full numerical M3 propagation.

Current `soil_snapshot.py` and `production_soils.py` SHA-256 values match the
benchmark record (`733325d3…` and `a0077e3a…`). Code inspection confirms inventory
still embeds raw dependencies and cache state; `_source_snapshots_current`
compares soil selections exactly. `verify_soil`, `verify_snapshot`,
`_current_authority` and locked strict artifact verification remain separate
guards. This disposition changes none of them.

## Why deferral preserves the authority boundary

[Production M3](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m3.md#runtime-and-compatibility-requirements)
requires bounded read-only preflight. The
[runtime contract](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m3_runtime.md)
requires fresh visible attempt-owned main/WAL copies for each logical read and
forbids connecting SQLite to the shared source. Real copy-side WAL/SHM creation
supports that distinction. Existing state reconciliation is not authority to
start a new scientific snapshot during a poll.

A process cache could reuse a previously proven physical-to-logical association.
It cannot establish the consumed rows of an unseen generation after checkpoint,
VACUUM, unrelated-table writes, eviction or process restart. Assigning an old
logical hash to that generation would introduce false-current behavior. Hashing
only main bytes would also omit committed WAL content. Retained accepted
manifests cannot supply historical proof for today's unknown source generation.

Keeping current behavior preserves journal rejection, no-follow bounded copies,
schema/type semantics, optional absence, source rechecks, publication guards,
and visible replay/failure records. The consequence remains conservative stale
status and potentially unnecessary rebuilds after harmless changes. It does not
grant a new permission, remove an integrity check or introduce a storage policy.

## Closeout interpretation and exact limit

The package's [complexity budget](../package.md#complexity-budget) expressly
allows a **justified unresolved inventory finding**. That permits an explicit
bounded deferral; it does not override the ExecPlan's statement that confirmed
in-scope failures block closeout or the medium/high review gates by implication.
The [security review template](../../../prompt_templates/security_review_template.md#findings)
specifies: “`Accepted-risk` requires security reviewer recommendation plus
explicit package owner acknowledgment in Sign-off.” This artifact supplies the
reviewer recommendation, not the owner acknowledgment.

Before closing the package, retain the owner's narrow acknowledgment and amend
the plan/decision log, tracker, inventory and final claims together: PF-R01 is
deferred with this evidence and existing behavior preserved; soil semantic
currentness is not a delivered fix. A linked follow-up must own the unresolved
policy decision. Until recorded, PF-R01 remains open for closeout. Do not relabel
it verified-safe, lower its severity merely to pass a gate, or silently apply this
exception to other findings. All changed-code security/correctness findings,
remaining consumer dispositions and mandatory runtime/archive/performance gates
retain their existing requirements. Other authorized package work can continue.

## Follow-up authority required

Any eventual correction needs a reviewed canonical M3 amendment defining when
fresh logical observations may be created, who initiates them, their visible
retention/archive lifecycle, bounded frequency/cost, process-cold behavior and
legacy accepted-proof rules. Changing read-only polling into an artifact-writing
workflow needs explicit operator authority for that behavior. An observability
exception needs approval of its exact records, reason and replacement evidence
under the [artifact standard](../../../standards/artifact-observability-standard.md).
Existing execution authorization is not permission to connect to shared SQLite,
checkpoint sources, drop failed copies or hide polling artifacts.

This review proposes no cache protocol, new datastore, service, watcher or native
reader. A future owned-reader evaluation would require separate committed-WAL,
schema/type, source-noninterference and retention evidence before changing the
current primitive. Collection/MUKEY, masks, THICK, policy and raster-closure
dependencies remain independent obligations. No approval of those open scopes
follows from this PF-R01 disposition.
