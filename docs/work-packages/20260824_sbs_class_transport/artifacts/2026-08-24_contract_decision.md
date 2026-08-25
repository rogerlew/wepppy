# SBS-A11Y-02 Contract Decision

**Status**: Revision 3; operator-approved, awaiting post-correction review
**Decision date**: 2026-08-24
**Implementation baseline**: `5ef67d8d4f82991ee7e2a78c1c3a0b3051f14df8`
**Revision history**: r1 (new artifact/route/request-time regeneration) was
withdrawn; r2 (client-only, closed-encoding premise) was rejected when the
premise was disproved. Superseded review paperwork was removed during scaffold
cleanup; the retained GDAL probe and revision-3 review record the findings that
still matter.

## Authority and Ownership

This is a new work package governed by the current repository standards. It
does not reopen or amend closed work packages. Durable behavior is promoted to
`docs/ui-docs/contracts/sbs-display-transport-contract.md`; this package retains
execution evidence and provenance only.

Applicable canonical authorities:

- `docs/ui-docs/controller-contract.md` for shared controller invariants;
- `docs/ui-docs/contracts/sbs-display-transport-contract.md`;
- `docs/adrs/ADR-0041-sbs-usgs-section508-palette.md`;
- `docs/adrs/ADR-0045-sbs-class-coded-display-transport.md`.

`docs/schemas/nodb-persistence-concurrency-contract.md` is **not** applicable:
revision 3 introduces no persisted field and no NoDb mutation beyond what
`validate()` already performs.

## Defect Being Remediated

Two coupled defects, both confirmed against source and production artifacts.

**D1 - stale display palette.** Both clients pass stored pixels through
unmodified when color shift is off, so a palette revision orphans every
earlier run. Confirmed on `strategic-eloquence/disturbed9002_wbt`: its
`resources/baer.png` (`last-modified` 2026-05-21) contains only `(0,115,74)`,
`(77,230,0)`, `(255,255,0)`, `(255,0,0)` while the deployed legend renders the
ADR-0041 palette.

**D2 - fabricated or wrong-severity colors for unassigned classifications.** In the color-table
classify branch, `get_sbs_color_table` drops any palette entry with a falsy
severity (`sbs_map.py:497-499`) and `_write_color_table` writes entries only for
recognized indices (`sbs_map.py:1113-1120`). Neither bake site passes
`-exact_color_entry`, so `gdaldem color-relief` fabricates a color for every omitted index -
interpolating between entries, or **clamping to a legitimate severity color**
for values outside the recognized range (executional probe:
`2026-08-24_color_relief_behavior_probe.md`). Those indices are exactly the colors a user left blank in the
classify form (`classify.htm:110-124`, submitted verbatim as `""` by
`baer.js:752-762`). The model path classifies the same pixel as `255`/unknown
(`sbs_map.py:651-653`), so display and model disagree.

The breaks branch has no gap; it writes a line for every value in `self.counts`.
`Baer.write_color_table` is total over `self.classes`.

## Scope Correction: This Is a Server and Client Change

Revision 2 described itself as "client-only". Revision 3 does not. It edits
server source. The precise boundary:

**Permitted server edits**, all inside the existing validate-time render path:

- `wepppy/nodb/mods/baer/sbs_map.py` - `_write_color_table` color-table branch
  made total; `-exact_color_entry` added to the `gdaldem color-relief`
  invocation; frozen-encoding documentation at the definition site.
- `wepppy/nodb/mods/baer/baer.py` - `-exact_color_entry` added to its
  `gdaldem color-relief` invocation; `legend` consolidated.
- `wepppy/nodb/mods/disturbed/disturbed.py` - `legend` consolidated.

**Prohibited**: new route, new payload key, new artifact path, persisted field,
request-time write, lazy regeneration, subprocess invocation from a request
thread, change to `query/baer_wgs_map` response shape, change to
`resources/baer.png` route behavior, `RedisPrep` writes outside those
`validate()` already performs, and any change to classification, thresholds,
coverage, ingestion, or `sbs_4class.tif`.

## Exact Normative Delta

1. **Producer totality over the raster value domain.** `_write_color_table`
   writes an explicit entry for every value in the **union** of the source
   color-table indices (`range(ct.GetCount())`) and the observed non-NoData
   raster values (`self.counts`). Enumerating only palette indices is
   insufficient: `get_sbs_color_table` walks `range(ct.GetCount())` while
   `self.counts` is derived independently from band values, so a raster may hold
   a value outside the palette's index range. Under `-exact_color_entry` such a
   value would render `(0,0,0,0)` and be read by the client as masked, which
   contradicts clauses 5 and 6 and the operator decision.

   Precedence, applied in order:

   1. source NoData value or index -> `0 0 0 0`;
   2. index recognized as a severity -> that severity's transport color;
   3. every other index or observed value -> sentinel `128 0 152 255`.

   An `nv` line is retained for destination NoData. The `ct is None` breaks
   branch is already total over `self.counts` and `Baer.write_color_table` over
   `self.classes`; both gain only the exact-mode flag.

