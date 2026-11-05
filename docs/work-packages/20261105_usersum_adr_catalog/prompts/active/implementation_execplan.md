# Add an automatically discovered ADR catalog to Help

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users can open Architecture Decision Records from Help and read every numbered
record newest first without anyone editing a manual publication list. ADR means
Architecture Decision Record: a source Markdown file documenting a decision and
its context. Source files under `docs/adrs/` remain authoritative.

## Progress

- [x] (2026-11-05 UTC) Inspect repository ADRs and existing dynamic Help catalog.
- [x] (2026-11-05 UTC) Prepare specification and checkpoint proposal.
- [x] (2026-11-05 UTC) Two independent reviews recorded; link-rule gaps amended.
- [x] (2026-11-05 UTC) Both reviewers approve revised date ordering and contract.
- [x] (2026-11-05 UTC) Operator approved; checkpoint committed as `0b804f1ff`.
- [x] (2026-11-05 UTC) Implemented workflow; 100 focused tests and all 138 ADR renders pass.
- [x] (2026-11-05 UTC) Independent correctness/security reviews pass; Review Date finding closed.
- [x] (2026-11-05 UTC) Record incomplete broad gates and live forest acceptance.
- [x] (2026-11-05 UTC) Repair reported Help 500 with graceful web reload; all 138 live ADRs return 200.

## Surprises & Discoveries

Forest bind-mounted templates update independently of Gunicorn route imports.
A new shared-template endpoint link can break existing Help until workers reload;
unit tests alone did not expose this live cutover issue.

There are 138 matching ADR files. Dates appear as plain/bold metadata, status
paragraphs, provenance sections or are absent. Numeric filenames are the stable
sortable convention documented in `docs/adrs/README.md`, but ADR-0028 GridMET
is dated after ADR-0029: numeric order is not necessarily date order. Help has a dynamic
Feature Catalog, but generic source rendering can require manifest membership.

## Decision Log

The full pytest command was attempted, then interrupted in the unrelated slow
native 100-year simulation matrix after 405 passes and 27 skips. Use the broad
suite excluding tests explicitly marked slow and report the full gate incomplete,
as permitted by the nearest WEPPcloud instructions.

Use the existing dynamic Help pattern, direct file discovery on each request and
dedicated detail routes. This avoids stale generated lists and preserves generic
source-route guards. Use explicit preamble Date descending, with unavailable dates last and numeric
ID/filename descending as tie breakers. This follows the original chronological
request after review demonstrated that numeric order alone is not chronological.

## Outcomes & Retrospective

Implemented dynamic discovery, chronological listing, full Markdown views and
Help navigation. All 100 focused tests and 1,047 frontend tests pass; independent
reviews are clear. Broad runs stopped after 405 and 3,886 passes without observed
failures, but remain incomplete. Details: `artifacts/20261105_validation.md`.

The operator reported a live forest Help 500: templates loaded before Python
route registration. Gracefully reloading the verified Gunicorn master restored
Help. External HTTPS readback confirmed the index, catalog, all 138 ADR documents
and existing Getting Started page. Durable guidance now requires coordinated
route/template rollout and external readback. No production deployment.

## Context and Orientation

`wepppy/weppcloud/routes/usersum/usersum.py` owns the Flask blueprint, shell helper,
Markdown renderer and relative-link rewriting. Templates are in that directory's
`templates/usersum/`; `index.htm` and `layout.j2` provide discovery. The canonical
`specification.md` now contains the proposed Automatic ADR catalog section.
`tests/weppcloud/routes/test_usersum_bp.py` supplies a real Flask test client and
role seams. `tests/weppcloud/test_usersum_template_wiring.py` checks shell wiring.

## Plan of Work

First finish the mandatory contract checkpoint: review the specification with
two independent read-only reviewers, record findings and disposition, obtain
permission to commit, and commit only this package, the specification and this
package's project-board entry. Record that ancestor before any runtime edit.

Then add a small source-directory discovery helper and dedicated catalog/detail
GET routes. Match direct numbered Markdown files, preserve all matching files,
sort by explicit preamble Date with undated records last, extract a display H1 with filename fallback and render
full documents using existing helpers. Keep path containment and symlink checks
central to both discovery and detail. Rewrite eligible cross-ADR Markdown links
to the dedicated route while preserving other resolution. Reuse existing raw and
GitHub links. Add the listing template and standalone Help index/sidebar links.
Do not touch generated index or per-file manifest rows.

