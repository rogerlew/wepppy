# Map Layers and Feature UI Contract

**Status**: Closed 2026-07-28 UTC
**Timezone**: UTC
**Package ID**: DOM-04B
**Parent**: `20260716_pure_ui_contract_standardization_c`
**Security impact**: `none` for current test/documentation scope; re-triage if
a production change reaches a remote resource or public file route

## Purpose

Audit Map layer, scale, legend, and feature presentation behavior from the
actual Map template through the four map helper modules. Users must receive
the intended default layer controls, accessible layer/feature UI, and clear
legend state without a rendered-template/helper mismatch.

## Scope

The audit covers the layer, scale, feature, and shared Map helpers plus the
rendered SBS color-shift control, subcatchment colormap options, and legend
hosts in `map_pure_gl.htm`. DOM-04A owns navigation/search/elevation/drilldown.
Remote resource protocols, external map services, and changing any route or
file-serving behavior are excluded unless a direct regression proves a mismatch.

## Acceptance

- Actual-render tests prove risk-bearing layer/legend controls and default
  state.
- Focused Map Jest tests prove layer/scale/feature behavior and accessibility.
- Any production repair is minimal and re-triaged for route/resource risk.

## Decision

The operator authorized DOM-04B on 2026-07-28 as the direct, low-risk follow-up
to DOM-04A. Use direct assertions and existing tests; create no helper,
registry, or enforcement mechanism.

## Outcome

The audit added an actual-render regression for layer defaults and legend hosts.
Existing Map Jest coverage already conformed for layer order, SBS presentation,
scale behavior, and feature-modal accessibility. No production source changed.
