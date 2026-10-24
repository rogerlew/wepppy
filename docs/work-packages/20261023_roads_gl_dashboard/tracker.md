# Roads GL Dashboard tracker

## Status

2026-10-24 UTC: independent contract review and disposition complete at starting
implementation revision `5227cb25831a1f86b2a70dd977d1cdad56a236cf`. Standalone checkpoint committed as `2399f835c`. The user subsequently authorized
implementation; active plan is prompts/active/implementation_execplan.md. No
project mutation, model rerun or deployment is planned. Package date uses Pacific time; events use UTC.

## Progress

- Operator settled D1–D4 and requested a visible Baseline/Roads switch.
- Independent correctness, security and UX reviews completed.
- Nine findings accepted, corrected and independently closed; no unresolved findings.
- Canonical dashboard, output-scope and lifecycle amendments agree; ADR-0105 records display formulas/defaults.
- Documentation lint, spelling previews and diff checks pass; final hashes retained.

## Decisions

Preserve upstream mode-specific mandatory resource admission. Materialize all map
inputs within one existing shared guard using an additive view on the existing
Roads map route. Use effective prepared input_crs, literal labels and isolated
optional-layer errors. Explicitly manage incompatible map scenarios and graphs
across scope transitions. Keep modeled per-profile lengths separate and unsummed.
No new identity system, infrastructure or persisted source-schema changes.

## Review and disposition evidence

See [disposition](artifacts/review_disposition.md),
[correctness](artifacts/correctness_review.md), [security](artifacts/security_review.md)
and [UX](artifacts/ux_review.md). All approvals are specification-only. Final
reviewed-file hashes and validation are in artifacts/review_manifest.json.
The existing 39-line/34-profile inslope fixture supports source feasibility only;
mixed-profile, projected CRS, races and browser transitions require runtime tests.

## Implementation outcome

Complete locally at runtime revision `afebebcff`. Coherent HTTP view, prepared
centerline renderer, accessible details/table, jet2 legend and Baseline/Roads
switch are implemented. All twelve independent implementation findings are
closed. Five feature browser tests, 1017 frontend tests and 282 final focused
Python checks pass. Actual 39-line/34-profile values and geometry agree with
source artifacts. Broad segmented coverage: 11764 passed, 155 skipped.

The initial scientific publication mismatch was resolved by moving the display
adapter beside the route, preserving all 94 source identities and the strict
checker. The final unrelated catalog browser check passed with the installed
browser path. General dashboard smoke fixture/scroll timing limits remain
documented in [implementation validation](artifacts/implementation_validation.md).
See [implementation disposition](artifacts/implementation_disposition.md) and
[manifest](artifacts/implementation_manifest.json) for final reviews/hashes.

No model rerun on the reported project, push or production deployment.
