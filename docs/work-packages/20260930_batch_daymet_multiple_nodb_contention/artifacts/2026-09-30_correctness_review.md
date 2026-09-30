# Correctness Review - Batch Daymet Multiple NoDb Contention

**Status**: Pending independent review
**Review target**: candidate revision TBD
**Environment evidence**: forest validation plus open-wepp.org file integration

## User Goal

Observed-Daymet batch leaves using `ClimateSpatialMode.Multiple` complete under
multi-worker execution without stale controller overwrites, while preserving
valid concurrent edits and scientifically equivalent generated climate inputs.

## Required State Matrix

Review the absent, empty, populated, supported legacy, malformed, relevant-edit,
unrelated-edit, duplicate-execution, collection-failure, and finalization-failure
states separately. Record the exact fixture and outcome for each state; do not
claim exhaustive coverage from a broad test count.

## Required Evidence

- Pre-fix real-file reproduction of the incident signature.
- Direct unmocked serializer/finalizer interleaving.
- Fresh `climate.nodb` reload through the normal reader.
- Semantic parsing of generated climate intermediates.
- Readback of the exact input consumed downstream.
- Proof that the actual batch path is wired to the correction.
- Forest test results and exact open-wepp.org revision/image/job evidence.

## Findings

Pending.

## Disposition

Pending. Package closure requires no unresolved medium or high correctness
findings and completion language bounded by the retained evidence.
