# Make the SBS color table total, and decode class in both map clients

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current, and update
this plan and the package tracker at every stopping point.

## Purpose / Big Picture

After this work, no SBS pixel is ever baked a fabricated color, unassigned
classifications are visible and countable on the map so users can catch them,
and display color is a property of the deployed client rather than of a file
written months earlier. Known historical endpoint colors are corrected without
rewriting artifacts; unrecoverable interpolated and clamped colors remain an
explicit compatibility limitation until re-validation.

## Progress

- [x] (2026-08-24) Confirmed the stale-palette defect against fetched production
  artifacts; traced the bake sites and both passthrough branches.
- [x] (2026-08-24) Revision 1 (new artifact, route, request-time regeneration)
  rejected by two independent reviews and withdrawn.
- [x] (2026-08-24) Revision 2 (client-only, closed-encoding premise) rejected;
  premise disproved and verified disproved by the author.
- [x] (2026-08-24) Located the real second defect: unassigned palette indices get
  no color-table entry and are interpolated.
- [x] (2026-08-24) Operator decided unassigned is its own state, not masked.
- [x] (2026-08-24) Sentinel selected on measured CVD evidence.
- [x] (2026-08-24) Revision 3 research and proposed ADR authored.
- [x] (2026-08-24) Scaffold cleanup removed premature edits to closed packages,
  implementation-pending production docs, and generated observability reports.
- [x] (2026-08-25) Two independent reviews of the cleaned revision completed;
  both blocked implementation on canonical registration, inherited security
  triage, compatibility contradictions, and checkpoint ancestry.
- [x] (2026-08-25) Operator established that closed work packages are transient
  history; durable governance was promoted to a current contract outside the
  package, and the standard was corrected accordingly.
- [x] (2026-08-25) Operator approved execution of the summarized compatibility
  policy; ADR-0045 and the promoted SBS contract record that decision.
- [x] (2026-08-25) Two independent post-correction reviews approved the
  checkpoint with no unresolved high/medium findings; disposition recorded.
- [x] (2026-08-25) Committed corrected checkpoint as standalone ancestor
  `f79aef8fc2290526785a478ad8c490254648d25f` and recorded it in the tracker.
- [x] (2026-08-25) Milestone 2: producer tables are total over source-valid
  values and exact GDAL lookup is enabled on both VRT paths.
- [x] (2026-08-25) Milestone 3: both clients decode all three known transport
  generations, apply either display palette, count/reset Unassigned, and expose
  decoded legend and tooltip semantics.
- [x] (2026-08-25) Milestone 4: server legends share one definition and the
  cross-client/Python parity test passes.
- [x] (2026-08-25) Milestone 5: all three real-GDAL output paths, focused
  producer/client suites, full frontend gates, docs gates, stubs, and the
  4096×4096 performance bound pass. Repository-wide Python validation passed;
  final correctness review findings were corrected and the reviewer approved
  closure with no unresolved high/medium findings.

## Surprises & Discoveries

- The display raster never contains the uploaded raster's colors.
  `gdaldem color-relief` maps source values through a table WEPPcloud writes
  itself. That is why display palettes drift independently of uploads.
- Undecodable and unassigned are the same set **in the current color-table
  branch**, but not historically. Interpolation there happens only where an index
  had no entry, and an index lacks an entry only when its severity was blank in
  the classify form. The pre-2018 writer is different: it emitted only four break
  entries while `class_map` classified every observed value, so its interpolated
  pixels were *classified*, not unassigned. Relabeling those as Unassigned is a
  deliberate compatibility loss requiring operator approval, not a recovery of
  true state.
- `gdaldem` clamps as well as interpolating. A value outside the entry range
  takes the nearest end entry's color - a legitimate severity. Those pixels are
  inside the decode domain and cannot be detected client-side; only
  re-validation repairs them. Executional evidence in
  `artifacts/2026-08-24_color_relief_behavior_probe.md`.
- Display and model already disagree on those pixels: `ct_classify` returns
  `255`/unknown while the map paints an interpolated color
  (`sbs_map.py:651-653`).
- Three bake generations exist, not two. The pre-2018 palette
  (`46,203,24` / `161,250,220` / `255,161,5` / `217,34,3`) was replaced by commit
  `126673850`. An earlier enumeration missed it by matching RGBA quadruples when
  that code wrote RGB triples.
- The pre-2018 table was sparse - four entries at the break values - so those
  artifacts contain genuinely interpolated colors between assigned classes.
- The shifted mode is accidentally correct on stale runs because
  `SBS_STANDARD_TO_SHIFTED_RGB` enumerates two generations. That also proves
  exact-RGB canvas decoding works in production.
