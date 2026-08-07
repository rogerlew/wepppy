# Adopt the canonical USGS SBS accessibility palette end to end

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current, and update
this plan and the package tracker at every stopping point.

## Purpose / Big Picture

After this work, users see the same current interagency burn-severity colors in
the non-shifted run-page map, GL Dashboard, legends, tooltips, and explicit
`export_palette="legacy"` SBS exports. Uploaded indexed rasters using those colors classify correctly, while
older supported palettes remain compatible. The application continues to
offer its optional color-shifted display while the non-shifted display adopts
the current interagency colors.

## Progress

- [x] (2026-08-07 UTC) Verified official palette values and inventoried the
  primary implementation surfaces.
- [x] (2026-08-07 UTC) Scaffolded package, tracker, proposed ADR, and this plan.
- [x] (2026-08-07 UTC) Accepted corrected ADR-0041 and checkpoint with two reviews.
- [x] (2026-08-07 UTC) Implemented parser/export parity across Python and Rust.
- [x] (2026-08-07 UTC) Implemented the run-page and GL Dashboard UI contract.
- [x] (2026-08-07 UTC) Updated public accessibility and supporting documentation.
- [x] (2026-08-07 UTC) Completed automated and generated-artifact validation;
  recorded the external Playwright target limitation for manual/visual evidence.

## Surprises & Discoveries

- Observation: the current application has two different display palettes and
  performs per-pixel browser recoloring when the shifted option is enabled.
  Evidence: `map_gl_shared.js` and GL Dashboard `map/layers.js` each define a
  standard-to-shifted RGB mapping.
- Observation: the SBS parser already accepts several historical and shifted
  RGB variants through a shared JSON file used by Python and passed to the Rust
  fast path. Evidence: `sbs_map.py` passes `sbs_color_map.json` to each
  `wepppyo3.sbs_map` operation.
- Observation: masked white currently appears in export tables as transparent
  NoData, but it is absent from the semantic RGB lookup. Its display and
  ingestion meanings must therefore be decided explicitly.

## Decision Log

- Decision: new displays and exports use exactly `#008080`, `#52CCCC`,
  `#FFE820`, `#A80000`, and `#FFFFFF` as the canonical palette.
  Rationale: these are the current values published by the interagency Burn
  Severity Portal and explicitly requested by the operator.
  Date/Author: 2026-08-07, Roger Lew / Codex.
- Decision: retain exact historical RGB recognition and browser display-time
  color shifting; update only the non-shifted palette.
  Rationale: removing the optional shifted view is outside the requested scope.
  Date/Author: 2026-08-07, Codex proposal; ADR acceptance pending.
- Decision: update the public accessibility statement conservatively.
  Rationale: the palette is a meaningful CVD-friendly improvement, but color
  choice alone does not prove Section 508 or WCAG conformance.
  Date/Author: 2026-08-07, operator direction / Codex.
- Decision: masked/unmappable value `255`/NoData renders transparently on maps;
  legends use a labeled white swatch with a dark boundary.
  Rationale: transparent pixels reveal useful basemap context, while the
  bordered swatch records the official white source color without disappearing
  on a light legend surface.
  Date/Author: 2026-08-07, Roger Lew.

## Outcomes & Retrospective

The corrected implementation preserves both shifted modes and changes only the
non-shifted palette. Native, explicit, inferred, exact-white, and Int16 NoData
now agree across model fallback, coverage, web alpha, and interchange export.
Full Python/frontend gates and corrective independent reviews passed. Targeted
Playwright could not reach a run page containing `#mapid` on the configured
external target, so manual visual evidence remains a release-environment check.

## Context and Orientation

SBS is a categorical raster used to assign unchanged/unburned, low, moderate,
and high burn classes. Normalized WEPPcloud raster values are `130`, `131`,
`132`, and `133`; `255` is NoData. `wepppy/nodb/mods/baer/sbs_map.py` reads
indexed raster color tables and exports normalized maps. Its
`data/sbs_color_map.json` is also supplied to the optional Rust fast path in
`wepppyo3`.

The main run page renders SBS through
`wepppy/weppcloud/controllers_js/map_gl.js`, with palette and legend helpers in
`map_gl_shared.js`. GL Dashboard independently renders the SBS canvas and
tooltip in `static/js/gl-dashboard/map/layers.js` and its legend in
`layers/renderer.js`. Both carry standard/shifted state that must remain in
sync. The public accessibility statement is
`wepppy/weppcloud/routes/usersum/weppcloud/accessibility-statement.md`.

## Plan of Work

Milestone 1 ratifies behavior before implementation. Complete a contract
decision artifact under this package, identify the applicable canonical UI
contract owner, update all applicable canonical contracts, obtain explicit
operator approval and two independent reviews, and commit that checkpoint as a
standalone ancestor. Accept ADR-0041 in the same checkpoint. Resolve masked
white as value `255`/NoData with transparent map rendering and a labeled,
dark-bordered white legend swatch, and preserve saved `shifted` state.