2. **Exact lookup.** Both `gdaldem color-relief` invocations pass
   `-exact_color_entry`. No raster value may receive an interpolated color.

3. **Sentinel.** Unassigned renders `#800098` at full per-pixel alpha,
   participating in layer opacity identically to the severity classes. Partial
   alpha is prohibited: layer opacity multiplies per-pixel alpha, so a
   partial-alpha sentinel disappears at low opacity, which is when validation
   occurs.

4. **Client decode.** Both clients decode every nontransparent pixel by exact
   RGB equality against this domain, then color the resulting class from the
   active display palette, unconditionally in standard and shifted modes:

   | RGB | Class |
   | --- | --- |
   | `46,203,24` / `0,115,74` / `0,128,128` | `130` unburned |
   | `161,250,220` / `77,230,0` / `82,204,204` | `131` low |
   | `255,161,5` / `255,255,0` / `255,232,32` | `132` moderate |
   | `217,34,3` / `255,0,0` / `168,0,0` | `133` high |
   | `128,0,152` | unassigned |

   No nearest-color or tolerance matching. The non-shifted passthrough in
   `map_gl_shared.js::mapSbsRgbForMode` and
   `gl-dashboard/map/layers.js::mapSbsRgbForDisplay` is deleted, as are both
   `SBS_STANDARD_TO_SHIFTED_RGB` tables.

5. **Alpha `0` is masked.** Skipped, left at alpha `0`, RGB not inspected.

6. **Any other opaque pixel renders as the sentinel.** The stored artifact is
   untrusted legacy display data; no provenance is assumed, because fork
   (`project_rq_fork.py`) and archive restore (`project_rq_archive.py`) copy run
   trees and an artifact may predate the local deployment.

   **This is a deliberate compatibility loss, not a recovery of true state, and
   it requires explicit operator approval.** For artifacts produced by the
   current color-table branch, an off-domain opaque pixel genuinely was
   unassigned. For **pre-2018 artifacts it was not**: that writer emitted only
   four break entries while `class_map` classified every observed value, so
   values between breaks were *classified* pixels that `gdaldem` rendered as
   interpolated off-domain RGB. Revision 3 relabels those as unassigned. Exact
   matching against twelve endpoint colors cannot recover their original
   severity; only artifact-specific classification metadata or regeneration
   could. The chosen behavior is conservative degradation - it shows the pixel
   as unclassified rather than guessing a severity - and the alternative
   considered was a distinct `legacy-undecodable` state.

7. **Display palettes** are constants keyed by class code. Standard
   `130 = #008080`, `131 = #52CCCC`, `132 = #FFE820`, `133 = #A80000`; shifted
   `130 = #009E73`, `131 = #56B4E9`, `132 = #F0E442`, `133 = #CC79A7`; masked
   `#FFFFFF` legend-only with a dark border; unassigned `#800098` in both modes.
   Severity values are unchanged from ADR-0041.

8. **Unassigned observability.** The decode pass returns an
   `unassignedPixelCount` integer alongside the rendered image, stored on the
   layer object as `layer.sbsUnassignedCount`. It is recomputed on every decode,
   reset to `0` when the layer is removed or the SBS map is cleared, and is
   rendered in the legend as a count beside the Unassigned entry. It is
   per-layer, not cumulative, and is not emitted as telemetry.

9. **Legends.** Both legends gain a labeled `Unassigned` entry with the
   clause-8 count. Existing entries, labels, ordering, and the masked swatch are
   unchanged.

10. **Tooltip.** The GL Dashboard SBS tooltip reports the decoded class code and
    severity label, or `Unassigned`, instead of a raw RGBA triple.

11. **Definition consolidation.** Python has one server-side palette definition.
    The run-page classic bundle and GL Dashboard ES modules each have one decode
    table and one display-palette table within their separate client boundaries.
    A cross-client/Python parity test prevents drift; no new shared loading path
    or build step is introduced. Legends derive from their boundary's table.

