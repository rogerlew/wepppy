# Project RQ code quality refactor

**Status** Closed 2026-11-21

**Timezone** UTC

## Scope

Extract WBT subcatchment job-state validation from `wepppy/rq/project_rq.py`.
The worker coordinates Redis transactions for a build job and its completion
receipt. Giving the inspection and validation logic its own module makes the
transaction easier to read and preserves the existing worker import paths.

## Complexity Budget

Use one internal Python collaborator and the current RQ jobs, Redis keys, and
tests. Keep the transaction, dependency registration, and public worker
functions in `project_rq.py`. The budget has no infrastructure or dependency
additions.

## Acceptance and Risk

The fidelity target is a mechanical extraction. The local acceptance gate is
a real Redis-backed test that reuses an admitted job tree and reads back the
two stored jobs, forward and reverse dependencies, queue placement, and tail
key. Exercise existing retry, in-progress and malformed-state cases alongside
project mutation-guard tests. Read back the queue graph from source as a
separate guard against edge changes.

Security impact is low. The extraction touches state validation, with existing
authorization, job key formats, failure outcomes, and transaction ownership.
The tests verify that stale or inconsistent records still fail closed.
There is no numerical parameterization change.

The maintainer owns execution and integration. Close the package after the
focused evidence is recorded, then integrate through a commit-preserving PR.
The operator waived the full test suite.

## Outcome

The project worker delegates WBT subcatchment state inspection to
`project_rq_subcatchment_state.py`. The worker decreased from 3,379 to
3,107 lines. [Validation evidence](artifacts/validation.md) records 86
focused passes, including real Redis readback, and semantic parity for
all 154 queue graph edges.
