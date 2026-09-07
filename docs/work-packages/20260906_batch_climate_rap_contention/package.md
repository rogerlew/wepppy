# Batch Climate and RAP NoDb Contention

**Status**: Closed 2026-09-07 — implementation and authorized local validation complete
**Timezone**: UTC

## Overview

Correct reproducible `NoDbStaleWriteError` failures in openWEPP batch watershed
jobs after the batch/culvert Climate rehydration rollout. The outer cache guard
is working as designed, but long-running Climate and RAP_TS operations retain a
controller mutation base across intervening whole-object NoDb rewrites. This package gives each affected operation explicit writer ownership
and a fresh, bounded finalization transaction without weakening stale-write
detection.

The operator subsequently clarified that the failure is specific to a separate
Kubernetes deployment and prohibited live reruns. Execution covers code,
isolated regressions, and reviews; deployment attribution and recurrence are
unmeasured. Source inspection does not establish a nested writer as the
incident cause. See [writer attribution](artifacts/2026-09-07_writer_attribution.md).

## Incident Evidence

- Environment: openWEPP Kubernetes canary, WEPPpy `87cfe4047`, image digest
  `sha256:bdbe374f5245a35a40e63347934887ffe3dcae9ffcf41ea11b123ae55ebe9c98`.
- Batch: `nasa-roses-202608-psbs`.
- Climate examples:
  - job `ba5479c1-9da3-4a91-b185-a0ff81ce3a1b`, run `OR-206`;
  - job `d54a9820-97c2-454c-90cd-6e8e29d2de56`, run `OR,WA-101`;
  - job `12e593e7-6779-41fb-aaff-5cd6e296fe6c`, run `WA-19`.
- RAP_TS examples:
  - job `ddee1946-20a8-400f-9568-712d8fb2f7d3`, run `WA-156`;
  - job `1fbdd5bb-7ae8-4387-99c4-fd86775bb181`, run `OR-39`.
- Exact signature: `NoDbStaleWriteError: stale NoDb write rejected`, with the
  expected and observed files having equal sizes but mtimes separated by about
  0.3 to 12 seconds.
- Runtime logs show Climate hillslope builds and RAP year/band analysis using
  thread pools immediately before the failures. RQ reports `Job OK` because
  `run_batch_watershed_rq()` converts the domain exception to `(False,
  elapsed)`; StatusMessenger separately publishes `EXCEPTION_JSON`.
- Diagnostic anomaly: `202608` run paths emitted logger names containing
  `nasa-roses-202606-psbs`. Treat copied controller/logger identity as an
  investigation item, not as the established cause of the stale write.

## Objectives

- Reproduce both Climate and RAP_TS same-size contention failures against real
  temporary `.nodb` files.
- Attribute every write to `climate.nodb` and `rap_ts.nodb` in the failing
  operations before choosing the mutation boundary.
- Refactor affected long-running work into collect-then-finalize or another
  contract-conforming single-writer transaction.
- Preserve unrelated durable rewrites and explicitly reject relevant-input
  changes; never retry by dumping a stale object.
- Keep generated climate and RAP artifacts, task timestamps, retry selection,
  and batch completion classification compatible.
- Make the domain failure unambiguous in tests and operator evidence without
  changing RQ completion/trigger semantics unless a standalone contract
  checkpoint authorizes that behavior change.

## Scope

### Included

- `Climate.build()` modes exercised by the failing observed GridMET batch path,
  including PRISM revision and hillslope-climate helpers.
- `RAP_TS.acquire_rasters()` and `RAP_TS.analyze()` mutation ownership where
  they can persist `rap_ts.nodb`.
- BatchRunner hydration/finalization integration needed for those controllers.
- Copied-run controller/logger identity diagnosis where it affects hydration,
  cache keys, lock keys, or persistence targets.
- Deterministic contention, partial-failure, compatibility, and isolated
  generated-output evidence.
- Canonical NoDb contract/docs updates if discovery establishes a missing rule.

### Explicitly Out of Scope

- Weakening or suppressing `NoDbStaleWriteError`.
- Generic whole-object merge, blind retry, global cache clearing, or longer
  lock TTL as a substitute for writer ownership.
