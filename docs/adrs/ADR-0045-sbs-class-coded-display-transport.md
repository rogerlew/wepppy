# ADR: SBS Display Class Decoding and the Unassigned State

Status: Accepted (revision 3)  
Date: 2026-08-24

## Context

WEPPcloud renders soil burn severity (SBS) maps from
`disturbed/baer.wgs.rgba.png`, produced by `gdaldem color-relief` during
`Disturbed.validate()` or `Baer.build_color_map()`. Both clients pass those
pixels straight to the screen when color shift is off: `mapSbsRgbForMode` in
`map_gl_shared.js` and `mapSbsRgbForDisplay` in `gl-dashboard/map/layers.js`
each return the source RGB unchanged in that mode.

ADR-0041 revised the display palette on 2026-08-07 by changing the generator, so
runs built earlier disagree with their own legends. Production run
`strategic-eloquence/disturbed9002_wbt`, built 2026-05-21, shows the
pre-ADR-0041 palette under an ADR-0041 legend.

Two earlier revisions of this ADR were rejected at independent review. Revision 1
proposed a new artifact, a new route, and request-time regeneration; that write
path was withdrawn. Revision 2 asserted the baked raster was a closed encoding of
burn class; that premise was disproved - a third, pre-2018 palette generation
exists, and the pre-2018 color table was sparse while neither bake site disables
`gdaldem` interpolation.

Investigating the disproof located the actual defect precisely. In the
color-table classify branch, `get_sbs_color_table` drops any palette entry whose
severity is falsy (`sbs_map.py:497-499`), and `_write_color_table` then writes
entries only for the recognized indices (`sbs_map.py:1113-1120`). Because neither
bake site passes `-exact_color_entry`, `gdaldem color-relief` interpolates a
fabricated color for every index that has no entry.

Those indices are exactly the palette colors a user left blank in the classify
form (`classify.htm:110-124`, options `""`, `unburned`, `low`, `mod`, `high`).
So an undecodable pixel *is* an unassigned pixel. Meanwhile the model path sends
the same pixel to `ct_classify`, which returns `255`/unknown. The model says
"unknown" while the map paints a color that corresponds to no class and appears
in no legend.

The breaks branch has no such gap: it writes a line for every value in
`self.counts`. `Baer.write_color_table` is likewise total over `self.classes`.

## Decision

**Unassigned is a first-class display state, distinct from masked/NoData.**

1. Intent is not inferred for values absent from the default mappings. An
   unassigned color is not treated as NoData, not treated as unburned, and not
   given an interpolated color. Users are responsible for validating their
   classification on the deck.gl map, so unassigned pixels must be identifiable
   there.

2. **Producer.** `sbs_map.py::_write_color_table` writes an explicit entry for
   every value in the union of the source color-table indices and the observed
   non-NoData raster values. Precedence: source NoData to `0 0 0 0`; recognized
   index to its severity color; everything else to the unassigned sentinel
   `128 0 152 255`. Enumerating palette indices alone is insufficient, because
   `self.counts` is derived from band values independently of
   `ct.GetCount()`, and an unlisted observed value would otherwise render
   transparent under exact mode and be read as masked. Both bake sites invoke
   `gdaldem color-relief` with `-exact_color_entry`. This is confined to the
   existing validate-time render path.

3. **Sentinel.** Unassigned renders as `#800098` at full per-pixel alpha,
   participating in layer opacity exactly like the severity classes. Selection
   evidence:
   `docs/work-packages/20260824_sbs_class_transport/artifacts/2026-08-24_unassigned_sentinel_analysis.md`.

4. **Client.** Both map clients decode each nontransparent pixel to a class by
   exact RGB match, then color that class from the active display palette,
   **unconditionally** in standard and shifted modes. The non-shifted passthrough
   and both `SBS_STANDARD_TO_SHIFTED_RGB` tables are deleted.

   The decode domain is the sentinel plus all three historical severity
   generations:

   | Generation | Unburned | Low | Moderate | High |
   | --- | --- | --- | --- | --- |
   | 0 (pre-2018-08-10) | `46,203,24` | `161,250,220` | `255,161,5` | `217,34,3` |
   | A (to 2026-08-07) | `0,115,74` | `77,230,0` | `255,255,0` | `255,0,0` |
   | B (ADR-0041, current) | `0,128,128` | `82,204,204` | `255,232,32` | `168,0,0` |

5. **Alpha `0` is masked/unmappable.** It is skipped and left at alpha `0`; its
   RGB is not inspected. This is unchanged from ADR-0041.

