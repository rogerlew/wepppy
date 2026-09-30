# Batch Daymet Multiple NoDb Contention

**Status**: Open (2026-09-30)
**Timezone**: UTC

## Overview

Fix recurrent `NoDbStaleWriteError` failures in the open-wepp.org Kubernetes
batch path when observed Daymet climates use `ClimateSpatialMode.Multiple`.
Earlier collect-then-finalize work covered multiple-interpolated and selected
GridMET/PRISM paths, but live job evidence shows the legacy observed-Daymet
build and its subsequent PRISM revision can still observe a competing rewrite
of the same run's `climate.nodb`.

Implementation and local integration will run on `forest`. The final
file-backed integration test will run on the open-wepp.org cluster under a
separate explicit execution gate, using retained job and artifact evidence.

## Incident Evidence

- Environment: open-wepp.org Talos/Kubernetes cluster.
- Deployed WEPPpy revision: `ce09d3ace81cb6e376eb086cf62149cd9425d183`.
- Batch job: `a7d21ee5-49e6-480f-9658-b825c8be6150`, batch `st-joe-mofe`.
- Snapshot during execution: 84 of 170 complete and 40 failures.
- Root causes displayed by the job dashboard: 38 child
  `NoDbStaleWriteError` failures, one
  `WbtUnresolvedDepressionsError`, and the failed parent job-order roll-up.
- Affected stacks terminate from either
  `Climate._build_climate_observed_daymet()` or `run_prism_revision()` while
  exiting a NoDb lock and dumping `climate.nodb`.
- Representative files have unchanged size but a newer observed mtime,
  generally separated by fractions of a second to about eleven seconds.
- The WBT unresolved-depressions failure is an input/conditioning exception
  and is not part of this package.

## Objectives

- Reproduce the observed-Daymet/`Multiple` same-size stale-write signature
  against real temporary NoDb files.
- Attribute every writer that can touch a leaf run's `climate.nodb` between
  batch base resynchronization, Daymet collection, PRISM revision, and final
  persistence.
- Extend the existing snapshot, collect, rehydrate, validate, publish, and
  dump-once pattern to the uncovered path without weakening stale-write
  rejection.
- Prove that a single leaf cannot execute two climate writers concurrently, or
  correct the smallest lock/cache boundary that permits it.
- Preserve scientific inputs, generated climate artifacts, task timestamps,
  retry classification, RQ dependency edges, and result contracts.
- Validate locally on `forest`, then run one bounded file-backed integration on
  the open-wepp.org cluster and retain exact revision, job-tree, controller,
  generated-input, and output evidence.

## Scope

### Included

- `wepppy/nodb/core/climate.py` observed-Daymet single build used before
  PRISM revision in `ClimateSpatialMode.Multiple`.
- Existing climate collect/finalize collaborators where they can be reused
  without adding a parallel architecture.
- `wepppy/nodb/batch_runner.py` climate mutation and directory-root lock
  boundary, including duplicate leaf-execution attribution.
- Focused real-file concurrency tests and generated climate artifact checks.
- Forest execution and a separately gated open-wepp.org cluster integration
  test after local correctness and security review pass.

### Explicitly Out of Scope

- Weakening, suppressing, or automatically retrying `NoDbStaleWriteError`.
- Generic whole-object merging, global cache clearing, longer lock leases, or
  reduced worker count as the fix.
- Queue, Redis, NFS, Kubernetes topology, or worker placement changes.
- Climate parameterization, precipitation calculations, breach distance, DEM
  conditioning, or remediation of the WBT exception.
- Production Compose deployment on `wepp1`, `wepp2`, or `wepp3`.
- Repair or automatic replay of the affected batch runs; that requires a
  separate operator decision after the implementation is accepted.

## Complexity Budget

- **Existing mechanisms reused**: NoDb controller locks, batch directory-root
  locks, scoped cache invalidation, climate input snapshots, collect/finalize
  services, current batch queues, and existing test fixtures.
- **New mechanisms permitted**: none initially.
- **Simplest plausible change tested first**: extend the existing climate
  collect/finalize ownership boundary to observed Daymet followed by PRISM
  revision, with a fresh controller rehydrate and one durable commit.
- **Real acceptance condition**: a production-equivalent multi-worker batch
  leaf completes on open-wepp.org without `NoDbStaleWriteError`, produces the
  expected climate artifacts, and preserves a deliberate unrelated concurrent
  controller edit.
- **Evidence required before escalation**: a retained real-file failure showing
  that the existing locks and collect/finalize primitives cannot satisfy the
  acceptance condition.
- **Explicitly prohibited expansion**: new queue, datastore, daemon,
  dependency, privilege, protocol, retry service, or deployment topology.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction.
- **Authoritative source paths**: `wepppy/nodb/core/climate.py`,
  `wepppy/nodb/core/climate_multiple_build.py`, related observed-build and
  mode-routing collaborators, and `wepppy/nodb/batch_runner.py`.