12. **Preserved unchanged**: `#sbs_color_shift_toggle`,
    `#gl-sbs-color-shift-toggle`, `sbsColorShiftEnabled`, dual legends, the
    opacity slider and its default `0.3`, `#sbs_legend` and `#sub_legend`,
    `baer:map:opacity`, `map:layer:refreshed`, `map:layer:error`,
    `disturbed:has_sbs_changed`, ingestion (`sbs_color_map.json`,
    `_DEFAULT_COLOR_TO_SEVERITY`, exact-match, no fuzzy matching),
    `sbs_4class.tif` and its export palettes, class codes, thresholds, breaks,
    coverage formulas, and model behavior.

13. **No regeneration of existing artifacts, with a stated limit.** Runs built
    before this change keep their baked pixels. Unassigned pixels that `gdaldem`
    *interpolated* are off-domain and render as the sentinel under clause 6.
    Unassigned pixels that `gdaldem` *clamped* to a legitimate severity color -
    which it does for values outside the recognized entry range - are inside the
    decode domain, cannot be detected client-side, and continue to display the
    wrong severity until re-validation. Clause 1 and clause 2 are the only remedy
    for those. See `2026-08-24_color_relief_behavior_probe.md`.

## Discrepancy Classification

- **Superseded**: the transport by which ADR-0041's palette reaches the screen,
  and ADR-0041's contracted tooltip representation. ADR-0041 did not state a
  shifted-only recoloring restriction; the restriction was in the
  implementation.
- **Retained**: ADR-0041's palette values, class codes `130`-`133` and `255`,
  ingestion recognition and exact-match rule, masked/unmappable transparency with
  a labeled dark-bordered white legend swatch, the standard/shifted user choice,
  and the export contract.
- **New**: the unassigned state and its sentinel. ADR-0041 did not contemplate
  it; the interpolated colors it produced were an unintended implementation
  artifact, not a ratified behavior.

## Compatibility and Data Impact

No payload, route, schema, or persisted-field change, so no mixed-version
server/client negotiation exists. An old cached client against a new server
renders the sentinel color literally - visibly odd, not misleading. A new client
against an old server decodes generation-A/B pixels correctly and shows
interpolated pixels as unassigned. In the current color-table branch that
reflects the missing assignment. For the pre-2018 breaks writer it is an
approved conservative compatibility loss, not recovery of the original class.

Generated output changes for every run validated after the change. Existing run
files are not read differently or written at all. Model-facing consumers -
`data`, class maps, landuse, soils, coverage - are untouched.

## Valid-State and User-Experience Gate

**Input matrix**: color mode standard / shifted; opacity min / `0.3` / max; SBS
added or removed mid-session; layer toggled; run page and GL Dashboard
independently; classify branch breaks vs color-table.

**State matrix**:

| Category | State | Required outcome |
| --- | --- | --- |
| Absent | No SBS registered | Existing "No SBS map has been specified" error; no overlay, no legend. Unchanged. |
| Absent | Registered, raster missing on disk | Existing behavior: `map:layer:error`; rest of map usable. Unchanged. |
| Present-empty | Raster present, every pixel alpha `0` | Overlay fully transparent; legend renders; `sbsUnassignedCount` `0`; no error. |
| Present-empty | Raster present, all opaque pixels off-domain | All render as sentinel; count equals opaque pixel count; legend shows Unassigned; no error. |
| Populated | Generation-B raster, all colors assigned | Decodes to classes; canonical colors in standard, shifted colors in shifted; count `0`. |
| Supported legacy | Generation-0 or generation-A raster containing known endpoint colors | Endpoints decode to the same classes and render identically; stored bytes untouched. |
| Supported legacy | Current color-table raster with a missing assignment baked as an interpolated color | Interpolated pixel renders Unassigned and is counted, reflecting the missing assignment. |
| Supported legacy | Pre-2018 breaks raster with a classified between-break value baked as an interpolated color | Pixel renders Unassigned and is counted as the approved conservative compatibility loss; this does not recover its original class. |
| Mixed | Valid and off-domain pixels together | Valid pixels color normally; off-domain render sentinel and are counted. Never coerced to a severity. |
| Malformed | Raster fails to decode or has unexpected dimensions/channels | Existing canvas load path emits `map:layer:error`; no overlay; rest of map usable. Unchanged by this delta. |
| Hostile | Hand-modified artifact with severity-like off-domain colors | Sentinel, not a severity color. Exact matching is the control. |
| Hostile | Artifact inherited via fork or archive restore from another deployment | Decoded on content alone; no provenance assumed. Unrecognized colors render as sentinel. |

Expected states: all Populated, Supported legacy, Mixed, and both Present-empty
rows. Exceptional: the Absent-missing and Malformed rows only.

