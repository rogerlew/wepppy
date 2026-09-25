# Daymet audit tracker

2026-09-17 UTC: closed; accepted attempt `8190121c8a4b45e1952861e74d909693`.

- [x] Scope read-only audit and pin target.
- [x] Verify Daymet owner/catalog, 45-year calendar, 14,025 result rows, event backlinks, ranks and source hashes.
- [x] Independently download publisher 2021 series; quantized rainfall matches every retained date.
- [x] Compare original synthetic PRISM, GridMET and Daymet assessments and paper window.
- [x] Verify authenticated report at all durations, five downloads, reload and no browser errors.
- [x] Preserve all 858 protected files and accepted manifest; no additions in tracked file classes.
- [x] Document confirmed units defect, CLIGEN warning, coverage and applicability limits.
- [x] Documentation lint passes; no runtime implementation or project mutation.

## Decision log

2026-09-17 UTC: new package, because prior audits are immutable history. No live rerun is needed to audit the already accepted Daymet result.

2026-09-17 UTC: inspect the publisher's original 2021 series because the retained parquet was found to contain mislabeled PRN units. This establishes date alignment without treating transformed values as millimeters.

2026-09-17 UTC: close audit with explicit findings, not a scientific validation claim. The source-parquet repair and upstream warning presentation remain follow-up work outside this read-only audit.

## Evidence and next action

See [findings](artifacts/findings.md), [comparison](artifacts/comparison.json), [numerical audit](artifacts/numeric_audit.json), and [closeout](artifacts/closeout.json). The next bounded implementation should prevent PRN serialization from changing retained Daymet source units and define treatment of existing mislabeled artifacts. No remediation was performed here.
