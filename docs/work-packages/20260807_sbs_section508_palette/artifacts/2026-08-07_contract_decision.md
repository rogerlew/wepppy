# SBS-A11Y-01 Contract Decision

**Status**: Approved by operator; independently reviewed; ready for checkpoint commit  
**Decision date**: 2026-08-07  
**Starting implementation revision**: `8c15b1c3202b937015fad66532f0389cb9a559f8`

## Authority and Ownership

This is a bounded cross-owner enhancement under
`docs/standards/contract-first-change-standard.md`. Registration ID
`SBS-A11Y-01` composes only DOM-04B Map Layers and Feature UI and DOM-23
Disturbed/BAER. It does not reopen, advance, or close either verified owner.

Applicable canonical authorities are:

- `docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/child_package_register.md`;
- `docs/work-packages/20260728_map_layers_feature_ui_contract/artifacts/field_matrix.md`;
- `docs/work-packages/20260728_disturbed_baer_ui_contract/artifacts/field_matrix.md`;
- `docs/ui-docs/controller-contract.md` for shared controller invariants; and
- `docs/adrs/ADR-0041-sbs-usgs-section508-palette.md` for palette and
  classification parameterization.

## Exact Normative Delta

1. The only canonical SBS display/export palette is unchanged/unburned
   `#008080`, low `#52CCCC`, moderate `#FFE820`, high `#A80000`, and
   masked/unmappable `#FFFFFF`.
2. Normalized categorical values remain `130`, `131`, `132`, `133`, and
   `255`/NoData respectively. Scientific thresholds and model behavior do not
   change.
3. Masked/unmappable pixels are transparent on maps. Legends expose a labeled
   white swatch with a dark boundary.
4. The run-page `#sbs_color_shift_toggle`, GL Dashboard
   `#gl-sbs-color-shift-toggle`, `sbsColorShiftEnabled` state key, per-pixel
   recoloring, and dual legends are removed from their source templates,
   bootstrap, and modules. Old `window.__GL_DASHBOARD_STATE__` payloads that
   contain `sbsColorShiftEnabled` are ignored without error.
5. Current exact RGB entries are recognized during indexed color-table
   ingestion. Existing recognized historical RGB values remain accepted.
   Unknown colors remain unknown; nearest-color matching is forbidden.
   `#FFFFFF` is not added to `sbs_color_map.json` with a fifth severity string.
   Instead, Python separately detects exact white color-table entries and adds
   their source palette indices to `nodata_vals`, preserving the existing
   four-value JSON severity schema understood by old Python and Rust versions.
6. Python and `wepppyo3` fast paths must return identical class mappings.
7. New four-class exports contain exact color-table entries `0 = (0, 128, 128,
   255)`, `1 = (82, 204, 204, 255)`, `2 = (255, 232, 32, 255)`, `3 = (168, 0,
   0, 255)`, and `255 = (255, 255, 255, 0)`. Existing raster pixels are not
   migrated merely to change presentation.
8. Class names remain visible beside swatches so meaning is not communicated by
   color alone.

## Compatibility and Data Impact

The change is additive at ingestion and canonicalizing at display/export.
Existing categorical and historical color-table rasters remain readable.
There is no NoDb schema, route payload, RQ wiring, authorization, upload-limit,
or severity-threshold change. Generated-output validation must prove exact RGBA
values, NoData `255`, and the approved downstream treatment below.

The NoData domains are intentionally distinct:

- An input color-table index whose RGB is exactly `(255, 255, 255)` is treated
  as source NoData alongside the band-declared NoData value.
- `SoilBurnSeverityMap.data`, `class_map`, `class_pixel_map`, and landuse/model
  consumers apply the established safe fallback for source NoData/off-map:
  class `130` unchanged/unburned. Exact-white palette entries previously fell
  through as unknown `255`; this package intentionally corrects them to the
  existing NoData fallback. Generated landuse/model artifacts for inputs that
  contain exact-white masked cells may therefore change from erroneous unknown
  handling to class `130` and require downstream propagation evidence.
- Coverage summaries exclude exact-white masked cells from the denominator,
  consistent with other source NoData. This is an approved correction for the
  newly recognized palette, not a promise of byte-identical summaries.
- `SoilBurnSeverityMap` exposes a source-validity mask aligned with `data` that
  is false for band-declared NoData and exact-white color-table indices before
  they normalize to model class `130`. Disturbed and BAER coverage intersect
  this mask with `watershed.bound == 1.0` before counting classes. If the
  intersection contains zero eligible cells, all four coverage fractions are
  `0.0`; the existing `sbs is None` result remains `noburn = 1.0` and the other
  classes `0.0`.
- `export_4class_map` is a presentation/interchange artifact with class indices
  `0..3` and NoData `255`. Source NoData is explicitly written as `255`, not
  passed through the model fallback or class-zero classification.
- Web display products preserve/export alpha zero for NoData, so those pixels
  reveal the basemap.

Mixed-version deploy and rollback remain safe because the shared JSON contains
only the four existing severity strings. Exact-white NoData recognition is a
Python-side additive rule and can be rolled back without making the JSON
unreadable by an old worker.

## Security Impact

Security impact is `high` by inherited owner rule because DOM-23 contains SBS
upload/file handling. The enhancement itself changes no upload, path,
authentication, authorization, queue, or network boundary. Review must confirm
that color-table processing remains bounded and does not add tolerance or
unbounded work.

## Discrepancy Classification

This is an intended behavior change, not a conformance fix. Current dual
palette/toggle behavior conforms to the earlier DOM-04B matrix and therefore
requires this checkpoint ancestor before implementation.

## Regression Evidence

- Direct render test proves the shift checkbox is absent and both legend hosts
  remain.
- Jest tests prove one palette across run-page imagery, legend, tooltip, and
  old-state bootstrap; GL Dashboard tests prove the same and explicitly ignore
  stale `window.__GL_DASHBOARD_STATE__.sbsColorShiftEnabled`.
- GDAL fixtures prove current and historical indexed color tables, alpha,
  masked NoData, unknown colors, and canonical export tables.
- BAER and Disturbed tests prove mixed valid/masked coverage, an all-masked
  in-bound raster returns four zeros without division by zero, and generated
  summaries reflect the source-validity mask.
- Forced Python and available Rust paths produce identical results.
- Missing and corrupt shared-JSON tests prove Python and Rust fallback behavior
  uses the same complete built-in four-severity palette; a corrupt explicit
  JSON path may not silently produce divergent classification.
- Synthetic fixtures and screenshots contain no production raster metadata,
  credentials, run identifiers, or absolute production paths.
- Manual evidence covers persistent labels, bordered white swatch, transparent
  map cells, keyboard/accessibility-tree inspection, 200% zoom, and light/dark
  basemaps.

## Operator Approval

Roger Lew explicitly directed adoption of the five current Burn Severity Portal
colors, inclusion of the ADR and public accessibility-page update, execution of
the work package, and transparent masked/unmappable pixels on 2026-08-07. This
approves the exact matrix above and authorizes bounded composition of DOM-04B
and DOM-23 without advancing or closing them.

## Review Gate

Both independent read-only reviews passed after every finding was dispositioned
and medium/high fixes received post-fix confirmation. Implementation remains
blocked only until this checkpoint is committed as a standalone ancestor.
