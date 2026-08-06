# Culvert NoDb Writer Hardening

**Status**: Closed

**Started**: 2026-08-06 00:24 UTC

**Completed**: 2026-08-06 01:15 UTC

**Timezone**: UTC

## Overview

A production culvert batch parent loaded `culverts_runner.nodb`, then lost a
stale-write race to the submit route while preparing shared topology. The NoDb
generation guard rejected the parent's later write, correctly preventing lost
state, but the parent failed before enqueueing any culvert children. This
package restores the already-ratified NoDb writer-ownership contract: the
worker owns the parent receipt, the parent owns planned child receipts, each
child owns only its run directory and `run_metadata.json`, and the finalizer
alone merges child results into the shared `_runs` map.

## Objectives

- Remove the submit route's post-enqueue `culverts_runner.nodb` write.
- Keep the parent worker as the single writer of its RQ receipt.
- Refresh and retry the initial shared runner-state transaction after a bounded
  `NoDbStaleWriteError` or lock conflict.
- Remove all child-worker writes to shared `CulvertsRunner` state.
- Preserve NoDb generation checks and make the finalizer the authoritative
  merge point for per-run results.

## Scope

### Included

- Culvert batch submission in `wepppy/microservices/rq_engine/culvert_routes.py`.
- Culvert parent, child, and finalizer behavior in `wepppy/rq/culvert_rq.py`.
- Shared-run registration behavior in `wepppy/nodb/culverts_runner.py`.
- Focused regression tests, operator/developer documentation, and review
  artifacts.

### Explicitly Out of Scope

- Disabling or weakening NoDb stale-write detection.
- Changing RQ queues, dependency edges, retry policy, or API response shapes.
- Serializing independent child jobs or moving their run-local artifacts into
  shared storage.
- Repairing completed historical batch artifacts.

## Production Incident

- **Host/runtime**: submitted through `rq-engine` on `wepp1`; parent executed by
  a batch worker on `wepp2`.
- **Batch UUID**: `be84c595-4a3e-4de3-bea5-2f0c4068cea4`.
- **Parent job**: `7e409490-68be-4471-bd4a-59414e7e1eaa`.
- **Failure time**: 2026-08-05 16:33:49 UTC.
- **Failure signature**: `NoDbStaleWriteError` rejected an expected
  `(mtime=1785947422.189831, size=644)` generation after observing
  `(mtime=1785947422.319827, size=759)`.
- **Impact**: the parent failed after about 207 seconds of topology work and
  before any child enqueue; there was no overlapping archive/fork job.
- **Corroborating signal**: earlier successful batches logged 22 stale shared
  child-metadata writes while still finalizing complete 5/5 and 19/19
  summaries.

## Contract-First Classification

This is a conformance fix. The authoritative behavior in
`docs/schemas/nodb-persistence-concurrency-contract.md` and
`docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md` was clarified
in commit `bf88592dddd728df124edeff2ed78283148c2cdc` before this package opened.
The defect is that culvert route and child code still violates the committed
single-writer/finalizer pattern. No API, authorization, payload, or job-graph
contract changes.

## Stakeholders

- **Primary**: WEPPcloud operators and culvert batch users.
- **Maintainers**: NoDb, rq-engine, and culvert orchestration maintainers.
- **Reviewers**: independent correctness, QA, and security reviewers.

## Success Criteria

- [x] The submit route returns the parent job ID without creating or mutating
  `culverts_runner.nodb`.
- [x] The parent worker persists its receipt and retries the initial runner
  state transaction after bounded stale refresh.
- [x] Child workers never lock or mutate the shared runner `_runs` map.
- [x] The finalizer reconstructs and persists statuses/errors from each
  `run_metadata.json`.
- [x] The stale-write guard remains enabled and unchanged.
- [x] Focused tests, full pytest, documentation lint, code-quality checks, and
  review gates pass with no unresolved medium/high findings.

## Parameterization ADR Gate

- **Parameterization change present**: `no`
- **ADR required**: `no`
- **ADR link(s)**: N/A
- **Decision provenance captured**: `yes` (production incident and operator
  hardening request, 2026-08-05; implementer: Codex)

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: the package touches an existing public submission
  handler, queue worker persistence, and cross-process data-integrity behavior.
  It does not widen authentication, accepted input, filesystem roots, or queue
  topology.
- **Security review artifact**:
  `artifacts/2026-08-05_security_review.md` (completed)

## Hardening and Callus Softening

- **Failure hypothesis**: a long-lived cached runner instance permits a
  short-lived route or parallel child to advance the shared file generation;
  the later dump is then correctly rejected.
- **Health signals**: no culvert parent failures with this stale signature; no
  child warnings about shared runner metadata writes; final summaries match
  per-run metadata counts.
- **Danger signals**: missing parent/child job receipts, finalizer totals that
  differ from run directories, or any accepted write from a stale generation.
- **Observation window**: 30 days after deployment.
- **Temporary calluses introduced**: none. Bounded refresh is the canonical
  transaction pattern, not a bypass or indefinite retry.

## Related Work

- `docs/schemas/nodb-persistence-concurrency-contract.md` - authoritative
  writer-ownership and stale-write rules.
- `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md` - bounded
  refresh-under-lock transaction guidance.
- `docs/standards/hardening-lifecycle-standard.md` - incident lifecycle gates.
- `docs/culvert-at-risk-integration/weppcloud-integration.spec.md` - finalizer
  ownership of shared result aggregation.
- `docs/work-packages/20260428_build_soils_rq_stale_cache_guard/` - related
  stale-cache precedent.
- Commit `6e9ed34b7` - prior bounded retry for parent-owned child job IDs.

## Deliverables

- Regression-backed single-writer implementation.
- Updated culvert integration documentation.
- Code-review, QA-review, and security-review disposition artifacts.
- Completed/archived ExecPlan and 30-day production observation guidance.

## Closure

The route no longer writes the parent receipt after enqueue, the parent owns
shared planning state with bounded fresh-instance retry, and children write
only run-local metadata. The finalizer replaces its authoritative result fields
from current `run_metadata.json` files so a successful retry cannot retain an
older error. The NoDb generation guard remains unchanged.

Focused validation passed with 43 tests; the repository suite passed with
5,842 tests and 61 skips. RQ graph, documentation, broad-exception, and diff
checks passed. Independent correctness, QA, and high-impact security review
closed with no unresolved findings. The remaining operational action is the
30-day observation window described below.

## Follow-up Work

- Observe production logs and completed batch summaries for 30 days after
  deployment. Open a separate package only if evidence identifies another
  shared-state writer or receipt-recovery gap.
