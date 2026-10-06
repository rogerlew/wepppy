# Omni dynamic timeout

**Status**: Completed with validation exception (2026-10-06)
**Timezone**: UTC
**Owner**: Codex
**Amendment**: WRT-02

## Overview

An Omni scenario for production run `electromagnetic-woodcutter` exhausted its
fixed 43,200-second RQ allowance while executing the watershed model. The
existing WRT-01 workload budget was already available to ordinary continuous
watershed children but was not applied to Omni scenario or contrast leaf jobs.
This package extends that existing policy to those two leaf types without
changing its formula, queue topology, model inputs, or retry behavior.

## Objectives

- Apply the existing WRT-01 timeout options to newly submitted continuous Omni
  scenario and contrast leaves.
- Preserve the fixed timeout for single-storm work and for Omni coordinator,
  compile, and finalizer jobs.
- Store the existing `watershed_timeout` metadata on affected leaves so the
  serialized RQ budget is inspectable.
- Validate the exact RQ enqueue options and preserve all dependency edges.

## Scope

### Included

- `wepppy/rq/omni_rq.py` scenario and contrast leaf enqueue options.
- Existing WRT-01 contract, ADR, RQ documentation, stubs, catalog, and tests.
- Contract checkpoint, correctness review, security review, and local
  validation evidence.

### Explicitly Out of Scope

- Changing the WRT-01 coefficient, floor, rounding, or alarm range.
- Changing coordinator, compile, finalizer, hillslope, or model subprocess
  timeouts.
- Automatic retry, mutation of existing failed jobs, deployment, or production
  rerun of `electromagnetic-woodcutter`.
- Queue, dependency, service, datastore, protocol, or topology changes.

## Complexity Budget

- **Existing mechanisms reused**: `watershed_timeout_options`, existing batch
  queue, Omni coordinators, WRT-01 metadata, and current RQ dependency graph.
- **New mechanisms permitted**: one small Omni-owned adapter that reads the base
  project's existing Climate and Wepp controllers and returns WRT-01 options.
- **Simplest plausible change tested first**: compute one option dictionary per
  coordinator invocation and pass it unchanged to each enqueued leaf.
- **Real acceptance condition**: serialized scenario and contrast leaves receive
  the calculated timeout and metadata while non-leaf jobs and dependency edges
  remain unchanged.
- **Evidence required before escalation**: a failing focused test or retained
  serialized job showing that the existing helper cannot represent the leaf.
- **Explicitly prohibited expansion**: new queues, services, stores, daemons,
  dependencies, privileges, protocols, topology, retry loops, or timeout
  coefficients.

## Generated Artifact Validation Gate

- **Applicable**: yes, because the production symptom occurred while an RQ leaf
  consumed prepared WEPP inputs.
- **User-visible failure/outcome**: a valid long continuous Omni leaf no longer
  receives the fixed 12-hour allowance; it receives its WRT-01 budget.
- **Intent evidence**: scenario/contrast definitions selected through the
  existing Omni workflow.
- **Persisted-state evidence**: existing Climate years and Wepp watershed hill
  count read through their normal controllers.
- **Generated-intermediate evidence**: not changed; prepared files remain under
  existing Omni child workspaces.
- **Prepared/consumed-input evidence**: no-prep parsing is not used; the
  coordinator uses the same base controller workload from which Omni child
  inputs are generated.
- **Execution/output evidence**: actual serialized RQ job timeout and metadata
  in a disposable real-Redis graph inspected through `job_info`; production
  execution is outside this package.
- **User-facing result evidence**: job inspection exposes the larger allowance;
  successful production rerun remains a deployment/recovery gate.
- **Direct unmocked boundary**: real `watershed_timeout_options` arithmetic with
  controller-shaped objects plus real RQ serialization/readback and cleanup.
- **Actual-project/environment gate**: the named production failure is retained
  as diagnosis; exact-candidate production-equivalent execution is required
  before claiming environment validation.
- **Highest completion claim currently supported**: implemented and locally
  validated; the broad suite has a documented unrelated catalog-latency
  exception.

## Stakeholders

- **Primary**: WEPPcloud operators and Omni users.
- **Reviewers**: independent correctness and governance reviewers.
- **Security Reviewer**: independent security reviewer.
- **Informed**: maintainers of RQ and Omni orchestration.

## Success Criteria

- [x] Contract checkpoint is independently reviewed and committed before code.
- [x] Scenario and contrast leaves use WRT-01 timeout and metadata.
- [x] Empty, skipped, single-storm, malformed, legacy, and populated states have
  explicit behavior and focused evidence.
