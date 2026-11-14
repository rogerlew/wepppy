# Code review - Shape-converter security conformance

**Status**: Pending

**Reviewer**: Unassigned; must be independent of the implementation author

**Candidate revision**: Not yet available

## Review Scope

- Data-only IPC encoder, decoder, schema, bounds, and error handling.
- Archive normalization, collision, compression, and dataset-selection changes.
- Exact driver assertion and semantic validators.
- Sandbox command construction, identity, mounts, environment, process lifecycle,
  cancellation, cleanup, and readiness attestation.
- Changed container/Compose configuration and the absence of a GDAL upgrade.

## Required Checks

- No executable or object-capable decoder remains on worker-controlled bytes.
- Validation occurs before Shapely, CRS, dataframe, or output construction.
- No permissive sandbox fallback, privilege expansion, or unbounded output exists.
- API/error/output behavior remains backward-compatible for valid requests.
- The implementation stays within the package complexity budget.

## Findings

| ID | Severity | Finding | Disposition | Evidence |
| --- | --- | --- | --- | --- |
| Pending | Pending | Review not yet performed. | Open | N/A |

## Gate

**Decision**: Not reviewed. Critical/High findings must be closed; Medium findings
require owner, rationale, target date, and operator acceptance.
