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

## Next gate

Execute the implementation ExecPlan, validate actual artifacts/browser behavior,
and obtain independent implementation reviews. This review turn does not authorize deployment or
claim the new layer/switch is already available. Current canonical decisions live
outside this work package, especially the dashboard contract's Decision register,
Dashboard output-scope switch, Coherent detachment view payload, and Error
isolation and cache behavior sections. Review ExecPlan progress/outcomes updated.

## Implementation progress

Coherent view, centerline renderer, accessible details/table, numeric legend and
visible scope navigation are implemented. All ten independent implementation
findings are closed; see artifacts/implementation_disposition.md and the three
implementation review artifacts. Focused Python/render 279, frontend 1007 and three
live browser checks pass. Actual 39-line/34-profile HTTP propagation matches every
source geometry/rate without changing source hashes. Broad Python regression and
existing dashboard smoke checks remain running. No production deployment.
