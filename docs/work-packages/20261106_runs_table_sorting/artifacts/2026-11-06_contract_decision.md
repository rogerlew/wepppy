# RUNS-TABLE-02 contract decision

## Authority, discrepancy and scope

Base revision: `cd4e44a3e43d44ad4c9aff05bbc5e202b3906eb7`.
The operator explicitly requested consistent column widths with wrapped content,
repeatable Automatic deletion asc/desc sorting after Creation date, disabled
runs always last, and one How to keep your project link at the top of Table.
Session authority to commit this feature's scoped work was already granted.
Sort reversal/clickability are conformance repairs. Layout, help placement and
explicit unknown-before-disabled ordering refine intended presentation.

## Canonical authority

Amend `docs/ui-docs/contracts/runs-catalog-ttl-deletion-contract.md`, Presentation
Contract. Preserve `project-ttl-control-contract.md`, shared controller contract,
CSRF/request/response contracts, and run-catalog-projection-contract. The latter's
null-last requirement remains satisfied; no projection activation or schema change.

## Normative delta and rationale

Use stable column widths for a fixed viewport and wrap cell/header text rather
than allowing row content to change widths. Keep the existing horizontal overflow
container on narrow displays. Show the existing same-origin help URL exactly once
at the top of Table, not in each row. Keep sort controls clickable when switching
columns and repeatedly toggling. For expiration sort, order dated active rows
chronologically in requested direction, unknown dates next, and confirmed-disabled
rows last, independently of direction. Other sort columns keep their own ordering.
This removes visual movement/clutter and lets users consistently find upcoming
expirations without protected runs moving to the top on reverse sort.

## Compatibility, safety and evidence

No schema, formula, TTL mutation or auth change. Preserve ordinary/admin alias
scope, existing bulk protection, pagination and safe text/URL rendering. Empty
and unknown/legacy metadata remain visible; disabled dates are never treated as
active expiration. No fallback or new dependency. Security high by catalog-route
classification; final read-only correctness/security review required.

Reproduce actual pointer hit targets and navigation in Chromium with real styles,
long labels/configs, mixed known/unknown/disabled dates, repeated clicks and switching
from creation sort. Verify full-catalog ordering before paging, both directions,
keyboard activation, stable measured widths after sort/filter/page changes, and
one help link in table panel. Retain scope/no-read ordering and bulk-action tests.
Focused Python/Jest, full frontend, docs lint and broad Python checks provide
regression evidence; no production deployment is implied.

## Reviews

Both independent reviews passed; see [review disposition](2026-11-06_contract_reviews.md).
Implementation edits wait for the accepted checkpoint ancestor. No changed files outside this package are included.