Milestone 2 establishes one palette contract in raster processing. Add the
current exact RGB triplets to `sbs_color_map.json`, retain existing triplets,
and update the canonical export color table in `sbs_map.py`. Keep JSON limited
to the established four severity names. Detect exact-white color-table entries
separately in Python and add their palette indices to source `nodata_vals`.
Model-facing data/class/landuse behavior continues mapping source NoData/off-map
to class `130`, while coverage excludes those cells. Exact-white entries
previously classified as unknown intentionally adopt that established NoData
behavior; compare downstream generated landuse/model artifacts for a
representative fixture. Four-class interchange export instead preserves source
NoData as `255` with alpha zero. Verify whether `wepppyo3` needs code changes; tests
must run the same fixtures through Rust and forced-Python paths, including
missing/corrupt JSON fallback parity and mixed-version JSON parsing. Do not
introduce approximate RGB matching.

Add a source-validity mask property to `SoilBurnSeverityMap` before normalized
data loses the distinction between true unburned and model-fallback NoData.
Update both BAER and Disturbed coverage calculators to intersect that mask with
the watershed boundary. When no eligible pixels remain, store zero for all four
coverage fractions; retain the existing no-SBS default separately. Test mixed
and all-masked inputs and their generated summaries.

Milestone 3 updates only non-shifted client rendering. Retain both run-page
legend arrays, the toggle, shifted canvas behavior, and persisted state. Make
the equivalent non-shifted color changes to GL Dashboard imagery, legends, and
tooltips while preserving its shifted mode.
Labels remain visible so class meaning is not conveyed by color alone. Give
the masked white swatch a dark visible boundary while keeping its map pixels
transparent.

Milestone 4 updates documentation and evidence. Amend map and GL Dashboard
specifications, BAER SBS input/export documentation, relevant user guidance,
the internal accessibility evidence map, and the public accessibility
statement. State the official source and implementation scope. Do not state
that the USGS palette alone guarantees conformance.

Milestone 5 validates observable behavior. Create an indexed fixture with all
current colors and a legacy fixture. Prove class assignment, NoData handling,
exported color tables, and unchanged normalized pixel values. Exercise both
map clients and capture screenshots on light and dark basemaps. Check legend
labels with keyboard and accessibility-tree inspection, 200% zoom, and a
color-independent review. Run focused and full test gates.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    wctl run-pytest tests/nodb/mods/baer --maxfail=1
    wctl run-pytest tests/nodb/mods/disturbed/test_sbs_validation.py --maxfail=1
    wctl run-npm test -- map_gl
    wctl run-npm test
    wctl run-npm lint
    wctl run-playwright --suite full --grep "SBS|burn severity" --workers 1
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260807_sbs_section508_palette

Inspect a generated raster with `gdalinfo` or an existing repository helper and
record the five RGBA entries, NoData value, and unique categorical values in an
artifact under this package.

## Validation and Acceptance

An indexed raster using `(0,128,128)`, `(82,204,204)`, `(255,232,32)`,
`(168,0,0)`, and `(255,255,255)` must classify as unchanged, low, moderate,
high, and masked/NoData. A representative old palette must return its previous
classes. An explicit `export_palette="legacy"` raster must retain class pixels
and publish the canonical table; an export with no palette argument must retain
the existing shifted table. On both map clients, imagery, legend swatches, and tooltips
must agree in non-shifted mode and both palette-shift controls must remain. The masked legend entry
must remain perceptible on a white surface, and masked map pixels must expose
the basemap. The public accessibility page must describe this feature and
retain its conformance caveat.

## Idempotence and Recovery

Fixture generation and validation commands must be repeatable. Preserve the
old RGB lookup entries so rollback of the UI does not strand uploaded maps.
Rollback consists of reverting the canonical export/display selection while
leaving additive input recognition in place unless it is shown to misclassify
real data.

## Artifacts and Notes

Store the accepted contract, review dispositions, generated-raster inspection,
screenshots, and manual accessibility notes under this package's `artifacts/`
directory. Do not check large raster fixtures into Git when a deterministic
small test fixture can be generated at test time. All committed fixtures and
screenshots must be synthetic or redacted and contain no production raster
metadata, credentials, run identifiers, or absolute production paths.

## Interfaces and Dependencies

Use existing GDAL, NumPy, Jest, and Playwright facilities. Add no dependency.
Keep `sbs_color_map.json` as the shared exact input-recognition source consumed
by Python and Rust. Preserve the public Python functions `get_sbs_color_table`,
`ct_classify`, and `SoilBurnSeverityMap.export_4class_map`, and preserve the
run-page and GL Dashboard event and palette-toggle state contracts.

Revision note: created 2026-08-07 to capture the operator-directed USGS palette,
ADR requirement, public accessibility update, compatibility boundary, and
end-to-end validation plan. Updated 2026-08-07 to record transparent
masked/unmappable map pixels and a bordered white legend swatch.
