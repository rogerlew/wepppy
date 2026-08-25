# SBS-A11Y-02 Revision 3 Review Disposition

**Date**: 2026-08-25  
**Dispositioned by**: Claude Code (checkpoint author)  
**Review dispositioned**: `2026-08-24_revision3_review.md` (Codex, REJECTED, 5 findings)

## Outcome

**All five findings accepted.** Two were verified independently by the author
before acceptance rather than taken on report.

| # | Sev | Finding | Disposition |
| --- | --- | --- | --- |
| 1 | High | Producer totality defined over color-table indices, not the observed raster value domain. An observed value outside `ct.GetCount()` would render transparent under exact mode and be read as masked - contradicting the operator decision that unknown is not masked. | **Accepted and fixed.** Totality redefined over the union of palette indices and observed non-NoData values, with explicit precedence. Three generated-output evidence items added, including a fixture whose observed value exceeds the palette count and an assertion that every source-valid pixel stays opaque. The reviewer is right that the previously proposed opaque-RGB-subset assertion would have passed while silently losing the pixel. |
| 2 | High | Revision 3 still claimed historical artifacts decode correctly. Pre-2018 interpolated pixels were *classified*, not unassigned; relabeling them is a compatibility loss, not recovery of true state. | **Accepted and fixed.** Verified against `126673850^`: that writer emitted four break entries while `class_map` classified every observed value. ADR clause 6 and contract clause 6 now state the loss explicitly, mark it as requiring operator approval, and record the rejected `legacy-undecodable` alternative. A generation-0 fixture with between-break values is added to the evidence table. |
| 3 | Medium | The CVD analysis composited after simulation. Correct order is composite, then simulate. | **Accepted and verified by recomputation.** The reviewer's corrected figures reproduce exactly: baselines `5.32` standard and `2.83` shifted at alpha `0.3`; `#7F00FF` falls from `10.39` to `8.64`. Re-running the search under the corrected order selected **`#2000E0` at `12.08`**, so the sentinel changed. Both scripts rewritten and now resolve their library relative to `__file__`. The referred DOM-04B opacity figures were updated everywhere. |
| 4 | High | Cross-owner authority not established; contract decision overstated registration. Checkpoint requirements 3, 5, 6 open. | **Accepted and fixed.** The Authority section now states that `SBS-A11Y-02` is a *proposed*, not registered, bounded remediation until a GOV-00A milestone exists, and that revision-1/revision-2 reviews do not satisfy review of revision 3. Milestone registration is operator-owned and tracked as an open blocker. |
| 5 | Medium | Tracker remained internally revision-2 and contradicted every revision-3 authority in live status, risk, and verification sections. | **Accepted and fixed.** Tracker rewritten for revision 3. Superseded revisions moved to a labeled History section, including the disproved two-generation enumeration and the superseded `#7F00FF` / `10.39` / `5.04` / `3.48` figures, so stale citations remain recognizable. |

## Reviewer confirmations recorded

The review verified and confirmed several things that now stand as evidence:

- All twelve generation RGB triples match `126673850^`, `126673850`, and
  `531d06d35`. All twelve are mutually distinct and none collides with the
  sentinel.
- The sentinel does not appear in `sbs_color_map.json` or
  `_DEFAULT_COLOR_TO_SEVERITY`. Display PNG generation is downstream of
  classification, and `sbs_4class.tif`, coverage, landuse, and soils read
  classified or source data rather than the display PNG, so the sentinel cannot
  feed back as a severity.
- Independent GDAL exercise confirmed `nv` is honored in exact mode and that a
  missing non-NoData entry becomes transparent rather than opaque black,
  matching the author's own probe.
- The Machado matrices, sRGB transfer functions, D65 Lab conversion, and
  CIEDE2000 implementation match their standard forms.
- Revision-2 findings 3, 4, 6, and 7 are resolved in revision 3.

## Author-originated correction, found independently

Not a review finding. Before the review returned, an executional GDAL probe
established that default `color-relief` **clamps** outside the entry range to a
legitimate severity color, not only interpolating between entries. Clamped
pixels are inside the decode domain and cannot be detected client-side. This
reclassified the producer change and `-exact_color_entry` from defense-in-depth
to load-bearing, and withdrew the claim that client decoding repairs historical
artifacts. See `2026-08-24_color_relief_behavior_probe.md`.

## Residual open items

Not review findings, but blocking for the checkpoint:

1. Operator approval of the corrected revision-3 exact normative delta.
2. Operator approval of the pre-2018 compatibility loss (finding 2).
3. Operator acknowledgment of the two referred preexisting defects.
4. GOV-00A bounded-remediation milestone registration (operator-owned).
5. A second independent review of the corrected revision 3.
6. Standalone ancestor commit, with its revision recorded in the tracker.

## Note on independence

This disposition is authored by the checkpoint author and is not itself a
review. The corrected revision 3 requires its own independent review before the
ancestor commit.
