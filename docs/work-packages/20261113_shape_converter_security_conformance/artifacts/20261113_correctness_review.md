# Correctness review - Shape-converter security conformance

**Status**: Pending

**Reviewer**: Unassigned; must be independent of the implementation author

**Candidate revision**: Not yet available

## User-Visible Acceptance

Valid uploads must retain the same selected dataset, feature/property values,
geometry types and coordinates, CRS behavior, bounds, warnings, filenames,
content types, and GeoJSON/GeoParquet semantics. Invalid uploads must fail before
publishing a partial or stale output and must preserve canonical error behavior.

## Required Evidence Chain

- Exact upload/option intent and selected dataset.
- IPC content hash plus schema parse from a disposable request root.
- Readback of the exact generated GeoJSON/GeoParquet response artifact.
- Parsed semantic comparison across valid controls.
- Failure/retry/cleanup evidence for malformed and interrupted cases.
- Exact revision and container identity for environment validation.

## Findings

| ID | Severity | Finding | Disposition | Evidence |
| --- | --- | --- | --- | --- |
| Pending | Pending | Review not yet performed. | Open | N/A |

## Gate

**Decision**: Not reviewed. File existence, HTTP success, or job completion alone
does not establish correctness.
