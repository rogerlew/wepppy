# Queue-Sequencing Checkpoint Operations and Security Re-review

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: independent operations/security control agent
- **Review date**: 2026-07-30 UTC
- **Comparison ancestor**:
  `4d2ef5838868bfa02d4badc403ace43f3a95fe84`
- **Working-tree HEAD**:
  `4e5845a04c5b4808d78f4c4806db24e5b90ff70f`
- **Scope**: revised documentation-only queue-sequencing contract, ADR-0033,
  active ExecPlan, tracker, and prior operations/security FAIL artifact
- **Implementation or test review**: not performed
- **Implementation, runtime, acceptance, Forest, or production mutation**:
  none

This re-review assesses the optimistic Redis admission transaction that
supersedes the rejected admission lease and saved dormant child. The decision
is limited to whether the revised documents are a safe contract ancestor for
later implementation and validation.

## Verdict

**PASS — approve the revised documentation-only queue-sequencing checkpoint.**

- **Unresolved High**: 0
- **Unresolved Medium**: 0
- **Unresolved Low**: 0
- **Decision**: approve the exact reviewed documentation fingerprint

The revised protocol removes the unfenced lease and the multi-step durable
pre-activation state. One watched Redis `MULTI`/`EXEC` transaction is now the
only admission commit point. Before `EXEC`, no admission state is durable;
after a successful commit, the complete runnable tree, dependency graph, root
trace, tail, and queue/deferred registration exist together.

This approval does not attest that the implementation realizes the contract.
Runtime promotion remains gated on implementation review, deterministic
Redis evidence, broad validation, final reviews, local acceptance, and the
separately authorized Forest controls.

## Prior Finding Disposition

| Prior finding | Severity | Disposition | Closure |
| --- | --- | --- | --- |
| `QUEUE-OPS-01`: time-bounded admission lease is unfenced | High | Closed | The lease and dormant-child protocol are explicitly superseded. Admission watches the persistent tail and commits the entire runnable tree in one optimistic transaction. A tail conflict retries at most five times and then fails without creating work. No former lease holder can resume and publish stale admission state. |
| `QUEUE-OPS-02`: saved but inactive child has no safe recovery | Medium | Closed | Nothing is durable before `EXEC`; a hard interruption therefore leaves no admission state or a complete runnable tree. Retry and ambiguous-response handling validate the exact committed tree and never activate or duplicate a partial child. |

The prior FAIL artifact remains valid evidence for its earlier document
fingerprint and is not overwritten by this re-review.

## Control Assessment

### Atomic admission and shared-state containment

**PASS.**

The contract identifies one atomic transaction that persists both jobs,
registers both dependency directions, records both root links, replaces the
per-run tail, and adds the mutable child to the applicable queued or deferred
registry. This is the required containment boundary: no separately durable
reservation, saved child, receipt, root link, or activation phase remains.

`WATCH` on the persistent tail serializes competing same-run admissions. A
conflict cannot commit stale predecessor assumptions. The maximum of five
retries bounds admission effort; exhaustion fails closed without work rather
than weakening ordering or silently proceeding.

The complete mutable child still performs construction and abstraction under
one watershed directory-root lock. Its 43,200-second RQ timeout plus
300-second lock margin protects the entire shared mutation lifetime. The
historical abstraction node is expressly nonmutating and cannot repeat
abstraction or write readiness.

### Crash and ambiguous-response recovery

**PASS.**

The contract now states the durable crash postcondition precisely:

- interruption before commit leaves no admission state;
- interruption after commit leaves the complete runnable tree; and
- a saved-but-never-activated child is not a reachable protocol state.

The caller may reuse an existing committed tree only after validating the
tail, both jobs, both root/child links, and dependency state. An ambiguous
Redis response that does not satisfy that exact match fails closed for
operator diagnosis and does not enqueue a duplicate mutation. This preserves
evidence and avoids unsafe cleanup in genuinely inconsistent state.

The contract also makes ordinary retry idempotent by validating and reusing
the already committed root-linked tree. The implementation evidence must
demonstrate that the same IDs are returned and that no second mutation,
receipt, tail, or dependency graph is created.

### Execution trace and terminal cleanup

**PASS.**

Both child IDs become root-linked in the same transaction that makes the
mutable child runnable or deferred, so execution cannot outrun its public
trace. Each child carries bounded linkage to the root and its sibling.

