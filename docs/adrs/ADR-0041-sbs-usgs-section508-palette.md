# ADR: Canonical USGS SBS Accessibility Palette

Status: Accepted  
Date: 2026-08-07

## Context

WEPPcloud exposes a non-shifted SBS palette and an optional client-side
color-shifted palette. The non-shifted palette needs to track the current
interagency colors while the established shifted option remains available. The interagency Burn
Severity Portal publishes a current CVD-friendly palette intended to support
Section 508 accessibility: teal unchanged, cyan low, yellow moderate, dark red
high, and white masked/unmappable.

## Decision

Use this palette for non-color-shifted display and export:

| Meaning | Hex | RGB | Normalized WEPPcloud value |
| --- | --- | --- | --- |
| Unchanged / unburned | `#008080` | `0, 128, 128` | `130` |
| Low severity | `#52CCCC` | `82, 204, 204` | `131` |
| Moderate severity | `#FFE820` | `255, 232, 32` | `132` |
| High severity | `#A80000` | `168, 0, 0` | `133` |
| Masked / unmappable | `#FFFFFF` | `255, 255, 255` | `255` / NoData |

Retain the standard/shifted display choice, per-pixel client recoloring, and
default shifted export. Preserve exact recognition of every currently
supported historical palette so
existing projects remain readable. Unknown colors remain unknown; no fuzzy
matching is introduced.

The shared JSON retains only the four established severity strings. Exact
white is recognized separately as a source color-table NoData entry. Existing
model consumers continue mapping source NoData/off-map cells to class `130`;
the four-class interchange export instead writes those cells as `255` with
transparent alpha.

Masked/unmappable pixels render transparently on maps. Legends retain an
explicitly labeled white `#FFFFFF` swatch with a dark boundary so the published
source color remains documented and visible against a light background.

## Decision Provenance

Decision Venue: Codex work-package request, 2026-08-07 08:15 PDT  
Participants Present: Roger Lew, Codex  
Decision Owner(s): Roger Lew  
Implementer(s): Codex

Correction Venue: Codex implementation review, 2026-08-07 PDT (between the
08:15 request and 09:10 review; exact message timestamp unavailable)
Correction: preserve both shifted display modes and the default shifted export;
apply the new colors only to non-shifted display and explicit non-shifted export.

## Change Summary

The non-shifted UI palette and explicit `export_palette="legacy"` palette
change to the five exact RGB values above. The default shifted export and
shifted UI palette do not change. The four-severity RGB input lookup
grows additively. Numeric severity classes and thresholds do not change.
Exact-white entries previously treated as unknown intentionally adopt the
existing source-NoData behavior: class `130` for model consumers, exclusion
from coverage denominators, and value `255` in four-class interchange exports.

## Rationale

One authoritative non-shifted palette aligns imagery, legends, tooltips, and
explicit non-shifted exports while preserving the user-selectable shifted
view. It follows the current interagency publication and improves differentiation for common color
vision deficiencies. Additive recognition is the smallest compatible input
change.

## Alternatives Considered

1. Remove the user-selectable shifted palette — rejected because that is an
   unrelated breaking change outside the requested non-shifted palette update.
2. Replace historical RGB recognition — rejected because old indexed rasters
   would stop classifying.
3. Use nearest-color tolerance — rejected because it can silently assign an
   unknown thematic color to the wrong burn class.

## Consequences

Non-shifted maps and explicit non-shifted exports visibly change colors. The
shifted display and default shifted export do not. Severity thresholds and formulas do
not change, but landuse/model results and coverage summaries for exact-white
inputs may change because those cells move from unknown handling to the
approved source-NoData behavior. Existing saved color-shift state remains active.
White NoData needs a non-color boundary in legends and careful basemap
validation. The public accessibility statement may describe the adopted
CVD-friendly palette, but must not infer overall conformance from this decision.

## Evidence

- [RAVG FAQs](https://burnseverity.cr.usgs.gov/ravg/faqs)
- `docs/work-packages/20260807_sbs_section508_palette/package.md`
- Implementation and validation artifacts: pending.

## Risk and Rollback Notes

Primary risks are Python/Rust classification drift, masked pixels being treated
as unburned, and white becoming invisible. Roll back the canonical export/UI
selection if validation fails; retain additive input RGB recognition unless it
causes demonstrated misclassification.

## Implementation Notes

Update `sbs_color_map.json`, Python export tables, the Rust parity path, both
map clients, tests, specifications, and the public accessibility statement in
one change set. Preserve masked/unmappable as value `255`/NoData and transparent
map pixels; do not composite them to opaque white. ADR acceptance is part of
the contract-first checkpoint and becomes an implementation authority only
when that reviewed checkpoint is committed as a standalone ancestor.
