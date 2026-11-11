# Contract decision - Browse filesystem output contexts

**Status**: Accepted for implementation; independent M0 reviews passed  
**Date**: 2026-11-11 UTC  
**Finding**: F3 / SEC-03  
**Canonical target**: `docs/schemas/browse-filesystem-contract.md`

## Decision

Filesystem entry names and symlink targets are data. In HTML browse pages they
must render only as text, and each entry name used in a URL must be encoded as
exactly one path segment before it is joined to a trusted route prefix. Query
values continue to use the query encoder. No filesystem-derived value may create
HTML elements, attributes, URL scheme/authority, additional path segments, or
query parameters.

The application must preserve the original filesystem name for lookup and
display semantics. The security control is contextual output encoding, not
input rejection, normalization, renaming, or hiding. Ordinary ASCII, Unicode,
punctuation, whitespace, percent signs, and separator lookalikes remain valid.

Intentional listing markup may be trusted only at a narrow renderer boundary
whose untrusted fields are all contextually encoded. A broad `Markup()` or
template `safe` operation around strings assembled from raw filesystem metadata
does not satisfy the contract.

## Context Rules

| Value | Output context | Required treatment |
| --- | --- | --- |
| Filename/directory label | HTML text | HTML escape |
| Symlink target display | HTML text | HTML escape |
| Filename/directory in route | URL path segment | Percent-encode once with no filename-safe separators |
| Filter, diff, page, sort, Parquet filter | Query value | Existing `urlencode` composition |
| Copy-path attribute | HTML attribute | Attribute escape; preserve copied text |
| Static renderer markup | HTML structure | Literal template/renderer output only |

## Compatibility Decision

- Existing authorized files remain listable and downloadable.
- Navigation and action links keep their existing route targets and query state.
- Sorting width may be calculated from the original display string, but the
  emitted representation must be escaped.
- No auth, containment, symlink traversal, parser, or content-type rule changes.
- JSON API strings remain JSON data and are not HTML-escaped at the API layer.

## Rejected Alternatives

- **Filename allowlist**: rejected because it changes valid filesystem behavior,
  does not protect other artifact producers, and applies security in the wrong
  output context.
- **String replacement sanitizer**: rejected because HTML text, attributes, URL
  paths, and query values have different encoding rules.
- **CSP-only mitigation**: rejected as incomplete; CSP is defense in depth and
  cannot make unsafe HTML assembly correct.
- **Site-wide renderer refactor**: rejected as unnecessary expansion unless a
  focused regression proves the small boundary cannot preserve behavior.

## Acceptance Evidence

Focused route tests must create real temporary entries and prove that hostile
characters are inert, links encode one name segment, ordinary controls still
navigate, action links preserve their route/query behavior, and symlink display
text cannot form markup. The full repository suite is explicitly waived by the
operator for this package.

## Review Gate

Correctness and security reviewers must approve this decision and the
failure-class matrix before production-code edits. Any change to filename
admission, CSP, authorization, or containment requires a new scope decision.

## Authorization and checkpoint

The operator requested execution of this exact active plan on 2026-11-10
Pacific, authorizing its bounded encoding amendment and required checkpoint.
Base: `c040d51d09530dee7f1562c467b98d74c8d6c5a4`. Current authority is the
browse filesystem contract, section "Filesystem names in HTML and URLs".
No persisted schema or parameterization changes. Both independent reviews and
the accepted inventory correction are retained in the review artifacts.
