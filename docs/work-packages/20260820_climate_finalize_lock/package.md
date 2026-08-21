# Climate Multiple-Build Finalize Lock

**Status**: Implementation and validation complete; CWD validation follow-up resolved; canary pending separate authorization (2026-08-21)
**Timezone**: UTC

## Overview

Harden the GridMET and Daymet multiple-interpolated climate builders against
legitimate concurrent rewrites of `climate.nodb`. The change will preserve the
strict stale-write guard while moving expensive collection outside the NoDb
critical section and finalizing derived results against freshly loaded state.

## Objectives

- Introduce an explicit collect-then-finalize lock pattern for NoDb mutation.
- Apply the pattern to both multiple-interpolated climate build paths.
- Reject finalization when relevant climate inputs changed during collection.
- Preserve unrelated concurrent state when relevant inputs did not change.
- Add deterministic regression coverage for the observed same-size rewrite.

## Scope

### Included

- A narrowly scoped refresh-on-finalize helper or equivalent explicit pattern.
- GridMET and Daymet multiple-interpolated climate collection/finalization.
- Input comparison limited to values that determine generated climate outputs.
- Focused concurrency, failure, and backward-compatibility tests.
- Updates to the canonical NoDb concurrency contract and NoDb operator docs if
  the accepted contract checkpoint requires them.

### Explicitly Out of Scope

- Disabling or weakening `NoDbStaleWriteError`.
- Generic automatic object merging.
- Artifact-generation manifests, resumable builds, or generation directories.
- Queue topology, UI workflow, climate parameter defaults, or output formats.
- Deployment to production or the openWEPP Kubernetes canary.

## Scope Boundary

Fix the confirmed long-lived stale Climate mutation without redesigning climate
orchestration or persistence generally.

## Stakeholders

- **Primary**: WEPPcloud operators and users building spatial climates.
- **Reviewers**: NoDb maintainer, climate-path reviewer, correctness reviewer.
- **Security Reviewer**: Independent reviewer for worker, subprocess, file, and
  concurrency boundaries.
- **Informed**: openWEPP canary operator.

## Success Criteria

- [x] Expensive interpolation and CLIGEN work executes without holding the
  Climate NoDb lock.
- [x] Finalization reloads durable state under lock and performs one bounded
  controller mutation.
- [x] An unrelated same-size rewrite is preserved and finalization succeeds.
- [x] A relevant climate-input change produces an explicit superseded/conflict
  result without overwriting newer state.
- [x] GridMET and Daymet multiple-interpolated paths have parity coverage.
- [x] Existing generated filenames and controller output fields remain
  compatible.
- [x] Required focused, environment-qualified repository, correctness, QA, and security gates pass.

The unfiltered repository suite was attempted. Docker Compose v2 is unavailable
in the runner's Docker CLI, so the canary contract test now explicitly skips
with an environment reason. An order-sensitive CWD leak previously made the
Topanga test report a false missing-fixture error; the CWD/fixture follow-up
now passes in the failing order with `25 passed, 1 skipped`. The prior
repository sweep excluding the Docker smoke test completed with `6087 passed,
61 skipped`.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes — Roger Lew selected the finalize-lock
  scope on 2026-08-21; Codex is the planned implementer.

## Dependencies

### Prerequisites

- Ratify the contract checkpoint for refresh-on-finalize semantics before
  production implementation edits.
- Preserve `docs/schemas/nodb-persistence-concurrency-contract.md` as canonical
  authority.

### Blocks

- Reliable continuation of openWEPP multiple-interpolated climate canary tests.

## Related Packages

- **Related**: [`20260805_culvert_nodb_writer_hardening`](../20260805_culvert_nodb_writer_hardening/package.md)
  uses fresh-state finalization while retaining stale-write enforcement.
- **Related standard**:
  [`hardening-lifecycle-standard.md`](../../standards/hardening-lifecycle-standard.md).

## Timeline Estimate

- **Expected duration**: 1-2 focused sessions plus review and canary observation
- **Complexity**: Medium
- **Risk level**: Medium-High

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package changes worker subprocess orchestration,
  run-tree writes, and concurrency ownership, which are high-impact surfaces
  under repository governance even though it adds no new public endpoint.
- **Security review artifact**:
  [`artifacts/2026-08-21_security_review.md`](artifacts/2026-08-21_security_review.md)
- **QA review artifact**:
  [`artifacts/2026-08-21_qa_review.md`](artifacts/2026-08-21_qa_review.md)

## Hardening and Callus Softening

- **Failure signature**: `NoDbStaleWriteError: stale NoDb write rejected` for
  `/wc1/runs/ma/manly-systematization/climate.nodb`, expected mtime
  `1787285526.3880107`, observed mtime `1787285597.046286`, both size `11334`.
- **Impact**: Job `a2d23f26-8386-433a-9df7-d5f3a03c8d96` completed its
  expensive GridMET/CLIGEN work but failed its final controller dump.
- **Related prior hardening**: The culvert package established fresh-state,
  finalizer-owned mutation without weakening generation checks; this package
  adapts that precedent to Climate-derived fields.
- **Hypothesis**: If collection returns derived results and finalization
  rehydrates under a short lock, unrelated concurrent rewrites will no longer
  discard completed builds while relevant input changes remain protected.
- **Health signals**: exact interleaving regression passes; no recurrence of
  this stale-write signature in multiple-climate canary jobs; no lost unrelated
  state.
- **Danger signals**: automatic field merging, stale-object dump retries,
  longer lock duration, silent acceptance of changed climate inputs, or drift
  between GridMET and Daymet behavior.
- **Observation window**: 14 days after canary deployment.
- **Temporary calluses introduced**: none planned; bounded conflict handling
  must be part of the explicit finalization transaction.

## References

- `docs/schemas/nodb-persistence-concurrency-contract.md`
- `wepppy/nodb/base.py`
- `wepppy/nodb/core/climate.py`
- `wepppy/nodb/core/climate_gridmet_multiple_build_service.py`
- `wepppy/nodb/core/climate_build_helpers.py`
- `wepppy/rq/project_rq.py`
- `wepppy/nodb/mods/omni/omni_run_orchestration_service.py`
- `tests/nodb/test_climate_gridmet_multiple_build_service.py`
- `tests/nodb/test_climate_build_helpers.py`
- `tests/nodb/mods/test_omni_run_orchestration_service.py`
- `tests/wepp/peakflow_census/test_peakflow_census.py`

## Deliverables

- Contract checkpoint and implementation PR.
- GridMET and Daymet finalization regressions.
- Completed correctness, QA, and security review artifacts.
- Canary evidence and rollback notes (follow-up; deployment was not authorized by this execution).

## Follow-up Work

- Writer-attribution logging may be proposed separately if the finalize pattern
  does not make future conflicts sufficiently diagnosable.