- `Baer.write_color_table` is already total over `self.classes`, and the breaks
  branch of `_write_color_table` is total over `self.counts`. Only the
  color-table branch has the gap.
- Layer opacity multiplies per-pixel alpha (`SBS_DEFAULT_OPACITY = 0.3`), which
  is why a partial-alpha sentinel would vanish exactly when a user lowers opacity
  to inspect.
- An earlier opacity accessibility referral was withdrawn after its measurement
  mixed mutually exclusive palettes. Opacity remains unchanged and out of scope.
- `resources_baer_sbs` has no authorization decorator and never calls
  `authorize()`. Its route/auth behavior is unchanged and out of scope; any
  remediation requires a separate security-scoped package and current contract.
- Exact color relief plus a numeric NoData entry and `nv` produces an invalid
  VRT LUT in GDAL 3.10 because the generated lookup is no longer monotonic.
  NoData is therefore represented exclusively by `nv`; totality applies to the
  source-valid domain. A real VRT-to-PNG regression covers this constraint.
- The first exact-RGB implementation exceeded the benchmark ceiling because it
  allocated string keys in the per-pixel loop. Packing RGB into one integer
  reduced the slowest new path to 0.650 times the old shifted decoder median.

## Decision Log

- Decision: make the color-table branch total and pass `-exact_color_entry`.
  Rationale: removes the interpolation gap at its source, inside the render path
  that already exists.
  Date/Author: 2026-08-24, Claude Code.
- Decision: unassigned is a first-class state, distinct from masked.
  Rationale: operator - intent must not be assumed for values absent from the
  default mappings, and users validate classes on the deck.gl map, so unassigned
  must be identifiable there.
  Date/Author: 2026-08-24, Roger Lew.
- Decision: sentinel `#800098` at full per-pixel alpha.
  Rationale: worst-case CIEDE2000 `8.07` across four vision models, two
  basemaps, and two opacities - 1.5x the standard palette's own internal
  separation and 2.9x the shifted palette's. Bound by basemap visibility rather
  than palette confusability. Magenta failed at `5.39` and `#7F00FF` at `8.64`;
  partial alpha fails at low layer opacity.
  Date/Author: 2026-08-24, measured; see the sentinel analysis artifact.
- Decision: anything not in the decode domain renders as the sentinel.
  Rationale: exact for the current color-table branch; conservative degradation
  for pre-2018 artifacts, where the original severity is unrecoverable by exact
  matching. It also removes any need to trust artifact provenance, which fork and
  archive restore make unsafe. A distinct `legacy-undecodable` state was
  considered and not adopted.
  Date/Author: 2026-08-24, Claude Code; compatibility loss approved by the
  operator for execution.
- Decision: do not regenerate existing artifacts automatically.
  Rationale: known endpoint colors decode through the client, while
  interpolated and clamped historical pixels are not recoverable from RGB alone;
  re-validation corrects the file when a user re-submits classify.
  Date/Author: 2026-08-24, Claude Code.
- Decision: scope "remove the source color map" to the display path.
  Rationale: uploaded rasters carry their own palettes and are classified by that
  table; removing it breaks every upload.
  Date/Author: 2026-08-24, Claude Code proposal adopted by Roger Lew.
- Decision: emit NoData only through GDAL's `nv` color-table entry.
  Rationale: a duplicate numeric NoData entry makes exact-mode VRT LUTs invalid;
  excluding NoData preserves the intended total source-valid domain and yields
  transparent NoData in all three generated-output tests.
  Date/Author: 2026-08-25, Codex, based on executional GDAL evidence.

## Outcomes & Retrospective

The package completed without adding a route, payload, migration, or historical
artifact rewrite. Newly validated rasters now use exact, total class transport;
both clients decode all known generations and expose Unassigned rather than
passing stored RGB through. Real-GDAL coverage caught the subtle duplicate
numeric-NoData/`nv` VRT failure before closure. Packed RGB lookup made the most
expensive new decode path faster than the old shifted-only path while preserving
the source-plus-one-destination memory bound. Final validation passed 6,697
Python tests (63 skipped), 105 frontend suites / 778 tests, lint, stubs, docs,
and independent correctness review.

## Context and Orientation

SBS is a categorical raster with normalized values `130` unburned, `131` low,
`132` moderate, `133` high, `255` NoData.
`wepppy/nodb/mods/baer/sbs_map.py` owns classification and export. The display
raster `disturbed/baer.wgs.rgba.png` comes from `gdaldem color-relief` plus
`gdal_translate` over a table written by `_write_color_table` (Disturbed) or
`baer.py::write_color_table` (BAER).