## Security Impact

Security impact is `low`. The proposed delta adds no route, request-time write,
request-thread subprocess, persistence, or authorization surface. The producer
edit runs where GDAL is already invoked, under the same ownership and lock as
today.

**Adjacent observations, not part of this package:**

1. `resources_baer_sbs` serves the raster used by this display path, but its
   route and authorization behavior are unchanged. Any authorization remediation
   requires a separate security-scoped change.
2. **`SBS_DEFAULT_OPACITY = 0.3` - the reported finding is RETRACTED.** An
   earlier revision reported that the default opacity attenuates the ADR-0041
   CVD palette and referred it to DOM-04B. That finding was an artifact of
   scoring the union of the standard and shifted palettes - which are mutually
   exclusive display modes - while compositing at `0.3`. Assessed one palette at
   a time at full opacity, the shifted palette holds `12.21`-`15.54` under all
   three dichromacies and the standard palette holds roughly `23` across all
   four vision models. Both are sound. No palette change is proposed, the
   default stays at `0.3`, and the referral is withdrawn as erroneous rather
   than closed as won't-fix.

## Proposed Regression Evidence

Boundary-indexed. Producer boundaries require generated-output tests over real
GDAL invocation, not fixture-only assertions or constant scraping.

| Boundary | Evidence |
| --- | --- |
| Producer totality (clause 1) | Run three real-GDAL paths: Disturbed color-table classification proves union-of-source-indices-and-observed-values totality; Disturbed breaks classification proves observed-value totality; BAER class-map writing proves observed-class totality. Each asserts source-valid opacity and NoData transparency. Only the Disturbed color-table path has assigned/unassigned source indices and the out-of-range-table case. |
| Out-of-range observed value (clause 1) | Fixture whose observed raster value exceeds `ct.GetCount()-1`. Assert the pixel is **opaque sentinel**, not transparent. This is the case that a naive opaque-RGB-subset assertion would pass while silently losing the pixel to masked. |
| Source-valid opacity invariant (clause 1) | Generated-output assertion that every source-valid (non-NoData) pixel remains opaque after baking, and decodes to either a severity or the sentinel. Destination NoData asserted separately. |
| Exact lookup (clause 2) | Decode output from all three paths and assert the opaque RGB set is a subset of the clause-4 domain. The Disturbed color-table path includes missing and beyond-table values; the breaks and BAER paths include between-entry values. A mutation removing `-exact_color_entry` must fail. |
| Sentinel (clause 3) | Assert the produced PNG contains `128,0,152,255` for unassigned indices and that no severity pixel carries partial alpha. |
| Decode domain (clause 4) | Table test over all twelve severity RGBs plus the sentinel; negative case asserting an off-domain opaque RGB does not decode to a severity. |
| Unconditional recolor (clause 4) | Both clients, both modes, all three generations: assert output pixels are the expected palette colors. Must fail if a passthrough branch is reintroduced. |
| Masked (clause 5) | Alpha-`0` pixel untouched; RGB never inspected. |
| Untrusted artifact (clause 6) | Fixture with colors from no generation renders sentinel and is counted. |
| Unassigned count (clause 8) | Assert value, reset on layer removal, and legend rendering; assert per-layer not cumulative. |
| Legends (clause 9) | Unassigned entry present with count in both clients, both modes. |
| Tooltip (clause 10) | Class code and label for a known class; `Unassigned` for an off-domain pixel. Replaces the raw-RGBA assertion in `sbs-color-shift-tooltip.test.js`. |
| Consolidation (clause 11) | Cross-client/Python parity test; assert one definition in Python and one within each separate client boundary. |
| No server surface change (clause 12) | Assert the blueprint registers no new route and the `query/baer_wgs_map` payload shape is byte-equivalent to baseline. |
| Ingestion untouched (clause 12) | SBS-A11Y-01 recognition fixtures pass unchanged. |
| Legacy integrity (clause 13) | Stored raster bytes identical before and after rendering. |
| Clamping limit (clause 13) | Executional test proving a pre-change artifact with a clamped unassigned pixel still decodes as that severity, so the limitation is asserted by test rather than only documented. |

## Operator Approval

- Operator: Roger Lew
- Directives captured 2026-08-24: always recolor and remove display dependence on
  the stored source color map, including the GL Dashboard; unassigned is its own
  state, intent must not be assumed for values absent from the default mappings,
  users validate classes on the deck.gl map; revise magenta.
- Explicit approval of this exact normative delta and compatibility policy:
  approved by the operator's 2026-08-24 request to execute the summarized work
  package and 2026-08-25 governance clarification.