Write focused regressions before implementation. Use actual temporary files for
filesystem boundaries, then verify every actual repository ADR with the Flask
renderer. Update developer/user guidance about discovery/order. Run the prescribed
gates, review correctness independently and update this plan and tracker.

## Concrete Steps

From `/home/workdir/wepppy`, use `wctl run-pytest` for scoped Usersum route and
shell tests. Add meaningful fixture tests for discovery and path safety. Run
`wctl run-npm lint`, `wctl run-npm test`, and
`wctl run-pytest tests --maxfail=1` for final substantive-code validation. Run
`wctl doc-lint --path <changed-document>` and spelling previews for prose edits.
Record real results instead of predicted passing counts.

## Validation and Acceptance

At `/usersum/adrs/`, observe every valid source record once, in recorded-date descending
order with undated records last, with a link that renders its full Markdown. Read all 138 current documents
through actual routes. A temporary added ADR appears on the next request; editing
or removing it changes the next response. Missing/empty roots yield an explicit
empty page, while traversal/symlink targets never expose content. Dates and H1
omissions must not hide legacy records. Test date/ID inversions, invalid dates, duplicate IDs, escaped titles,
strict-manifest settings, anonymous and privileged users, site-prefix URLs,
cross-ADR links and preserved non-ADR role guards. Confirm navigation is visible
outside curated sections and changes require no generated-index update.

## Idempotence and Recovery

All new routes are read-only; source files remain authoritative. Revert the
bounded code/templates to remove the feature. No migrations, stored copies,
queue changes or production operations are needed. Preserve unrelated dirty
files and do not change branches. Stage shared project-board edits by hunk.

## Artifacts and Notes

Record checkpoint and review evidence under this package's `artifacts/`.
Record the ancestor revision in `tracker.md`; keep implementation and deployment
claims separate. A generated HTML response, not a file-existence assertion,
establishes that readers can use the listing and open the records.

## Interfaces and Dependencies

Use Python standard-library pathlib/regular expressions and existing Flask,
Jinja and cmarkgfm facilities. No new dependencies. New routes:
`GET /usersum/adrs/` and `GET /usersum/adrs/<filename>`.
Existing raw-source route remains usable under its existing contract.

Revision note (2026-11-05 UTC): initial bounded plan and contract proposal.

Revision note (2026-11-05 UTC): independent review exposed numeric/date inversions;
use explicit recorded dates to honor the original chronological request.

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

## Date enforcement hardening follow-up

Operator request: prevent recurrence after 47 of 138 ADRs omitted explicit dates.
Scope: enforce the existing explicit-date authoring convention in a local CLI
and the existing Docs Quality job, using the unchanged catalog parser. Document
it beside the template and in local ADR authoring instructions. No publication,
ordering, access, runtime renderer, hook installation or dependency changes.

- [x] Confirm template/generic Markdown lint did not enforce ADR metadata.
- [x] Identify existing Docs Quality spec/generator and catalog parser for reuse.
- [x] Add failing regression coverage, bounded checker and CI invocation.
- [x] Update authoring instructions and template reminder.
- [x] Validate good/bad real files, all 138 ADRs and generated workflow parity.
- [x] 122 focused tests, documentation lint and independent correctness review pass.

Current package and date-backfill artifacts supply failure evidence. Precedents:
markdown-doc adoption's Docs Quality job, root AGENTS size gate, and the Usersum
catalog parser. Add one metadata check because generic Markdown lint accepts
missing/placeholder dates. This is a permanent authoring invariant, not a retry,
compatibility shim or temporary mitigation; no sunset flag is needed. Gate health
is 138 valid records; danger is any numbered ADR lacking a recognized valid date.
Rollback removes the checker CI step without modifying ADRs or runtime access.

Broad native suites were already attempted and stopped for this package; this
bounded tooling follow-up uses focused checker and existing Usersum tests plus
CLI and workflow-generation readback, with no full-suite pass claimed.
