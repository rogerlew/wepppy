# Investigate July 30–August 2 correspondence

## Purpose / Big Picture

Assess whether the earlier wet sequence is a credible cause of the Dead Horse Creek deposits and whether M3 rainfall scenarios are consistent with it.

## Progress

- [x] (2026-09-17 UTC) Scope read-only follow-up and identify saved assessments.
- [x] Extract and independently check July 25–August 16 event context, with July 30–August 2 as the candidate window.
- [x] Inspect paper supplement and sample precipitation across the basin.
- [x] Retain findings, source limitations, and documentation closeout.

## Surprises & Discoveries

Canonical ScienceBase file/get URLs succeeded where earlier direct S3 downloads failed. The in-basin gauge records high intensities on July 31 and August 2. The supplement provides no dated Dead Horse Planet pair.

## Decision Log

2026-09-17 UTC: investigate the user's earlier-storm hypothesis directly. Keep both date windows visible and distinguish consistency from causal attribution. Do not modify source files or rerun the live model.

## Outcomes & Retrospective

Scoped investigation complete: observed rainfall supports the earlier sequence, July 31 is the leading regional correspondence, and the remaining discriminator is actual dated Planet imagery. Saved event tables unchanged.

## Context and Orientation

Run /wc1/runs/th/thespian-cleanness; saved Daymet attempt 8190121c8a4b45e1952861e74d909693 and GridMET attempt f493a714df9d4fbfbfd4370c46ad54f8 under postfire_debris_flow/attempts. Original Daymet publisher CSV is retained in the preceding 20260917_dead_horse_daymet_audit package. Paper https://nhess.copernicus.org/articles/24/2093/2024/ and downloadable supplement provide timing context.

## Plan of Work

Write artifacts/analyze.py to read saved tables, check probabilities independently and export date comparisons; retain publisher raw data. Download and inspect the supplement for specific image dates. Use basin raster geometry to choose spatial screening locations and obtain Daymet daily data at those points. Write findings with evidence for and against candidate attribution.

## Concrete Steps

Run scripts through wctl exec weppcloud python from the repo root; downloads write only to this package. Use pdftotext for supplementary PDFs. Run wctl doc-lint --path docs/work-packages/20260917_dead_horse_storm_correspondence.

## Validation and Acceptance

Recompute probabilities from saved T/F/S and duration coefficients, verify table hashes before/after, report all candidate dates and durations. Document exact point selection and avoid claiming a sampled screen covers every pixel. Inspect available imagery evidence; if actual image scenes or gauge archives are inaccessible, retain access responses and state that gap without discarding the hypothesis.

## Idempotence and Recovery

No live writes. Retain failed/intermediate downloads; use successful retained inputs on repeats. Closed evidence packages are not edited.

## Artifacts and Notes

CSV comparisons, JSON hash/calculation receipts, raw supplemental files, spatial sample data and findings live under artifacts.

## Interfaces and Dependencies

Existing pandas, rasterio, pyproj, requests and plotting tools only. No new runtime dependencies.

Revision 2026-09-17 UTC: close after numerical, spatial, gauge and available-imagery checks. Missing continuous gauge/Planet scene evidence is a stated limit, not a rejected hypothesis.
