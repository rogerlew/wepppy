# Declarative DEM vertical slice

**Status**: Open — planning scaffold, 2026-11-10 20:18 UTC

**Timezone**: UTC

**Owner**: Roger Lew; implementation agent to be assigned

## Overview

Deliver one real declarative acquisition build on the open-wepp-org Kubernetes
cluster using the same DEM RQ task as on-demand modeling. The resulting ordinary
project must retain task/image provenance, finalize read-only, and support an
actual subsequent on-demand viewing task without changing protected build state.
This request scaffolds the work; it does not execute the implementation or deploy.

## Objectives and scope

Implement a minimal operator-invoked independent engine, schema/image admission,
one build-specific queue/worker, shared task observations, local Git checkpoints,
read-only finalization and visible outcomes. Start with `fetch_dem_rq`, one supported
provider and a bounded extent. Select an existing DEM-compatible derived viewing
operation during discovery; do not substitute a dummy task for real consumption.

No full watershed simulation, Bootstrap, reuse/import, incremental rebuild,
formal determinism/comparison, compatibility layer, general workflow language,
new secret-management system, autoscaling or production wepp.cloud rollout.
Operator submission remains private. Existing on-demand task defaults, signatures,
authorization, failure semantics and Compose deployment remain intact.

## Complexity Budget

Reuse RQ/Redis, NoDb ownership, normal project creation/storage, Git, existing
acquisition and viewer tasks, and open-wepp-org image/deployment mechanisms.
Permit a small independent operator engine and image-local adapter, a versioned
v1 request/result contract, deployment-owned approved-image configuration,
project-local provenance records and one dedicated queue/worker per bounded build.
Do not require a new always-running web service, datastore, dependency, cluster,
namespace, filesystem copy tree or cluster-wide privilege. Any necessary scoped
runtime permissions must be explicit and reviewed. Record actual evidence that a
simpler approach failed before escalating beyond this budget, including recovery
cost. One worker is conditional on the selected task not waiting for queued children.

## Implementation fidelity and evidence

Target: faithful reuse of `wepppy/rq/project_rq.py:fetch_dem_rq` and existing
scientific acquisition. This document is a scaffold; package completion requires
wired execution and generated-output evidence on the target cluster. Local tests,
mocked execution, or a new task that never serves a project cannot close it.

## Generated Artifact Validation Gate

Applicable: yes. Retain selected model/extent/provider intent, reloaded NoDb map
state, actual fetched raster identity and semantic readback (CRS, extent, shape,
nodata and meaningful sample content), task/worker/image evidence, Git checkpoint,
read-only state, and a fresh derived viewing result linked to the consumed raster.
Verify normal browse/download and archive/restore preserve the visible records.
Use real writers and readers under actual cluster identities/mounts/umask. No
claim beyond planning is supported today; implementation, local validation,
environment validation and deployment must be tracked separately.

## Success Criteria

- [ ] Contract checkpoint and two independent read-only reviews precede code edits.
- [ ] Valid minimal definition produces a fresh ordinary project on open-wepp-org.
- [ ] Exact approved image/schema admitted; actual task/container identity verified.
- [ ] Real DEM semantic readback and visible task-linked Git provenance pass.
- [ ] On-demand DEM baseline preserves behavior without an engine dependency.
- [ ] Successful build finalizes read-only; protected UI/API/queued mutations fail.
- [ ] Real on-demand derived viewing succeeds after finalization with bounded writes.
- [ ] Failure, checkpoint loss, cancellation, worker interruption and duplicate
      admission leave truthful outcomes and no unintended scientific replay.
- [ ] Bootstrap is unavailable on declarative projects; ordinary Bootstrap unchanged.
- [ ] Browse/download/archive/restore evidence, overhead measurements and rollback
      instructions are retained; failed evidence is not erased.
- [ ] Correctness, QA and security reviews close all medium/high findings.

## Security Impact and Review Gate

Impact: **high** (queue/worker deployment, image authority, path handling and
read-only mutation permissions). Dedicated security review required in
[security review](artifacts/20261110_security_review.md); correctness review is
separate in [correctness review](artifacts/20261110_correctness_review.md).
Both artifacts are pending, not approvals. Operator-approved images and source
access do not permit arbitrary code mounts, credentials or URLs.

## Compatibility and regression plan

Evolve project metadata additively: projects without declarative/provenance fields
remain normal on-demand projects. No wholesale NoDb record migration or parameter
default changes. Write exact field/path and allowed-derived-write contracts before
code. Exercise absent, empty, populated, legacy and malformed states separately
from request combinations. Compare ordinary on-demand behavior using the same
bounded inputs and real generated/consumed artifacts. Preserve mandatory batch
handoffs and catalog rules except for explicitly checkpointed bounded amendments.

## Dependencies and stakeholders

Roger owns product scope. Correctness/UX, QA and security reviewers supply distinct
gates; open-wepp-org owns deployment and its live-change requirements. Cluster
access, image publication path, current capacity and usable source/viewer fixtures
are discovery prerequisites, not presumed blockers or already verified facts.
Parameterization changes: none; no parameterization ADR expected. If needed,
stop and separately scope the scientific change rather than hide it here.

## References and deliverables

- [Canonical proposed specification](../../schemas/declarative-model-build-spec.md)
- [Architecture review dispositions](../../reviews/declarative-model-build-spec-review.md)
- [Tracker](tracker.md)
- [Active ExecPlan](prompts/active/implementation_execplan.md)
- [Contract decision scaffold](artifacts/20261110_contract_decision.md)
- [Evidence ledger](artifacts/validation_matrix.md)

Deliverables are working application/deployment changes in their respective
repositories, current contracts, concrete operator commands, retained sanitized
cluster evidence and an operator runbook. Future full-pipeline expansion is a
separate scope. No delivery date is asserted before fixture/deployment discovery.
