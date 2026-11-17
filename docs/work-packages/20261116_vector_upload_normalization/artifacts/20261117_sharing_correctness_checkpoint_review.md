# Sharing contract correctness checkpoint review

Reviewer: independent `reviewer` agent `provenance_review`.  
Date: 2026-11-17 UTC.  
Base: `0ba4be47be17b9e717c1f970a816c2f5cf3a1386`.  
Verdict: **PASS for the contract checkpoint; implementation acceptance remains open.**

The review covers the draft canonical section “Sharing, copies, and existing
workspace resets” and `20261117_sharing_contract_decision.md`. Exact reviewed
SHA-256 values are respectively
`0030dff048a88d0b187f01ca547fc1f96ae3fe1a946415c4642d0eef03115f02` and
`dcad1e49b455dac4300abc432492da4b271d158fe74b715698345a12e47505b9`.
No production code was edited or tested during this checkpoint review.

## Correctness disposition

The operator explicitly accepts inherited records when the source owner makes
its project public or grants team access. The draft implements that decision as
a copy-boundary exception, preserves existing fork admission and destination
ownership, and rejects the proposed source-only/exclusion alternative. The former
High privacy finding `VUN-CORRECTNESS-RESUME-01` is **resolved by approved policy**;
it is not an exploit requiring an exclusion or extra approval under this amended
contract. Direct source download restrictions remain a distinct boundary.

The amended draft preserves original bytes, source SHA-256, upload actor, attempt
identity and source project identity. Additive `retention_actor` separates the
verified copying principal's storage charge from immutable upload provenance;
the existing unattributed bucket applies to legacy/automated callers without a
verified principal. This closes the security review's source-budget exhaustion
finding without changing thresholds or identities. A bounded copy-source
receipt/hash records inheritance. A copy is not a new upload, conversion or
successful validation event. Quarantined bytes remain uninterpreted evidence.
Existing fork/Batch metadata identifies the derived project without inventing a
new identity store or changing users, mounts or execution configuration.

Physical accounting remains necessary: a byte-preserving copy inside the managed
root consumes additional storage even though its receipt UUID is unchanged.
Counting by physical tree, preserving unrelated active reservations and enforcing
existing quotas before destination mutation correctly address the outstanding
Medium accounting finding. Automatic cleanup of generated content must preserve
the owning project's attempt roots; an explicitly selected whole-workspace reset
can retain its established removal behavior through the durable repair lifecycle.
No extra operator decision is required to implement those stated semantics.

The root boundary is coherent. Offline data-repository promotion/export outside
the configured run filesystem does not create bytes in that ledger and must not
silently change profile storage or identity. Reentry into a managed run/sandbox
is an admitted copy. An external snapshot's uploaded payloads remain data-only;
metadata/descriptor verification is sufficient and must not parse the originals.
The explicit known export call sites distinguish that boundary: absent retention
configuration cannot silently turn managed copying into an offline export.
Legacy projects with no retained evidence remain compatible, and reconciled
terminal `incomplete` records remain copyable evidence.

## Implementation acceptance conditions

- Count every physical retained tree, including duplicate attempt/reservation
  UUIDs, private archives, nested generated runs and deferred stale workspaces.
  Do not deduplicate charges by receipt identity.
- Preserve the receipt's originating `actor`, but charge new physical copies to
  the verified initiator using `retention_actor`. Existing receipts without the
  additive field retain their original accounting meaning. Test a second user
  copying the first user's public project without consuming the first user's
  budget, and repeated copies without unbounded provenance nesting.
- Apply global-before-project ownership, bounded inventory, pre-copy quota/free-
  space checks, dual repair obligations and exact post-copy/reset accounting to
  the confirmed consumers. Reconcile nonterminal/corrupt evidence before copying;
  permit terminal `incomplete` evidence without treating it as accepted output.
  Retain retry authority after partial copy/removal, fsync or lease failure.
- Preserve normal canonical inputs and ordinary public/team copy behavior. The
  inventory's earlier filter/refusal suggestions are superseded by this sharing
  decision; its consumer list remains the required failure-class coverage map.
- Keep external offline exports outside the run ledger, but verify managed
  reentry with old as well as newly created snapshots. No root, mount, identity,
  parser or deployment changes are implied.

No unresolved High or Medium **contract-design** finding remains. Commit this
reviewed checkpoint before the bounded accounting conformance changes. The
previous implementation accounting finding stays open until its consumer table,
fault tests and exact-byte/principal readback pass on the implementation successor.
Publication and deployment remain outside this checkpoint.

Re-review amendment: the first draft charged copied bytes to the originating
actor. The security review correctly identified cross-principal exhaustion;
the amended draft above supersedes that accounting recommendation. The PASS
verdict applies only to the amended digests recorded here.