A later child depends on an active prior complete child with failure allowed;
a missing or terminal tail is replaced without an impossible dependency.
Compare-and-delete release permits a child to remove only its own still-current
tail. A controlled or unexpected mutable-child failure cancels only its
matching receipt and must leave no deferred-registry or dependency-set
residue. These controls contain cleanup to the exact admission tree and
preserve unrelated same-run work.

### Rollback, recovery authority, and post-action review

**PASS for the documentation checkpoint.**

ADR-0033 records the queue decision owners, rejected alternatives, operational
parameters, required evidence, risks, and coordinated rollback boundary.
Rollback must first stop enqueue surfaces, drain workers, and move all
web/worker consumers to the reviewed revert together. Existing tail keys and
terminal jobs are treated as inert. Tail removal is limited to a verified tail
whose referenced job is missing or terminal, preventing an operator from
manually releasing a mutation that may still execute.

The active ExecPlan retains coordinated quiescence, registry checks, exact
revision verification, rollback containment, retained artifacts, and
post-action review. The tracker keeps implementation validation, local E2E,
and Forest work blocked behind this checkpoint and subsequent gates.

### Security and audit boundary

**PASS.**

The revision does not expand authorization or expose the private WBT policy
snapshot. Existing audit rules allow bounded actor, run, root/child,
correlation, policy-source, outcome, and error identifiers while excluding
JWTs, cookies, session identifiers, email, CSRF tokens, and database
credentials. Fail-closed ambiguity handling preserves the execution record
for diagnosis instead of destroying evidence.

## Required Implementation Evidence

Approval of the document ancestor requires, but does not substitute for,
durable implementation evidence proving:

- concurrent admissions in both orders, forced `WATCH` conflicts, successful
  retry, and five-conflict exhaustion with no created work;
- hard interruption immediately before and after `EXEC`, showing respectively
  no admission state and one complete runnable tree;
- committed-but-ambiguous response reconciliation, exact-tree reuse, and
  fail-closed behavior for every deliberately mismatched tree component;
- atomic presence of both jobs, both dependency directions, both root links,
  the persistent tail, and correct queued/deferred registry membership;
- idempotent retry returns the original exact tree without duplicate mutation;
- successful and failed predecessors, both opposite-policy execution orders,
  missing and terminal stale-tail recovery, and compare-and-delete release;
- matching-receipt cancellation plus empty deferred and dependency registries
  after controlled and unexpected child failure;
- complete-child directory-lock ownership through build and abstraction, with
  no shared NoDb/cache policy leakage;
- secret-free correlated execution evidence sufficient for post-action review;
  and
- a coordinated rollback drill that demonstrates enqueue quiescence, worker
  drain, consumer revision agreement, and only verified tail cleanup.

Any change to the transaction contents, watched state, five-conflict bound,
tail lifetime, dependency policy, receipt semantics, directory-lock lifetime,
ambiguity matching, cleanup authority, or rollback sequence invalidates this
approval and requires a new ADR amendment and independent checkpoint.

## Reviewed Snapshot

The reviewed sources were uncommitted working-tree documents based at
`4e5845a04c5b4808d78f4c4806db24e5b90ff70f`. Hashes are SHA-256:

| Reviewed item | SHA-256 |
| --- | --- |
| user-context contract amendment | `c51e794bfbc633ef545e344c3aedaa9a8a0bd51c483ea0fe61c8d723f2216edd` |
| ADR-0033 | `81d8473651698579cb67d483a1f96d5dc50001597139655ca72be4864187c3bb` |
| active ExecPlan | `228cfc093772ceb67f011684cf28d328ba3317f20ad789576462f5fd72d7d58c` |
| work-package tracker | `f6f18fa87615dba19a2874ed9ae83b6b0ac07b6627402098e133779e9406611a` |
| prior operations/security FAIL artifact | `fbed82c09135480bca3aef03229632440d13bf7fce2a84fbf5dfcea94c4f1210` |

## Gate Decision

- **Exact documentation-only queue-sequencing checkpoint**: approved
- **Standalone ancestor commit**: may proceed after the other required
  independent checkpoint also passes for the same source fingerprint
- **Implementation review**: not performed; still required
- **Local acceptance mutation**: not authorized by this review
- **Forest preflight/migration/canary**: not authorized by this review
- **Production/wepp1**: unauthorized and untouched
