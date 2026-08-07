# Tracker - SBS USGS Section 508 Palette Adoption

## Quick Status

**Timezone**: UTC  
**Started**: 2026-08-07 15:17 UTC  
**Current phase**: Standalone checkpoint commit  
**Last updated**: 2026-08-07 15:25 UTC  
**Next milestone**: Commit checkpoint, then implement raster semantics  
**Security impact**: `high` by inherited DOM-23 owner rule

## Task Board

### Ready / Backlog

- [ ] Validate the source inventory and identify the owning run-page template
  for the color-shift control.
- [x] Finalize and accept ADR-0041; masked/unmappable rendering is resolved.
- [x] Write and independently review the contract decision artifact.
- [ ] Implement shared palette/export/ingestion behavior and Rust parity.
- [ ] Update the run page and GL Dashboard, then remove obsolete shift state.
- [ ] Update public, user, operator, and developer accessibility documentation.
- [ ] Run focused, full, frontend, visual, and accessibility validation.

### In Progress

- None.

### Blocked

- Production implementation is blocked on ADR and contract acceptance.

### Done

- [x] Scaffolded package, tracker, proposed ADR, and active ExecPlan
  (2026-08-07 UTC).
- [x] Verified the official current RGB values against the RAVG FAQ and mapped
  the primary Python, run-page, GL Dashboard, documentation, and test surfaces
  (2026-08-07 UTC).
- [x] Registered SBS-A11Y-01, accepted ADR-0041, amended DOM-04B/DOM-23
  matrices, and drafted the contract/security checkpoint (2026-08-07 UTC).
- [x] Dispositioned all governance and ops/security findings; both independent
  post-fix reviews passed with no remaining high/medium findings
  (2026-08-07 UTC).

## Decisions Log

### 2026-08-07 UTC: Additive input compatibility

**Decision**: Plan for exact recognition of both the current USGS palette and
already supported historical palettes, with canonical USGS colors on new
exports and displays.

**Impact**: Existing uploaded SBS maps remain usable while the UI no longer
needs a display-time color-shift mode.

### 2026-08-07 UTC: Accessibility claim boundary

**Decision**: Update the public accessibility page with a factual feature note
and retain the existing ACR/VPAT and conformance caveats.

**Impact**: Users learn about the CVD-friendly palette without an unsupported
claim that color selection alone provides compliance.

### 2026-08-07 UTC: Transparent masked/unmappable pixels

**Decision**: Preserve masked/unmappable as value `255`/NoData and render those
pixels transparently on maps. Show a labeled white `#FFFFFF` legend swatch with
a dark boundary.

**Impact**: Masked areas reveal the basemap rather than covering it with white,
while the legend still documents the official source color and semantic class.

## Risks and Issues

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Python and Rust classify the same RGB differently | High | Shared fixture matrix and forced Python/Rust parity tests | Open |
| Transparent masked cells are confused with missing tiles | Medium | Persistent masked/unmappable legend label, bordered white swatch, and light/dark basemap review | Decision resolved; validation open |
| Removing shift state breaks saved dashboard hashes or old clients | Medium | Define ignored legacy state and test old hashes/bootstrap | Open |
| Palette-only UI still relies on color alone | Medium | Persistent text labels and manual color-independent review | Open |
| Existing rasters stop classifying | High | Preserve historical RGB lookup fixtures | Open |

## Verification Checklist

- [ ] `wctl run-pytest tests/nodb/mods/baer --maxfail=1`
- [ ] Relevant disturbed validation and route render tests pass.
- [ ] `wctl run-npm test -- map_gl`
- [ ] GL Dashboard Jest suites for renderer, layers, tooltip, and legacy state
  pass.
- [ ] GL Dashboard Playwright layer smoke passes on an SBS run.
- [ ] `wctl run-npm lint` and full frontend tests pass.
- [ ] `wctl run-pytest tests --maxfail=1` passes.
- [ ] Generated GeoTIFF inspection proves exact RGBA entries and unchanged
  categorical values.
- [ ] Axe, keyboard, 200% zoom, screen-reader label, and light/dark basemap
  evidence is captured.
- [ ] All changed Markdown passes `wctl doc-lint`.
