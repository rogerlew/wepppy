# SURF-14A Queue-Sequencing Amendment Governance Re-review

## Metadata

- **Reviewer**: independent governance/correctness control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Accepted base**: `4d2ef5838868bfa02d4badc403ace43f3a95fe84`
- **Prior review**:
  `artifacts/2026-07-30_queue_sequencing_checkpoint_governance_review.md`
- **Primary review boundary**: the revised post-`4d2ef5838` atomic-admission
  delta in
  `artifacts/2026-07-30_contract_amendment_delineation_snapshot.md` and
  ADR-0033
- **Supporting records**: active ExecPlan and package tracker
- **Implementation, test, acceptance, Forest, or production review**: none

This re-review considered only whether the revised queue-sequencing
documentation closes the prior governance findings and is ready to become a
standalone contract ancestor. Existing implementation and test changes in the
shared working tree were deliberately excluded.

## Verdict

**FAIL — REJECT checkpoint ratification and a documentation-only standalone
ancestor for this fingerprint.**

**Findings**: 0 High, 1 Medium, 0 Low.

The optimistic Redis transaction contract closes the prior High
saved-but-never-activated orphan finding. The ExecPlan and tracker correctly
retain the checkpoint as pending. ADR-0033, however, still does not preserve
the exact queue-decision provenance and supporting evidence required by the
repository's mandatory parameterization ADR standard.

No break-glass basis was requested or documented. Runtime implementation,
acceptance, Forest, and production remain unauthorized by this review.

## Prior Finding Disposition

### GOV-SEQ-01 — Closed

The revised contract supersedes the leased multi-step admission with one
watched `MULTI`/`EXEC` transaction. Nothing is durable before `EXEC`; the
transaction includes both jobs, both dependency directions, both root links,
tail replacement, and queued/deferred membership. Its normative postcondition
is therefore no admission state or one complete runnable tree.

The surrounding contract also bounds contention to five retries that create no
work on exhaustion, reuses an exact committed tree from root linkage, validates
all relevant linkage after an ambiguous response, fails closed rather than
duplicating a mutation, and limits receipt cancellation and dependency cleanup
to the matching tree. ADR-0033 retains explicit pre-/post-commit hard-stop,
conflict, stale-tail, ambiguous-response, idempotent-retry, cancellation, and
registry-cleanup evidence obligations.

This closes the governance-level crash-consistency and revocation gap for the
documented design. It does not attest that the current implementation realizes
the contract or that the required fault evidence passes.

### GOV-SEQ-02 — Partially closed; superseded by GOV-SEQ-RR-01

ADR-0033 now records the queue mechanism, exact lock and retry parameters,
responsibility split, rejected admission alternatives, rollback coordination,
and future evidence matrix. Those are material improvements. The remaining
mandatory record gap is narrowed below.

## Finding

### GOV-SEQ-RR-01 — Medium: ADR-0033 still lacks exact provenance and linked evidence

`docs/standards/parameterization-adr-standard.md` requires a decision venue
with date/time and timezone, named decision owners and implementers, evidence
links, and risk/rollback notes. ADR-0033 identifies a two-day workspace-thread
range but no decision time or timezone. It describes the operator, maintainers,
and independent reviewers by role, but does not distinguish the exact
queue-revision proposal/approval event from the earlier user-preference
decisions in its provenance section.

The ADR's `Evidence` section still links ownership sources and the general
SURF-14A amendment. The queue-specific paragraph says which evidence will be
required later; it does not link the two prior queue checkpoint reviews, the
forced-order evidence that motivated the complete-child design, or any retained
artifact supporting the selected transaction, lock-margin, tail, and receipt
choices. Its rollback language is useful, but the residual risks and concrete
revert triggers for the chosen design remain implicit.

This is a durable governance-record defect, not a rejection of the atomic
admission choice. It remains Medium because the contract itself is
crash-consistent and release is still gated, but the ADR would not let a later
maintainer reconstruct who approved the revision, when they did so, which
evidence supported it, and which observed condition requires revocation.

Required closure:

1. Record the queue-revision decision date/time and timezone, and distinguish
   the requesting operator's authority, the maintainer proposal, and the
   independent checkpoint decision.
2. Link the retained prior queue reviews and the exact existing ordering/race
   evidence. Clearly separate that evidence from the fault-injection evidence
   that remains required before final implementation approval.
3. State the chosen design's residual risks and observable rollback/revocation
   triggers, including conflict exhaustion, non-exact ambiguous reconciliation,
   stale-tail repair, or inability to coordinate all enqueue/worker consumers.
4. Re-run this documentation-only re-review on the amended fingerprint before
   creating the standalone ancestor.

## Accepted Scope and Remaining Gates

The following portions are accepted and may be retained:

- one complete mutable build-plus-abstraction child under the directory-root
  lock;
- a nonmutating completion receipt;
- a persistent watched per-run tail with compare-and-delete release;
- one no-pre-`EXEC`-state admission transaction and a five-conflict bound;
- exact-tree idempotent retry and fail-closed ambiguous-response handling; and
- checkpoint revocation for changes to admission, dependencies, tail lifetime,
  lock parameters, receipt semantics, or recovery.

The package records correctly leave dual approval and the standalone
documentation ancestor incomplete. After GOV-SEQ-RR-01 is closed, this exact
documentation must receive both independent PASS reviews, retain findings
disposition, and be committed alone as an ancestor before conforming or
approving implementation.

## Validation

- `wctl doc-lint` passed separately for ADR-0033, the contract amendment,
  active ExecPlan, and tracker.
- `git diff --check` passed for all four reviewed sources.
- `uk2us` preview found one non-substantive spelling suggestion in the
  ExecPlan; it does not affect this verdict.

## Review Fingerprint

The re-review used Git `HEAD`
`4e5845a04c5b4808d78f4c4806db24e5b90ff70f` and compared the four current
records against accepted base
`4d2ef5838868bfa02d4badc403ace43f3a95fe84`. Hashes are SHA-256:

| Reviewed item | SHA-256 |
| --- | --- |
| `docs/adrs/ADR-0033-user-defaults-and-wbt-boundary-policy.md` | `81d8473651698579cb67d483a1f96d5dc50001597139655ca72be4864187c3bb` |
| `artifacts/2026-07-30_contract_amendment_delineation_snapshot.md` | `c51e794bfbc633ef545e344c3aedaa9a8a0bd51c483ea0fe61c8d723f2216edd` |
| `prompts/active/user_preferences_wbt_boundary_execplan.md` | `228cfc093772ceb67f011684cf28d328ba3317f20ad789576462f5fd72d7d58c` |
| `tracker.md` | `f6f18fa87615dba19a2874ed9ae83b6b0ac07b6627402098e133779e9406611a` |
| Prior governance FAIL artifact | `db6e004efb1ebf840eeeca3089937b54b9f266606ee211f692d8bb6734fe2936` |
| Ordered post-`4d2ef5838` binary diff | `b77e4f07899a9bab33326b61520f12de308a49d70010bbe5cabf233faf6357f7` |