- **Cutover proof required**: trace or instrumentation must show the real
  `ClimateSpatialMode.Multiple` batch path enters the corrected ownership
  boundary; helper-only tests are insufficient.
- **Acceptance evidence type**: both generated output and real-file
  integration evidence.

## Contract and Compatibility Plan

The canonical authority is
`docs/schemas/nodb-persistence-concurrency-contract.md`. This is intended as a
conformance repair: collect expensive work without retaining mutation
authority, then lock, rehydrate durable state, reject changed relevant inputs,
apply only explicit derived outputs, and dump once. No user-visible key, NoDb
schema, generated filename, scientific parameter, queue edge, or RQ result
shape is intentionally changed. If source attribution requires a behavior or
contract change, stop at the ancestor-checkpoint gate before implementation.

## Generated Artifact Validation Gate

- **Applicable**: yes; climate files are generated and consumed by later WEPP
  preparation.
- **User-visible failure/outcome**: the batch leaf currently fails with a stale
  `climate.nodb` write; afterward the same supported leaf completes without
  overwriting a concurrent unrelated edit.
- **Intent evidence**: retained batch configuration and climate mode/spatial
  mode readback.
- **Persisted-state evidence**: freshly reloaded `climate.nodb` through the
  normal `Climate` reader.
- **Generated-intermediate evidence**: relative-path manifest and semantic
  parsing of generated CLI/PRN/parquet and applicable PRISM-revised files.
- **Prepared/consumed-input evidence**: read back the exact climate artifact
  opened by the downstream WEPP preparation step.
- **Execution/output evidence**: exact image/revision, RQ job tree, leaf result,
  and fresh output on open-wepp.org.
- **User-facing result evidence**: job dashboard and batch completion readback.
- **Direct unmocked boundary**: real NoDb file rewrite/interleaving and final
  serializer commit.
- **Actual-project/environment gate**: forest for implementation validation;
  open-wepp.org for the final bounded file integration test.
- **Highest completion claim currently supported**: diagnosed.

## Success Criteria

- [ ] A deterministic real-file test reproduces the live same-size stale-write
      signature before the change.
- [ ] Source attribution identifies the competing writer or proves the precise
      lock boundary that permits it.
- [ ] Observed Daymet plus PRISM `Multiple` uses the established
      collect-then-finalize ownership contract with no long-lived stale dump.
- [ ] Relevant concurrent input changes reject publication; unrelated durable
      edits survive successful finalization.
- [ ] Generated climate artifacts and downstream consumed inputs are
      semantically equivalent for an unchanged fixture.
- [ ] Focused NoDb/climate/batch tests and the full repository suite pass on
      forest.
- [ ] Independent correctness and security reviews have no unresolved medium
      or high findings.
- [ ] A separately authorized open-wepp.org file integration run passes with
      exact revision, job-tree, file-content, and user-facing evidence retained.
- [ ] Deployment, batch repair, and incident resolution are claimed only when
      their distinct evidence gates are satisfied.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **ADR links**: N/A.
- **Decision provenance captured**: yes; Roger selected forest execution and
  open-wepp.org file integration on 2026-09-30.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: the change affects multi-worker persistence ownership,
  run-tree file publication, and RQ execution boundaries.
- **Security review artifact**:
  `artifacts/2026-09-30_security_review.md`.

## Hardening and Callus Softening

- **Failure signatures**: `NoDbStaleWriteError: stale NoDb write rejected` from
  observed-Daymet and PRISM-revision climate builds in job
  `a7d21ee5-49e6-480f-9658-b825c8be6150`.
- **Related prior hardening efforts**:
  [`20260820_climate_finalize_lock`](../20260820_climate_finalize_lock/package.md),
  [`20260904_batch_culvert_climate_rehydration_b`](../20260904_batch_culvert_climate_rehydration_b/package.md), and
  [`20260906_batch_climate_rap_contention`](../20260906_batch_climate_rap_contention/package.md).
- **Health signals**: zero stale writes on the target path, one writer per leaf,
  preserved concurrent unrelated edits, and valid generated/consumed files.
- **Danger signals**: blind retry, larger cache-clearing scope, long-held lock
  during remote/parallel work, duplicate publication, or changed scientific
  output.
- **Observation window**: focused forest validation followed by the bounded
  cluster integration and the next operator-selected large batch.
- **Temporary calluses introduced**: none planned.

## Dependencies and Related Packages

- **Depends on**: the existing NoDb persistence contract and the three prior
  climate/batch hardening packages cited above.
- **Blocks**: reliable full-fleet Dell/HP batch execution for observed-Daymet
  `Multiple` projects.
- **Related**: batch hillslope-to-watershed task-boundary rollout; no queue-edge
  change is planned here.

## Deliverables

- Writer-attribution artifact with the pre-fix real-file reproduction.
- Minimal implementation reusing the existing climate finalization contract.
- Focused and broad validation results from forest.
- Independent correctness and security review artifacts.
- Open-wepp.org integration artifact with exact image, job, file, and output
  evidence.
- Updated canonical developer documentation if the uncovered path was omitted
  from its stated coverage.
