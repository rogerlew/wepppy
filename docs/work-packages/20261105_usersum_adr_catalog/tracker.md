# ADR catalog tracker

## Progress

- [x] Inspect current Help routes, shell, publication contract and 138 ADR files.
- [x] Draft the bounded dynamic catalog contract and implementation plan.
- [x] Follow requested chronology: recorded dates descending, undated last; no
  invented dates or assumption that numeric order equals chronology.
- [x] Complete two independent contract reviews and record findings.
- [x] Independent correctness review confirmed link-contract and asset-scope fixes.
- [x] Both independent reviewers approve the revised contract; no blocking findings.
- [x] Operator authorized checkpoint; committed ancestor `0b804f1ff`.
- [x] Implement discovery, rendering, links and meaningful regression tests.
- [x] Validate all 138 rendered documents; 100 scoped tests, frontend gates and independent reviews pass.
- [x] Record incomplete broad runs and successful live forest recovery/readback.

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
Implemented and verified on forest: 100 scoped tests and 1,047 frontend tests
passed; all 138 live ADR documents returned HTTP 200. Both independent reviews
passed. Broad attempts stopped without failures (405 and 3,886 passes); neither
is a full-suite pass. Forest web reload repaired the reported stale-route 500.
See `artifacts/20261105_validation.md`. No production deployment.
Preexisting controller-validation edits and generated index changes are unrelated.

## Navigation follow-up

Operator-requested sidebar placement is verified on forest: Quick Start → ADRs
→ Feature Maturity and Release Governance. Contract checkpoint `6bedea271`
precedes the template edit; 100 existing focused tests pass. The apparent missing
records are all present but lack explicit dates (47 of 138). The operator selected date backfill; see the completed metadata follow-up below.

## Date backfill follow-up

- [x] Operator authorized backfilling missing dates.
- [x] Audited original decision/venue evidence for all 47 missing fields.
- [x] Added only explicit Date fields; all prior ADR content is preserved.
- [x] Parser and external HTTPS readback confirm 138/138 valid dates in exact
  chronological order, no unavailable dates, and all 47 updated detail pages
  returning HTTP 200 with their dates. No index rebuild or worker reload.

Evidence and per-record provenance: `artifacts/20261105_date_backfill.md`.

## Date enforcement follow-up

Completed the operator-requested hardening: `tools/check_adr_dates.py` uses the
catalog parser, fails missing/invalid dates with filenames and repair guidance,
and runs in Docs Quality CI. Authoring instructions and template reminders name
the local command. No hooks are installed; CI activation requires publishing the
change. All 138 records pass; 122 focused tests, generated-workflow parity,
documentation lint and independent correctness review pass. Evidence:
`artifacts/20261105_date_enforcement.md`.