- [x] Dependency graph/catalog, focused tests, docs lint, broad-exception
  enforcement, and functional continuation pass.
- [ ] The full Python suite passes cleanly. It stopped after 10,122 passes on an
  unrelated PostgreSQL catalog latency threshold; the failing benchmark passed
  alone, and the remaining functional slice passed with four latency benchmarks
  deselected. See `artifacts/validation.md`.
- [x] No unresolved medium/high correctness or security findings remain.
- [x] Package closes as locally validated, without claiming deployment or repair.

## Parameterization ADR Gate

- **Parameterization change present**: yes; Omni leaf defaults change from fixed
  to workload-derived by applying the accepted WRT-01 policy unchanged.
- **ADR required**: yes; ADR-0076 is amended to record the authorized Omni
  default/application scope while retaining its numeric policy.
- **ADR link**: `docs/adrs/ADR-0076-watershed-runtime-budget.md`.
- **Decision provenance captured**: yes; operator request in this Codex session,
  2026-10-06, with Codex as implementer.

## Dependencies

### Prerequisites

- WRT-01 and `watershed_timeout_options` from the closed watershed timeout
  scaling package.
- Existing Omni job-pool concurrency path.

### Blocks

- Safe deployment and retry of the timed-out production Omni workload.

## Related Packages

- **Depends on**: [Watershed runtime budget](../20260928_watershed_timeout_scaling/package.md).
- **Related**: [Omni contrast EBE sidecars](../20260928_omni_contrast_ebe_sidecars/package.md).

## Timeline Estimate

- **Expected duration**: one focused session.
- **Complexity**: medium.
- **Risk level**: high because RQ admission/resource duration changes.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: leaf RQ resource allowances change; auth, paths,
  subprocess arguments, queue names, and dependency edges do not.
- **Security review artifact**:
  `docs/work-packages/20261006_omni_dynamic_timeout/artifacts/20261006_security_review.md`.

## Hardening and Callus Softening

- **Failure signature**: job `8f8d9f2a-9dd2-4fbe-970b-6898bfccd51a`,
  `JobTimeoutException: Task exceeded maximum timeout value (43200 seconds)`.
- **Related prior hardening efforts**: WRT-01 watershed runtime budget.
- **Health signals**: new continuous leaves expose WRT-01 metadata and a budget
  greater than 43,200 seconds when workload requires it.
- **Danger signals**: unrelated jobs receive larger limits, invalid workload is
  accepted, dependency topology drifts, or workers retain jobs without a finite
  alarm-range timeout.
- **Observation window**: first deployed retry plus seven days of queue review.
- **Temporary calluses introduced**: none.
- **Callus softening hypothesis**: not applicable.

## References

- `docs/schemas/wepp-run-input-contract.md#continuous-watershed-runtime-budget-wrt-01`
- `docs/adrs/ADR-0076-watershed-runtime-budget.md`
- `wepppy/rq/watershed_timeout.py`
- `wepppy/rq/omni_rq.py`
- `tests/rq/test_omni_rq.py`

## Resource and Threat Assumptions

Omni submission remains behind the existing project authorization and tracked
RQ conflict boundary. Scenario fan-out remains the configured scenario set.
Contrast fan-out remains the existing selected contrast set, and
`contrast_batch_size` continues to serialize batches through failure-tolerant
dependencies. WRT-02 adds no fan-out cap and does not increase concurrency; it
only permits each existing finite leaf to remain assigned longer. The existing
WRT-01 alarm-range maximum remains the per-leaf bound. Aggregate queue occupancy
is therefore a known operational risk, not an unbounded new submission surface.
Validation must prove batch boundaries and dependencies are unchanged.

Production rollout requires an empty `default` and `batch` started-job gate,
exact revision/container verification, a rollback revision, and post-retry queue
and worker review. Known subprocess cleanup behavior on timeout is unchanged and
must remain visible in the deployment decision.

## Deliverables

- Contract checkpoint `3c8c9c622ce722180c837e641b6d3bfbe9d67df3`.
- Implementation candidate `adff42d6d9e38f561d41cc681e89f3386ef888c0`.
- Focused state/admission regressions, generated RQ catalog, README, and stub.
- Candidate-bound real-Redis serialization and cleanup evidence.
- Independent correctness and security reviews with no unresolved medium/high
  findings.
- Qualified broad-suite evidence and the retained unrelated latency exception.

## Follow-up Work

- Deploy the validated revision to wepp1 under the production deploy gate.
- Retry and validate the named Omni workload only after deployment evidence.