The run page renders SBS through `controllers_js/map_gl.js` with helpers in
`map_gl_shared.js`; `baer.js` owns the control legend. The GL Dashboard renders
independently through `gl-dashboard/map/layers.js`, `layers/detector.js`, and
`layers/renderer.js`. Both carry `sbsColorShiftEnabled`.

## Plan of Work

**Milestone 1 - ratify before implementing.** Obtain two independent reviews of
the corrected checkpoint and disposition their findings. Commit the package,
ADR, promoted SBS contract, contract decision, evidence, and review disposition
as the pre-implementation checkpoint. Do not edit closed work packages or
describe unimplemented behavior as current in production UI documentation.

**Milestone 2 - producer totality and exact lookup.** In `_write_color_table`,
write an entry for every value in the **union** of source color-table indices
(`range(ct.GetCount())`) and observed non-NoData raster values (`self.counts`).
Precedence: source NoData to `0 0 0 0`; recognized index to its severity color;
every other index or observed value to `128 0 152 255`. Palette indices alone are
not sufficient - `self.counts` is derived from band values independently of
`ct.GetCount()`, and an unlisted observed value would render transparent under
exact mode and be read as masked. Retain the `nv` line.
Add `-exact_color_entry` to both `gdaldem color-relief` invocations - in
`sbs_map.py::export_rgb_map` and `baer.py::build_color_map`. Document the emitted
RGB at both definition sites as a transport encoding of class.

Do not add a reprojection path, do not change `export_wgs_map`, and do not touch
classification, `counts`, `breaks`, coverage, or `RedisPrep`.

**Milestone 3 - client decode, sentinel, legends, tooltip.** Define one decode
table and one class-keyed display-palette table within each separate client
runtime boundary, per the contract decision clauses 4 and 7. Replace
`mapSbsRgbForMode` and `mapSbsRgbForDisplay`
with a decode-then-color path used by both modes; delete both
`SBS_STANDARD_TO_SHIFTED_RGB` tables and the passthrough. Leave alpha-`0` pixels
untouched. Render every other unrecognized opaque pixel as the sentinel and
accumulate `unassignedPixelCount`, exposed as `layer.sbsUnassignedCount`,
recomputed per decode and reset when the layer is removed.

Add the labeled Unassigned legend entry with its count to both clients. Change
the GL Dashboard SBS tooltip to report class code and severity label, or
`Unassigned`.

**Milestone 4 - consolidation and parity.** Derive `disturbed.py::legend` and
`baer.py::legend` from one Python table. Define one table in the run-page classic
bundle boundary and one in the GL Dashboard ES-module boundary, and derive each
client's legends from its table. Add a cross-client/Python parity test. Do not
introduce a new shared loading path, build step, or codegen.

**Milestone 5 - validation.** Follow the boundary-indexed evidence table in the
contract decision. Producer boundaries need generated-output tests over three
real-GDAL paths: Disturbed color-table classification, Disturbed breaks
classification, and BAER class-map writing. All prove source-valid opacity,
NoData transparency, and exact lookup. The color-table path additionally covers
a missing assignment and an observed value exceeding `ct.GetCount()-1`, both of
which must bake **opaque sentinel**, not transparency. A mutation removing
`-exact_color_entry` must fail.

On the client, prove generation-A and generation-B fixtures render canonical
colors in both clients and both modes with stored bytes unchanged; prove a
generation-0 fixture with values *between* the old breaks renders the ratified
Unassigned outcome, so the compatibility loss is asserted by test; and prove a
pre-change clamped pixel still decodes as that severity, so the stated limitation
is asserted rather than only documented.

## Guardrails

- Server edits are confined to `sbs_map.py`, `baer.py`, and `disturbed.py`, and
  only as enumerated in the contract decision's Scope Correction.
- No new route, payload key, artifact path, persisted field, request-time write,
  lazy regeneration, or subprocess from a request thread.
- Do not regenerate, rewrite, or migrate any existing run raster.
- Do not modify `sbs_color_map.json` or `_DEFAULT_COLOR_TO_SEVERITY`, and do not
  merge the ingestion table with the display decode table.
- Do not add a NoData option to the classify select. Blank means unassigned.
- Do not render unassigned as transparent, nor as any severity color.
- Do not use partial alpha for the sentinel.
- Do not change class codes, thresholds, breaks, coverage formulas, or model
  behavior.
- Do not change `sbs_4class.tif` or its export palettes.
- Do not introduce nearest-color or tolerance matching anywhere.
- Do not remediate `resources_baer_sbs` or `SBS_DEFAULT_OPACITY` here. The auth
  observation requires separate security scope; the opacity referral was
  withdrawn.
