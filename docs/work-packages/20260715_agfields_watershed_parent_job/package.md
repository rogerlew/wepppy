# AgFields Watershed Parent Job

**Status**: Complete (2026-07-16)
**Timezone**: UTC

## Overview

AgFields Run All currently submits the Concept 1, Concept 2, and hybrid
watershed jobs as three independent top-level jobs. This package changes Run All
to return one canonical RQ parent whose three registered children still execute
serially and write the existing comparable scheme trees.

Single-scheme submissions remain direct jobs. The designated acceptance project
is `/wc1/runs/sa/sacral-self-discipline` on the local forest stack.

## Objectives

- Return one parent `job_id` for a Run All submission.
- Register exactly three scheme children and one terminal finalizer under the
  parent in stable order.
- Preserve serial execution, allow-failure continuation, independent scheme
  state, and the existing `job_ids` scheme mapping.
- Make recursive status, job-info, and cancellation behavior correct for the
  complete parent tree.
- Verify the authenticated workflow and all three output roots on the designated
  forest development project.

## Scope

### Included

- A dedicated AgFields watershed-suite RQ parent task.
- Canonical `job.meta["jobs:<order>,scheme:<scheme>"]` child registration.
- A batch-style finalizer dependency over all three scheme children with
  `allow_failure=True`.
- Additive suite-parent RedisPrep/state hints and UI tracking.
- Correct non-terminal aggregation while any descendant remains active.
- Descendant cancellation even after the dispatch parent itself has finished.
- Route, RQ, job-tree, frontend, graph, contract, and live forest verification.
- Two independent post-implementation reviews and a dedicated security review.

### Explicitly Out of Scope

- Changes to routing science, management inputs, WEPP binaries, or scheme output
  contents.
