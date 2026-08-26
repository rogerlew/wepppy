# Initial independent checkpoint security review

**Reviewer**: Independent read-only security reviewer
**Date**: 2026-08-21 UTC
**Initial verdict**: Fail; four High and two Medium findings

## Findings

- **High — RQ transition race**: Submission locks do not serialize dependency
  release; cancellation needed a watched compare-and-set over RQ state.
- **High — undefined ownership**: A stale, copied, corrupt, or hostile hint
  could target another run or operation without mandatory association checks.
- **High — non-exhaustive boundary**: Registry scanning, especially Batch
  Runner, required a distinct candidate and serialization strategy.
- **High — downstream graph residue**: Canceling only a target's prerequisite
  membership could strand its own deferred dependents.
- **Medium — polling contract conflict**: The controller-state contract still
  classified deferred as nonterminal without defining the retry boundary.
- **Medium — governance metadata**: Register version/count, project discovery,
  stored reviews, disposition, and post-fix confirmation were incomplete.

## Required Corrections

The reviewer required conditional state mutation, canonical run/batch plus
operation/origin/lineage association, a finite source matrix, graph containment,
polling-contract reconciliation, complete register/project metadata, and
post-fix rereview. All findings were accepted for correction; this raw review
is retained and is not rewritten as approval.
