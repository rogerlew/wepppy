# Sharing and copy accounting security checkpoint

Date: 2026-11-17. Independent reviewer: `frozen_security`.
Starting source: `0ba4be47b`.
Reviewed canonical draft SHA-256:
`0030dff048a88d0b187f01ca547fc1f96ae3fe1a946415c4642d0eef03115f02`.
Reviewed decision artifact SHA-256:
`dcad1e49b455dac4300abc432492da4b271d158fe74b715698345a12e47505b9`.
No production code was changed by this review.

**PASS for the amended contract checkpoint. No unresolved High or Medium
design finding remains.** Accounting implementation and runtime acceptance remain
open; this disposition permits that implementation against the reviewed contract.

## Policy disposition

**SEC-RESUME-01 is resolved by explicit operator-approved policy.** The operator
accepted that public sharing or team membership permits the existing authorized
fork/copy workflow to inherit originals, rejected attempts, receipts and private
archives. The canonical exception preserves those bytes and destination ownership
without adding approval or filtering. Direct source browse/download restrictions
and inert handling remain unchanged. This review does not reopen that choice.

## Accounting checkpoint disposition

**COPY-ACCOUNTING-01: closed in the amended contract.** The initial draft charged
copied bytes to the original upload actor, permitting a public copier to consume
another principal's upload allowance. The revised contract preserves immutable
original `actor`, source hash and attempt identity while attributing incremental
storage through additive `retention_actor` to the verified copying principal.
Automated/legacy calls without a verified principal use the existing unattributed
bucket. Bounded copy-source receipt/hash ancestry retains the original event's
provenance without claiming a new upload or conversion.

This separates source attribution from storage responsibility and closes the
reported cross-principal quota design flaw. No new authorization gate or copy
filter is needed. Implementation must source `retention_actor` from verified
request/job authority, never client-provided receipt fields, and reconciliation
must honor that attribution consistently while preserving legacy receipt behavior.

## Accepted controls and required evidence

The proposed global-before-project fence, source/destination scopes, terminal
receipt measurements, existing quota/free-space ceilings, durable operation
identity and exact-root rebuild are appropriate reuse of the current mechanism.
They must include the copied/reset subtree's independently writable child scopes
where applicable and measure retained stale directories left by deferred cleanup.
A new queue, datastore, service or parser is unnecessary.

The external/offline distinction is appropriate: bytes physically outside the
configured run filesystem do not consume that filesystem's ledger. Managed
reentry is a fresh physical admission. Classification must use resolved configured
containment, not treat missing configuration as proof of an external export.
The amended text makes this boundary explicit for known offline export callers.

The amended contract explicitly permits reconciled terminal `incomplete` evidence
to be copied. "Complete terminal source receipts" consequently refers to valid
accounting records, not completion of every original source upload. Nonterminal
or corrupt accounting requires reconciliation, never silent byte omission.
Neither copying nor reconciliation may reinterpret the raw `.upload`.

Acceptance must read actual copied bytes, original/source hashes, derived project
identity and exact principal/global totals; cover public/team copies, all five
retained roots, source and destination scopes, managed external reentry, partial
copy/reset and retry, quota rejection before mutation, deferred stale cleanup,
and unrelated reservations. The consumer inventory's prior filter/refusal
recommendations must be superseded by the ratified byte-preserving sharing policy.

SEC-RESUME-02 remains open until implementation and that evidence close the
confirmed copy/reset consumers. This is a design checkpoint, not runtime or
package acceptance.


## Re-review record

The initial canonical draft (`f777fa4e…e642ff`) and decision artifact
(`9df378f9…afe47a`) received COPY-ACCOUNTING-01. This re-review read the complete
amended sharing section and decision artifact whose full hashes are recorded
above. The amendment closes that issue and both terminal-incomplete and explicit
external-boundary clarifications. SEC-RESUME-01 remains resolved by the operator's
sharing decision; SEC-RESUME-02 still requires implemented and tested accounting.
