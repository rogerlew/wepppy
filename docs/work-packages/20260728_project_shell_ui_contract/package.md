# DOM-02 Project Shell UI Contract

**Status**: Closed 2026-07-28 UTC
**Package ID**: DOM-02
**Parent**: `20260716_pure_ui_contract_standardization_c`

## Outcome

Actual header rendering now proves project name/scenario fields, module toggles,
and persisted readonly/public/TTL states. Existing Project controller and route
tests cover debounced mutations, authorization, queue submission, and feature
gates. No production repair was needed.

## Bounded SURF-14A Amendment

SURF-14A resolves authenticated account defaults only at included canonical
new-project creation boundaries, before `Ron` initializes DOM-02 run state.
Existing/shared runs never consult the viewer account, and preference lookup
failure cannot register or leave a usable partial run. See
`../20260729_user_preferences_wbt_boundary/`. DOM-02's Project shell,
authorization, and later mutation contracts are otherwise unchanged.