- Parallel execution of the three memory-intensive watershed schemes.
- New result directories or an `all/` artifact tree.
- Changes to single-scheme submission topology.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful extraction`
- **Authoritative source paths**:
  `wepppy/microservices/rq_engine/ag_fields_routes.py`,
  `wepppy/rq/ag_fields_rq.py`, `wepppy/rq/job_info.py`, and
  `wepppy/rq/cancel_job.py`
- **Cutover proof required**: one authenticated Run All response returns a suite
  parent; `/jobinfo/{parent}` exposes three registered children; recursive status
  remains non-terminal until every child is terminal; all three existing fixed
  output trees complete.
- **Acceptance evidence type**: `both`

## Behavior and Compatibility Contract

- Request `scheme=all` expands to `concept_1`, `concept_2`, and `hybrid` in that
  order.
- The response `job_id` is the new suite parent. `job_ids` remains a mapping from
  those three scheme identifiers to their preallocated child IDs.
- Single-scheme responses retain their current direct job ID and one-entry
  `job_ids` mapping.
- `agfields_run_watershed` remains the historical Concept 2 alias.
  `agfields_run_watershed_suite` is an additive parent key used only by Run All.
- Each child keeps its existing scheme-specific RedisPrep key and NoDb job ID.
- The parent records children as `jobs:0,scheme:concept_1`,
  `jobs:1,scheme:concept_2`, and `jobs:2,scheme:hybrid`.
- The parent records the finalizer as
  `jobs:3,func:finalize_ag_fields_watershed_suite_rq`. The finalizer depends on
  all three scheme job IDs through one `allow_failure=True` dependency, so it
  cannot start until every scheme finishes or fails and it is still released
  when any scheme fails. Canceling the suite cancels the finalizer with the rest
  of the registered tree.
- Concept 2 and hybrid depend on their immediate predecessor with
  `allow_failure=True`, preserving comparison completion without overlapping the
  full-watershed memory peaks.
- The route stores all four planned IDs, the run ID, and sanitized submitter
  metadata atomically when it enqueues the parent. Parent dispatch and recursive
  cancellation share a lock and cancellation marker. The worker refreshes and
  checks that marker before updating metadata under the lock, preventing stale
  parent state from erasing a concurrent cancellation. Child metadata is
  supplied atomically at enqueue.
- Every failure-tolerant dependent applies the Batch Runner ready-deferred release
  guard. Suite-owned scheme children publish normal completion records without
  the suite terminal trigger; only the finalizer emits that trigger.
- A failed child does not make the parent tree terminal while a later child is
  queued, deferred, scheduled, or started. Once all descendants are terminal,
  any failed/stopped/canceled child determines the parent-tree failure status.
- Canceling the suite parent traverses and cancels active descendants even though
  the dispatch parent has already finished.
- Scheme outputs remain under
  `wepp/ag_fields/watershed/{concept-1,concept-2,hybrid}/`.

## Project Data Compatibility and Regression Plan

No NoDb schema or generated artifact schema changes. One additive RedisPrep/state
key names the suite parent; existing keys and per-scheme state remain readable.
Regression coverage must prove the response mapping, parent metadata, dependency
order, reload tracking, aggregated lifecycle, recursive cancellation, and fixed
output paths. Live acceptance must inspect the generated run artifacts in
addition to API responses.

## Stakeholders

- **Primary**: WEPPcloud AgFields operators and Mariana Dobre's science evaluation
- **Reviewers**: two independent Codex subagents
- **Security Reviewer**: independent QA/security subagent
- **Informed**: Roger Lew

## Success Criteria

- [x] Run All enqueues one top-level parent, three registered serial scheme
      children, and an always-released terminal finalizer.
- [x] Single-scheme submission behavior remains unchanged.
- [x] Parent job status and cancellation reflect the full descendant tree.
- [x] Focused, frontend, graph, stub, and full Python gates pass.
- [x] Authenticated `sacral-self-discipline` acceptance completes all scheme trees.
- [x] Two independent reviews and the security gate pass with no unresolved
      medium/high findings.

## Parameterization ADR Gate

- **Parameterization change present**: `no`
- **ADR required**: `no`
- **ADR link(s)**: N/A
- **Decision provenance captured**: `yes`; Roger Lew requested the parent/child
  topology on 2026-07-15, with Codex as implementer.

## Dependencies

### Prerequisites

- Completed routing suite package
  `docs/work-packages/20260714_ag_fields_routing_scheme_suite/`.
- Running local forest WEPPcloud/RQ stack and the designated prepared run.

### Blocks

- Reliable operator comparison and science-evaluation runs launched through Run
  All.

## Timeline Estimate

- **Expected duration**: one focused session
- **Complexity**: Medium
- **Risk level**: Medium

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: the package changes authenticated enqueue topology,
  recursive cancellation, Redis job metadata, and worker dependency edges.
- **Security review artifact**:
  `docs/work-packages/20260715_agfields_watershed_parent_job/artifacts/2026-07-15_security_review.md`

## References

- `wepppy/rq/README.md` - canonical parent/child metadata convention.
- `docs/schemas/rq-engine-agent-api-contract.md` - async response and polling
  contract.
- `wepppy/nodb/mods/ag_fields/ui_control_layout.md` - authoritative AgFields UI
  behavior.
- `wepppy/rq/job-dependencies-catalog.md` - queue dependency catalog.

## Deliverables

- One Run All dispatch parent with three serial scheme children and an
  after-all-children, failure-tolerant finalizer.
- Additive suite state/UI hydration plus recursive status and cancellation
  hardening.
- Regression coverage for dispatch, failure-tolerant release, finalization,
  authentication, status aggregation, cancellation, and browser tracking.
- Updated RQ graph/catalog, API/response contracts, and AgFields UI/module docs.
- Dual-review and dedicated security artifacts with no unresolved findings.
- Authenticated local-forest acceptance evidence in
  `artifacts/2026-07-15_forest_acceptance.md`.

## Follow-up Work

The generic run endpoint-discovery response did not list the live AgFields
routes, so the operator had to use the locally documented OpenAPI route after
discovery. Add AgFields operations to that discovery catalog in a separate,
small operator-usability package; this did not affect the live route or this
package's acceptance.
