# ADR catalog tracker

## Progress

- [x] Inspect current Help routes, shell, publication contract and 138 ADR files.
- [x] Draft the bounded dynamic catalog contract and implementation plan.
- [x] Follow requested chronology: recorded dates descending, undated last; no
  invented dates or assumption that numeric order equals chronology.
- [x] Complete two independent contract reviews and record findings.
- [x] Independent correctness review confirmed link-contract and asset-scope fixes.
- [x] Both independent reviewers approve the revised contract; no blocking findings.
- [ ] Obtain checkpoint commit authority and record the ancestor revision.
- [ ] Implement discovery, rendering, links and meaningful regression tests.
- [ ] Validate generated HTML, scoped/broad gates and independent correctness review.

## Decision log

- Use the existing dynamic Feature Catalog pattern rather than manual manifest
  entries. Every new ADR should appear without a publication-maintenance step.
- Use a dedicated fixed-directory detail route so source-manifest strict mode
  remains unchanged. Preserve existing role gates on unrelated documents.
- Date order follows the operator's original chronological requirement. Read only
  explicit preamble Date fields; missing/invalid dates remain visible and sort last.
  Numeric ID and filename are deterministic tie breakers, not date substitutes.

## Evidence and outcome

Both independent contract reviews passed after date-order and link-rule
amendments. The operator authorized the checkpoint commit and implementation on 2026-11-05. See `artifacts/20261105_review_disposition.md`.
No implementation or deployment yet.
Preexisting controller-validation edits and generated index changes are unrelated.