- Queue topology, worker count, scheduling priority, climate/RAP scientific
  parameterization, output schema, or UI redesign.
- Culvert paths without a reproduced equivalent failure.
- Changing `BATCH_WATERSHED_TASK_COMPLETED` or RQ success/failure semantics
  without first amending the applicable canonical contract in a standalone
  ancestor commit.
- Deployment or live replay on any host, per the operator's execution amendment.

## Contract and Compatibility Plan

- Canonical authority:
  `docs/schemas/nodb-persistence-concurrency-contract.md`, especially Writer
  Ownership and Mutation Topology.
- Scoped cache invalidation remains governed by
  `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`; it is an
  initial-hydration guard, not a multi-writer solution.
- No user-visible key, NoDb attribute, parquet schema, generated filename, or
  batch result shape is intentionally changed.
- Relevant-input snapshots and derived-output allowlists must be explicit for
  each controller. Unsupported legacy or malformed state must fail explicitly
  without overwriting durable state.
- If current RQ result/trigger behavior is judged incorrect, stop implementation
  of that portion, document the proposed contract, and obtain the required
  contract-decision checkpoint before code changes.

## Success Criteria

- [x] Real-file Climate and RAP regressions reproduce the same-size stale-write
  signature before the patch and pass afterward.
- [x] Expensive collection runs outside NoDb locks; finalization freshly
  hydrates, compares relevant inputs, applies derived-field allowlists, and
  commits once.
- [x] Unrelated edits survive; relevant edits reject publication explicitly.
- [x] Collection and finalization failures preserve or retain recoverable
  artifacts without publishing false completion timestamps.
- [x] Batch failure metadata, retry selection, summary, tuples, and triggers
  retain their existing semantics.
- [x] Independent correctness, code, QA, and security reviews have no unresolved
  medium/high findings.
- [x] Focused, persistence, stub, and generated-output checks pass.
- [x] Full repository suite: 7535 passed, 63 skipped; final documentation,
  stub, Vulture, and exception checks pass.
- [x] Exclude live reruns and deployment as directed by the operator; do not
  claim an observed Kubernetes post-fix exception count.
## Related Work

- [`20260820_climate_finalize_lock`](../20260820_climate_finalize_lock/package.md)
  established the collect-then-finalize pattern for multiple-interpolated
  GridMET/Daymet builds. Reuse its explicit input snapshots and derived-field
  allowlists; this recurrence covers different observed-GridMET/PRISM and RAP
  paths.
- [`20260904_batch_culvert_climate_rehydration_b`](../20260904_batch_culvert_climate_rehydration_b/package.md)
  added the outer cache-rehydration boundary. Preserve it and prove why it is
  insufficient for nested persistence contention.
- `docs/standards/hardening-lifecycle-standard.md` governs this recurrence.

## Hardening Hypothesis and Signals

- **Hypothesis**: If Climate and RAP_TS collect derived work without persisting
  a long-lived controller, then finalize once from freshly hydrated state under
  the controller lock, the target stale-write signature will disappear while
  legitimate concurrent relevant-input changes remain protected.
- **Health signals**: exact
  unrelated/relevant interleaving tests pass; successful runs retain expected
  artifacts and timestamps; failed runs remain retry-eligible.
- **Danger signals**: stale-object dump retries, missing or duplicate artifacts,
  lock duration spanning remote/parallel work, silently overwritten inputs,
  false RQ success, or increased cache/lock clearing.
- **Observation model**: recurrence-triggered. Isolated tests establish local
  conformance; deployment recurrence remains unmeasured. Durable danger signals
  are in `docs/dev-notes/batch-climate-rap-finalization.md`.
- **Temporary calluses**: none planned.

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Rationale**: worker concurrency, run-tree persistence, subprocess-derived
  artifacts, and queue failure reporting are high-impact repository surfaces.
- **Required artifact**:
  `artifacts/2026-09-07_security_review.md`

## Deliverables

- Contract checkpoint if required by discovery.
- Minimal Climate and RAP_TS ownership/finalization implementation.
- Direct real-file regressions plus focused and repository validation evidence.
- Completed correctness, code, QA, security, and isolated acceptance artifacts.
- Updated package tracker and `PROJECT_TRACKER.md` at every milestone.
