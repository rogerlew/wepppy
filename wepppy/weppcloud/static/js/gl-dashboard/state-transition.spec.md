# GL Dashboard State Transitions Spec
> Data-driven graph/slider layout state to prevent regressions from fragile imperative code.

## Goals
- Single source of truth for graph modes, slider placement, and focus per context.
- Deterministic transitions; no cascading side effects or re-entry loops.
- Easy to audit: a small definition map drives behavior and tests.

## Current Pain
- Multiple ad-hoc checks (`rapActive`, `yearlyActive`, `climateActive`, `graphModeUserOverride`) mutate DOM and state in unpredictable order.
- Event handlers (layer toggles, graph radios, slider changes, panel collapse) re-enter `activateGraphItem` and oscillate modes.
- Slider placement logic is split across CSS, `yearSlider.show`, and mode syncs.

## Proposed Architecture
### 1) Declarative Context Definition
Create a definition table keyed by `graphContext` (resolved from active graph key + data source):
```js
export const GRAPH_CONTEXT_DEFS = {
  climate_yearly: { mode: 'full', slider: 'bottom', focus: true },
  wepp_yearly:    { mode: 'split', slider: 'top', focus: false },
  rap:            { mode: 'split', slider: 'top', focus: false },
  cumulative:     { mode: 'full', slider: 'inherit', focus: true },
  omni:           { mode: 'full', slider: 'inherit', focus: true },
  default:        { mode: 'split', slider: 'hide', focus: false },
};
```
- `mode`: default graph mode if no user override.
- `slider`: `top` (slot), `bottom` (container), `inherit` (leave as-is), `hide`.
- `focus`: whether to force `graphFocus` true.

### 2) Deterministic Resolver
Add `resolveGraphContext(state)` that returns a single context key based on priority:
1. Active graph key (cumulative/omni/climate yearly).
2. Active data source (`glDashboardTimeseriesGraph._source`).
3. Visible layers (RAP/WEPP yearly) when no graph selected.

### 3) Single Sync Function
`syncGraphLayout({ userOverride })`:
- Derive `context = resolveGraphContext(state)`.
- Lookup `def = GRAPH_CONTEXT_DEFS[context] || GRAPH_CONTEXT_DEFS.default`.
- Mode = `userOverride || def.mode`.
- Apply `setGraphMode(mode, { source })`, `setGraphFocus(def.focus || mode === 'full')`.
- Call `positionYearSlider(def.slider)`:
  - `top` → move to `#gl-graph-year-slider`, remove `has-bottom-slider`.
  - `bottom` → move to `#gl-graph-container`, add `has-bottom-slider`.
- `hide` → hide/clear class.
- No DOM writes outside this function.

### 4) Event Entry Points
All entry points call `syncGraphLayout` after state changes:
- Graph radio change.
- Layer visibility toggles (RAP/WEPP yearly).
- Panel collapse/expand.
- Slider change (only data refresh, then sync).
- Graph data load completion (once).

### 5) Re-entry Guards
- Keep `activeGraphLoad = { key, promise }` and short-circuit duplicate calls.
- `syncGraphLayout` must be idempotent; no side effects besides DOM updates.

## Migration Steps
1. ✅ Implemented `GRAPH_CONTEXT_DEFS`, `resolveGraphContext`, `positionYearSlider`, `syncGraphLayout` (centralizes mode/focus/slider).
2. ✅ Refactored scattered toggles: graph radio changes, slider changes, climate mode/start radios now funnel through `syncGraphLayout`; layer selections clear overrides and collapse via shared helpers; slider placement uses `positionYearSlider`.
3. ✅ User overrides preserved but cleared on context switches; `setGraphMode` delegates to the sync helper.
4. ✅ Slider placement moved into `positionYearSlider`; CSS left unchanged.
5. ✅ Removed direct DOM graph toggles in `layers/renderer.js`; subcatchment overlays now clear graph overrides, collapse via `syncGraphLayout`, and deselect RAP/SBS/WEPP/Soils/Hillslopes consistently.

## Testing Matrix (to automate)
- WEPP Yearly → Climate Yearly → Cumulative Contribution: mode sequence `split -> full -> full`, slider `top -> bottom -> hide/inherit`, context stays stable after waits.
- RAP active (no graph) → slider top, split mode.
- Climate Yearly direct select → full + bottom slider + focus.
- Omni graphs → full, slider unchanged/hidden.
- Panel collapse/expand: no extra graph loads; mode/state unchanged except collapse.
- Map overlays (Landuse/Soils/WEPP/WATAR) -> graph minimized and slider hidden.
- Climate radios activate Climate graph even when not previously active.

## Guardrails
- All graph loads go through `activateGraphItem` with the load dedupe token.
- No mutation of `activeGraphKey` inside data refreshes unless explicitly requested.
- Year slider visibility controlled only by `positionYearSlider`.

## Deliverables
- Refactored `gl-dashboard.js` using the definition-driven sync.
- Playwright spec updates to assert mode/slider per context, plus re-entry loop guard.
- Skip RAP-dependent Playwright flows when a run lacks RAP overlays to keep the suite portable across runs.