6. **Any other opaque pixel renders as the sentinel.** The stored artifact is
   treated as untrusted legacy display data: no provenance is assumed, because
   fork and archive restore copy run trees and an artifact may predate the local
   deployment.

   For the current color-table branch this is semantically exact - an
   off-domain pixel genuinely was unassigned. For **pre-2018 artifacts it is a
   deliberate compatibility loss**: that writer emitted only four break entries
   while `class_map` classified every observed value, so interpolated pixels
   between breaks were *classified*, not unassigned. Relabeling them as
   unassigned is conservative degradation, chosen over guessing a severity.
   Exact matching against twelve endpoint colors cannot recover the original
   class; only per-artifact classification metadata or regeneration could. This
   loss was explicitly approved by the operator for this implementation.

7. **Legends and tooltip.** Both legends gain a labeled Unassigned entry. The
   unassigned pixel count is exposed as a first-class observable. The GL
   Dashboard SBS tooltip reports the decoded class code and severity label, or
   `Unassigned`, instead of a raw RGBA triple.

8. **Not changed.** No new route, payload key, persisted field, request-time
   write, or lazy regeneration. `query/baer_wgs_map`, `resources/baer.png`,
   `RedisPrep`, and NoDb state are untouched. Source color-table ingestion
   (`sbs_color_map.json`, `_DEFAULT_COLOR_TO_SEVERITY`, exact-match, no fuzzy
   matching) is unchanged, and the display decode table is separate from it.
   `sbs_4class.tif` and its export palettes are unchanged. Class codes,
   thresholds, breaks, coverage formulas, and model behavior are unchanged.

9. **Existing artifacts are not regenerated, and client decoding does not fully
   repair them.** A run built before this change keeps its baked pixels. Two
   cases must be distinguished, per the executional probe in
   `artifacts/2026-08-24_color_relief_behavior_probe.md`:

   - Unassigned indices whose value fell *between* recognized entries were
     **interpolated** to an off-domain color. Clause 6 renders these as the
     sentinel, so they are corrected on screen.
   - Unassigned indices whose value fell *outside* the recognized range were
     **clamped by `gdaldem` to a legitimate severity color**. These are inside
     the decode domain and are indistinguishable from genuinely classified
     pixels. No client-side rule can detect them. They continue to display the
     wrong severity until the run is re-validated.

   The producer change in clause 2 is therefore load-bearing rather than defense
   in depth: it is the only remedy for clamped pixels, and it takes effect on
   re-validation, which a classify re-submit already performs.

This supersedes the transport by which ADR-0041's palette reaches the screen and
ADR-0041's contracted tooltip representation. ADR-0041's palette values, class
codes, ingestion recognition, masked/unmappable semantics, legend requirements,
and export contract remain normative.

## Decision Provenance

Decision Venue: Claude Code session, 2026-08-24  
Participants Present: Roger Lew, Claude Code  
Decision Owner(s): Roger Lew  
Implementer(s): Codex

Operator directives, in order:

- Always recolor; remove display dependence on the stored source color map;
  apply the same correction to the GL Dashboard.
- On unassigned pixels: intent must not be assumed for values absent from the
  default mappings; unassigned/missing is its own state, not masked; users
  validate classes on the deck.gl map.
- On the sentinel: revise magenta.

Reviewer scope boundary, adopted by the operator: "remove the source color map"
is scoped to the display path; ingestion-side RGB recognition is retained.

Revision history: revision 1 (new artifact, new route, request-time
regeneration) withdrawn after two independent rejections. Revision 2
(client-only, closed-encoding premise) rejected when the premise was disproved.
Revision 3 is a bounded producer fix plus client decoding.

## Change Summary

Old: `classify -> bake display RGB, omitting unassigned indices -> gdaldem
interpolates them -> client renders stored colors when unshifted`.

New: `classify -> bake a total color table including an unassigned sentinel,
with exact lookup -> client decodes known colors to class -> client colors`.

Behavior visible to users: newly validated unassigned regions change from a
fabricated color to an identifiable sentinel. Known historical endpoint colors
no longer depend on when a run was built; unrecoverable interpolated and clamped
historical pixels retain the limitations in decision 9.

## Rationale

Making the color table total over the observed value domain removes the
interpolation and clamping gaps at their source rather than compensating for them
downstream, and it does so inside the render path that already exists. Decoding
on the client makes display palette a deployed-code property for known transport
colors, so palette revisions apply on next load without rewriting the artifact.

Treating anything unrecognized as unassigned is exact for the current
color-table branch, where undecodable and unassigned are the same set, and
conservative for pre-2018 artifacts, where it trades an unrecoverable historical
severity for an honest "unclassified" rather than a guess. It also removes any
need to trust artifact provenance, which fork and archive restore would otherwise
make unsafe to assume.

The mechanism is already proven. The shifted path performs exact-RGB canvas
decoding in production today, which is why shifted maps on stale runs look
correct while non-shifted ones do not.

## Alternatives Considered

1. **Backfill every run's display raster.** Rejected: a filesystem sweep, and the
   only supported re-render path reenters `validate()`, re-classifying and
   marking downstream stale.
2. **New class-coded artifact plus a route with lazy regeneration** (revision 1).
   Rejected at review: unbounded request-time GDAL write amplification,
   non-atomic publication, a NoDb persistence hazard, and a new authorization
   surface.
