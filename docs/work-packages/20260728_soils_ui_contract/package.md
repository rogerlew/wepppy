# DOM-10 Soils UI Contract

**Status**: Closed 2026-07-28 UTC
**Timezone**: UTC
**Package ID**: DOM-10
**Parent**: `20260716_pure_ui_contract_standardization_c`
**Security impact**: `high` if production route, state, or queue behavior changes;
current scope is tests and documentation only

## Purpose

Audit Soil mode, selection, build-option, and lifecycle values from rendered
fields through browser serialization, route parsing, persisted Soils/Disturbed
state, queued build work, and completion hydration.

## Scope and Acceptance

The package covers `soil_pure.htm`, `soil.js`, soils Flask/RQ-engine routes,
Soils/Disturbed state, and `build_soils_rq`. Actual rendering must prove all
risk-bearing names/values/actions, and existing focused tests must prove native
mode options, boolean/version updates, enqueue, worker mutation, and reload.

## Outcome

Actual rendering now proves Soil modes, selections, options, and lifecycle
targets. Existing downstream tests conformed; no production mismatch or patch
was found.
