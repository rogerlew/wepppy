# DOM-12 Observed UI Contract

**Status**: Closed 2026-07-28 UTC
**Package ID**: DOM-12
**Parent**: `20260716_pure_ui_contract_standardization_c`

## Purpose and Outcome

DOM-12 proves observed CSV/model-source form values reach model-fit submission
and its lifecycle. The audit found that the shared radio macro ignores a
`checked` option key, so saved SWAT selection did not render as selected.
`observed_pure.htm` now supplies the macro's canonical `selected` key; the
actual-render regression and existing browser/route tests pass.
