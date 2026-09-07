# Contract decision: MOFE mapping lookup

**Date**: 2026-09-07 19:26 UTC  
**Starting revision**: 83ae87a2e6c31a73866c28a4c9d63b1c7f95af29

## Approval and normative delta

Operator instruction: "scaffold and execute work-package to make mofe mapping-aware lookup". This approves semantic lookup using the active mapping after diagnosis of hardcoded disturbed IDs in a c3s-disturbed run. Create docs/schemas/disturbed-mofe-mapping-contract.md; retain docs/schemas/nodb-persistence-concurrency-contract.md unchanged.

## Classification, rationale, and compatibility

Confirmed implementation defect; existing documentation did not provide a canonical MOFE mapping contract, so establish it before code. Resolve semantic targets through the existing effective-map lookup. Preserve severity, vegetation eligibility, flags, schema, and rebuild timing. Do not add numeric offsets or legacy fallback. No parameterization delta or security impact.

## Regression evidence proposed

Real disturbed/C3S/custom map lookup, all three severities and vegetation buckets, no SBS, empty OFE assignments, incomplete maps before mutation, immediate/deferred rebuilds, and generated management output. Scope matrix and independent review disposition follow before implementation.

## Independent reviews

Review A (/root/contract_review_a): approved; clarified that existing MOFE flags do not gate eligible shrub/grass remapping. Review B (/root/contract_review_b): approved after adding separate state/input matrices and error policy references. No unresolved findings. Both reviews were read-only and independent of the author. Standalone ancestor commit follows.

## Valid-state matrix

| State | Required outcome | Error policy |
| --- | --- | --- |
| SBS absent, mapping absent/unusable | No-op, no lookup or assignments | Expected absence; no exception |
| SBS present, complete map, empty OFE dictionary | Remains empty; preserve rebuild scheduling | Valid empty state |
| SBS present, populated C3S or custom map | Resolve semantic IDs from effective map | Valid populated state |
| SBS present, legacy disturbed map | Existing IDs remain identical | Supported legacy state |
| SBS present, incomplete semantic map | Lookup assertion before assignment mutation | Exceptional configuration; mapping resolution contract |
| SBS present, malformed or missing explicit custom map | Existing load/custom-map error propagates | Exceptional configuration; state and persistence contract |
| Already-burned assignments from failed build | Rebuild baseline before retry | Recovery contract; no in-place translation |

Policy citations: docs/schemas/disturbed-mofe-mapping-contract.md sections Mapping resolution, State and persistence, and Rationale and recovery. Existing malformed-map failures are retained; no fallback or new error wrapper is added.

## Input matrix

Independently cover severity 131/132/133 and non-burn 130, forest/shrub/short grass/tall grass/ineligible classes, built-in/C3S/custom namespaces, and immediate/deferred rebuild. MOFE burn flags retain their existing ignored behavior, including false values. Tests target these dimensions without claiming exhaustive cross-product coverage.
