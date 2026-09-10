# ADR-0063: Distribution-based dNBR upload scale detection

Status: Execution criteria recorded; independent review pending  
Date: 2026-09-10

## Context

Users should not need to prepare scale metadata before uploading dNBR. The
initial production draft only resolved Auto from explicit metadata. The owner
requested value-distribution identification and an uploaded-map summary table.
The existing local normalizer still requires explicit factor/offset.

## Decision

Auto must attempt identification from valid source-value distributions. Compare
the standard factor 1 and factor 0.001 encodings, both with offset zero, using
robust statistics and metadata evidence. Do not invent arbitrary custom scaling.
Clear cases proceed without confirmation; ambiguous cases request scale selection.
Show upload details and the applied scale in `wc-control__panel-summary` and
allow correction using retained source files. Resolve encoding explicitly before
normalization and preserve detection evidence/version in publication provenance.

Distribution-v1 evaluates all finite unmasked values (bounded by existing raster
limits), using NumPy linear-interpolated quantiles of absolute values. Fewer than
32 samples is ambiguous. Select normalized (factor 1) when q99 ≤ 2 and at least
5% of values differ from their nearest integer by more than 1e-6. Select ×1,000
(factor 0.001) when q95 > 2 and q99 ≤ 2,000. Other cases are ambiguous. Zero and
negative values are included. Outliers are not clipped from the actual normalized
output. Evaluate source-wide and project-watershed-aligned raw distributions;
if both resolve and disagree, require explicit selection. If only one resolves,
use that decision and record the evidence domain. Nondefault valid metadata must
agree with an inferred factor/offset; conflict requires an explicit error, not
silent override. When distribution is ambiguous, explicit nondefault metadata
may resolve Auto; unqualified identity metadata is not evidence.

These conservative heuristics aim to handle ordinary products, not establish
encoding mathematically. The production package evaluation records known scaled
fixtures, normalized equivalents and analytical ambiguity/outlier cases. Further
regression checks must cover overlap/masks, metadata conflict and repeatability.
The normalizer's existing strict metadata conflict checks remain in force.

Production first-control defaults also freeze frequency source cli, durations
15/30/60 minutes, design intervals 1/2/5/10 years and inverse target 0.5. They
compose the existing explicit local APIs; no probability formula changes.

## Decision Provenance

Decision Venue: repository planning conversation, 2026-09-10, America/Los_Angeles;
exact message time not recorded.  
Participants Present: project owner (user), Codex.  
Decision Owner(s): project owner for distribution-based Auto and summary table.  
Implementer(s): Codex documents scaffold; runtime implementation by Codex under the owner’s execute-work-package instruction.

## Change Summary

Production proposal changes from metadata-only Auto to distribution-based Auto
with metadata checks. Existing normalizer API and scale presets remain unchanged.
Add a persistent upload summary, including the scale and how it was selected.

## Rationale and Alternatives Considered

Metadata-only detection leaves many maps requiring manual interpretation. Dtype-
only detection or a min/max cutoff can misclassify low-valued or contaminated
rasters. Robust distribution evaluation provides a practical automatic path;
explicit selection remains available when the evidence is insufficient.

## Evidence and Implementation Notes

The [UI contract](../ui-docs/contracts/postfire-debris-flow-control-contract.md#dnbr-field-and-copy)
defines the table, correction flow and distribution requirements. The
[production work package](../work-packages/20260910_staley_m1_production/package.md)
must supply fixture evidence before finalizing numerical criteria: equivalent
normalized/scaled maps, partial coverage, different extents, negative/zero values,
masked sentinels, isolated outliers, conflicting metadata and ambiguous inputs.
The recorded fixture probe is limited evidence, not population-wide accuracy.

## Consequences, Risk and Rollback Notes

Distribution does not prove encoding; a wrong choice changes M1's F predictor.
Preserve raw source, explicit factor/offset and evidence so users can correct
Auto without retransferring the file. Re-normalize corrections as new attempts;
invalidate dependent results on accepted replacement. Never clip values to force
a fit. If evaluation cannot distinguish a case reliably, require explicit scale
selection for that case. Do not silently reinterpret previously published maps.
