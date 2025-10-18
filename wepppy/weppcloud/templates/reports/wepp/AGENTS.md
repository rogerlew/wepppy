# Daily Streamflow Report Agent Notes

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Context
- The daily streamflow report renders a D3-backed focus + context chart inside `daily_streamflow_graph.htm`.
- The chart now measures width from the nearest `.wc-panel` container to avoid overflow and clamps to the viewport width.
- Hover overlays, flow areas, and precip bars share clip paths sized to the interactive region, preventing spline overshoot.

## Recent Changes
- Added responsive width measurement with resize observers and debounced rebuilds so SVG + overlay stay in sync with layout changes.
- Introduced unique clip paths for both focus and context charts; any future series should respect the same `clip-path` attributes.
- Reversed the precipitation axis (0 at top) while keeping hyetograph bars aligned and expanded the right margin to make room for the axis label.
- Axis label now positions relative to `rightMargin`; if margin changes, update the `rightMargin` constant and label offset together.

## Implementation Cues
- `getAvailableWidth()` pulls padding-less width from `.wc-panel`; adjust there if template structure changes.
- Legend toggle state persists across re-renders via `getLegendState()`. When adding legend items, ensure they have stable `id` keys.
- Tooltip creation is idempotent: agents should reuse the existing `div.d3-tooltip` element rather than appending new ones.
- Precipitation scaling uses `yP` (range `[0, height]`) for inverted axis; D3 bars rely on `yHyeto`/`yHyetoC` for heights, so maintain those parallel scales.

## Testing Tips
- Hard refresh the report after template changes to clear cached scripts.
- Verify no horizontal scrollbar appears at the document level.
- Resize the viewport and toggle legend items to confirm clip paths and rebuild flow.
- Confirm right-axis ticks remain legible and the label stays clear of bars after margin tweaks.