3. **Client-only decoding with no producer change** (revision 2). Rejected: the
   baked domain is not closed, so unassigned pixels would remain fabricated
   colors in every newly built run.
7. **A distinct `legacy-undecodable` display state**, separate from unassigned,
   for pre-2018 interpolated pixels. Considered under clause 6 and not adopted:
   it adds a fourth non-severity state that users cannot act on differently, and
   the remedy in both cases is re-validation. Recorded so the trade is visible
   rather than implicit.
4. **Map unassigned to masked/transparent.** Rejected by the operator: it assumes
   intent, and it renders unassigned identically to a legitimate NoData hole,
   defeating the visual validation users are responsible for.
5. **Add a NoData option to the classify select.** Rejected for the same reason;
   blank continues to mean unassigned.
6. **Magenta sentinel, or a partial-alpha sentinel.** Rejected on measurement.
   See the sentinel analysis artifact.

## Consequences

Unassigned classifications become visible instead of silently plausible. This
will surface preexisting misclassifications in runs whose users never noticed
them, which is the intent.

The producer change means output correctness applies to runs validated after the
change. Existing artifacts are partially repaired by client decoding: interpolated
unassigned pixels become the sentinel, but pixels `gdaldem` clamped to a valid
severity color cannot be detected client-side and keep displaying the wrong
severity until re-validation. How many runs contain clamped pixels is unquantified
and would need an inventory pass.

`-exact_color_entry` converts both failure modes - interpolation between entries
and clamping outside the range - into a visible-absent transparent pixel.
Confirmed executionally: an unmatched value renders `(0,0,0,0)`, and the `nv`
line is still honored in exact mode. Because clamping silently produces a valid
severity color, this flag is load-bearing, not merely defensive.

The decode domain now carries three historical generations. It grows only if a
new bake palette is introduced, which the producer-output tests are designed to
catch.

The GL Dashboard tooltip output changes; tests asserting a raw RGBA string must
be updated.

## Evidence

- Defect: production `resources/baer.png` and `disturbed/color_table.txt` for
  `strategic-eloquence/disturbed9002_wbt`, fetched 2026-08-24.
- Third generation: `git show 126673850` (2018-08-10) replacing
  `(46,203,24)`, `(161,250,220)`, `(255,161,5)`, `(217,34,3)`.
- Sparse pre-2018 table: `git show 126673850^:wepppy/nodb/mods/baer/baer.py`.
- Interpolation and clamping behavior: executional probe against GDAL 3.10.1,
  `artifacts/2026-08-24_color_relief_behavior_probe.md`. Default mode interpolates
  between entries and clamps outside the range; exact mode renders unmatched
  values transparent and still honors `nv`.
- Unassigned path: `classify.htm:110-124`, `baer.js:752-762`,
  `sbs_map.py:497-499`, `sbs_map.py:1113-1120`, `sbs_map.py:651-653`.
- Sentinel selection:
  `docs/work-packages/20260824_sbs_class_transport/artifacts/2026-08-24_unassigned_sentinel_analysis.md`
  and the three reproducible scripts beside it.
- Historical revision-3 review and disposition:
  `artifacts/2026-08-24_revision3_review.md` and
  `artifacts/2026-08-24_revision3_disposition.md`. A fresh review of the cleaned
  normative set is pending.
- Implementation and validation artifacts: pending.

## Risk and Rollback Notes

The producer change alters generated output for every subsequently validated run,
so its evidence must be generated-output, not fixture-only.

A future bake-palette change would extend the decode domain. Producer-output
tests over adversarial source domains, not constant scraping, are the control.

Surfacing unassigned regions may be read as a regression by users who had been
seeing a plausible color. Release notes should state that the sentinel reveals
an existing classification gap rather than creating one.

Roll back the client by restoring the passthrough branch; roll back the producer
by reverting the table writer. Neither direction destroys run data. A run
validated under the new producer and then viewed by an old client would show the
sentinel color literally, which is visibly odd but not misleading.

## Implementation Notes

Confine the producer change to `sbs_map.py::_write_color_table` and the two
`gdaldem color-relief` invocations. `Baer.write_color_table` is already total
over `self.classes` and needs only the `-exact_color_entry` flag.

Define one Python server-side palette table, one decode/palette table within the
run-page classic-bundle boundary, and one within the GL Dashboard ES-module
boundary. Derive legends within each boundary and enforce cross-client/Python
parity by test; do not add a shared loading path or build step.

Update `docs/ui-docs/map-specification-and-behavior.md`,
`docs/ui-docs/gl-dashboard.md`, `wepppy/nodb/mods/baer/README.sbs_map.md`, and
tests in one change set.

ADR acceptance is part of the contract-first checkpoint and becomes an
implementation authority only when that reviewed checkpoint is committed as a
standalone ancestor.
