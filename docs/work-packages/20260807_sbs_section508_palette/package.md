# SBS USGS Section 508 Palette Adoption

**Status**: In progress — checkpoint review pending  
**Timezone**: UTC  
**Package ID**: SBS-A11Y-01

## Overview

Adopt the current interagency Burn Severity Portal palette for soil burn
severity (SBS) maps and legends without client-side color shifting. The
canonical display/export colors are teal `#008080` for unchanged/unburned,
cyan `#52CCCC` for low severity, yellow `#FFE820` for moderate severity, dark
red `#A80000` for high severity, and white `#FFFFFF` for
masked/unmappable cells.

The work covers the run-page map, GL Dashboard, SBS raster export and color
table ingestion, tests, technical documentation, and the public accessibility
statement. Existing SBS rasters using earlier recognized palettes remain
readable; the new palette becomes the single default for newly rendered and
exported artifacts.

## Objectives

- Render matching canonical colors in SBS imagery, legends, and tooltips on
  the run page and GL Dashboard.
- Remove the user-facing standard/shifted palette choice and the per-pixel
  display recoloring path after the canonical palette is wired end to end.
- Recognize exact current USGS RGB color-table entries during Python and Rust
  SBS classification while preserving historical recognized RGB entries.
- Keep categorical class values `130` through `133` and existing model
  semantics unchanged; this is a palette and recognition change, not a burn
  severity formula change.
- Make the legend understandable without color alone through persistent class
  names and a distinguishable masked/unmappable treatment.
- Document the bounded accessibility improvement on the user-facing
  accessibility page without claiming that palette adoption alone establishes
  Section 508 or WCAG conformance.

## Included Scope

- Run-page SBS overlay and legend in
  `wepppy/weppcloud/controllers_js/map_gl_shared.js` and
  `wepppy/weppcloud/controllers_js/map_gl.js`, including removal of the color
  shift control from its owning template and state contract.
- GL Dashboard SBS rendering, legend, tooltip, and state in
  `wepppy/weppcloud/static/js/gl-dashboard/map/layers.js`,
  `layers/renderer.js`, `state.js`, the live bootstrap in
  `wepppy/weppcloud/static/js/gl-dashboard.js`, and the toggle markup in
  `wepppy/weppcloud/templates/gl_dashboard.htm`.
- Canonical export palette and exact color-table classification in
  `wepppy/nodb/mods/baer/sbs_map.py` and
  `wepppy/nodb/mods/baer/data/sbs_color_map.json`.
- Mask-aware coverage consumption in
  `wepppy/nodb/mods/baer/baer.py` and
  `wepppy/nodb/mods/disturbed/disturbed.py`.
- Parity changes in the `wepppyo3.sbs_map` implementation consumed by the
  Python fast path, or proof that the shared JSON alone provides parity.
- Regression fixtures covering indexed GeoTIFF color tables, alpha channels,
  current colors, historical colors, white masked entries, unknown colors,
  export color tables, legends, imagery, and tooltips.
- Updates to `docs/ui-docs/map-specification-and-behavior.md`,
  `docs/ui-docs/gl-dashboard.md`, BAER SBS documentation, accessibility
  evidence, and
  `wepppy/weppcloud/routes/usersum/weppcloud/accessibility-statement.md`.
- Proposed `docs/adrs/ADR-0041-sbs-usgs-section508-palette.md`, which must be
  accepted before implementation.

## Explicitly Out of Scope

- Changing numeric SBS class thresholds, erosion parameters, or WEPP model
  behavior.
- Reclassifying existing categorical raster pixels solely to rewrite their
  color tables.
- Treating an arbitrary near-match RGB value as a class. Recognition remains
  exact unless the ADR is explicitly amended with measured evidence.
- Claiming full Section 508 or WCAG conformance from palette selection alone.

## Compatibility and Regression Plan

The internal categorical contract remains `130` unchanged/unburned, `131`
low, `132` moderate, `133` high, and `255` NoData in normalized artifacts.
Current USGS and all already supported historical RGB values map additively to
those classes. Unknown color-table entries stay explicit unknowns and must not
be silently coerced. The implementation must verify Python/Rust parity and
inspect a generated four-class GeoTIFF to prove its pixel values, NoData value,
alpha, and color table. Existing representative legacy-palette fixtures must
continue to classify identically.

Exact white is recognized separately as a source NoData color-table entry; it
is not encoded as a fifth severity string in the shared JSON. Model-facing
`data`, class maps, and landuse apply their existing NoData/off-map fallback to
class `130`; coverage excludes masked cells. Exact-white entries previously
treated as unknown intentionally move onto those established NoData paths, so
representative generated run artifacts must be compared. The public four-class
export keeps the separate
`0..3 + 255` interchange domain and writes source NoData as `255` with alpha
zero. Tests must prove both domains and mixed-version JSON compatibility.

## Decision Gates

1. Accept ADR-0041 and its exact class/color/compatibility contract.
2. Preserve the approved masked/unmappable treatment: value `255`/NoData is
   transparent on maps, while legends show a labeled white swatch with a dark
   border. Opaque white map pixels must not be mistaken for an unburned class.
3. Complete the contract-first decision artifact and two independent reviews
   before UI-coupled NoDb or production UI edits.
4. Confirm the Rust fast path consumes the same canonical mapping and cannot
   disagree with Python.

## Success Criteria

- [ ] Run-page and GL Dashboard SBS imagery, legends, and tooltips use the five
  canonical colors and labels with no color-shift toggle.
- [ ] Current USGS indexed color tables classify four severity entries and
  recognize exact-white as source NoData. Export/display preserve NoData `255`
  and transparency; model-facing consumers retain the class-`130` fallback.
- [ ] Historical supported palettes retain classification parity.
- [ ] Newly exported SBS rasters contain the canonical RGBA table and preserve
  categorical pixel values.
- [ ] Automated tests cover maps and parsers; keyboard, zoom, color-independent
  identification, light/dark basemap, and screen-reader spot checks are
  captured as accessibility evidence.
- [ ] The public accessibility statement names the improvement and its limits.
- [ ] ADR, map specifications, GL Dashboard docs, BAER docs, and relevant user
  guidance agree on one canonical contract.

## Parameterization ADR Gate

- **Parameterization change present**: yes; display/export RGB values and RGB
  recognition rules change.
- **ADR required**: yes, `docs/adrs/ADR-0041-sbs-usgs-section508-palette.md`.
- **Status**: Accepted 2026-08-07; implementation remains blocked until the
  contract checkpoint is independently reviewed and committed.

## Security Impact and Review Gate

- **Security impact triage**: `high` by inherited DOM-23 owner rule.
- **Dedicated security review required**: yes.
- **Rationale**: the actual delta changes palette metadata and existing raster
  interpretation without changing authentication, authorization, upload
  limits, or path resolution. The higher rating is retained because the
  composed DOM-23 owner includes upload/file handling.

## References

- [RAVG FAQs](https://burnseverity.cr.usgs.gov/ravg/faqs)
- `docs/standards/contract-first-change-standard.md`
- `docs/standards/parameterization-adr-standard.md`
- `docs/ui-docs/accessiblity.md`
- `docs/ui-docs/map-specification-and-behavior.md`
- `wepppy/nodb/mods/baer/README.sbs_map.md`
- `prompts/active/sbs_section508_palette_execplan.md`
