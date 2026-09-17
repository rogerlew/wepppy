# PF-R01 security and conformance disposition

**PASS for justified deferral of PF-R01; no runtime change approved.** The
confirmed medium correctness/false-stale limitation remains unresolved. This is
an inventory disposition allowed by the package, not an `Accepted-risk` security
finding or a fixed defect. No new owner/human approval flow is required for this
bounded disposition. This scoped pass does not approve package closeout.
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
allows a **justified unresolved inventory finding**. The ExecPlan also says
confirmed in-scope correctness failures block closeout. Resolve these statements
through an explicit narrow scope disposition: PF-R01 remains in the inventory
and disclosed limitations, while its correction is deferred from this package's
implementation acceptance because it requires an unresolved canonical policy
decision. This uses existing package authority, not an implicit waiver of all
confirmed defects or mandatory gates.

The [security review template](../../../prompt_templates/security_review_template.md#findings)
requires owner acknowledgment for `Accepted-risk` security findings. That is not
the category here: no changed control, false-current acceptance, unauthorized
access or new artifact behavior is being accepted. The observed limitation is
preexisting conservative stale status; keeping its severity as medium does not
turn it into an attack-surface exception. Its appearance in a security discovery
inventory alone does not trigger a new approval flow.

Before closeout, amend the plan/decision log, tracker, inventory and final claims
together: PF-R01 is justified unresolved with this evidence and current guards
preserved; soil semantic currentness is not a delivered fix. Link follow-up
ownership of the unresolved policy decision. Do not relabel it verified-safe,
lower its severity to pass a gate, or silently apply this disposition to other
findings. Changed-code security/correctness findings, remaining consumer
dispositions and mandatory runtime/archive/performance gates retain their
existing requirements. No pending owner acknowledgment is imposed by this review.

The retained `soil_logical_currentness_security_disposition_initial.md` contains
the earlier draft's overbroad security-risk classification and acknowledgment
condition. This reviewed category clarification supersedes that condition;
the evidence and recommendation to preserve strict guards are unchanged.

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
