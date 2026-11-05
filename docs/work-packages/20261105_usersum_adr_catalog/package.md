# Automatic ADR catalog in WEPPcloud Help

Status: implemented, independently reviewed and verified on forest. Broad
suites attempted but incomplete; scoped and live workflow acceptance passed.

## Purpose and scope

The operator requested a Usersum listing that automatically detects and renders
all ADRs newest first. Add a dynamic catalog and document view under the existing
Help shell, discovered from `docs/adrs/`, and expose links on the Help index and
sidebar. Preserve current Markdown rendering, source links and non-ADR access.
Ordering follows the original request: recorded dates descending, undated
records last, with numeric ID and filename tie breaks. The original implementation
preserved source content; the operator subsequently authorized explicit date
metadata backfill, recorded in `artifacts/20261105_date_backfill.md`.

## Authority and execution

Current authority is the **Automatic ADR catalog** section of
`wepppy/weppcloud/routes/usersum/specification.md` (approved checkpoint).
Execute `prompts/active/implementation_execplan.md`. The repository contract-first
standard requires two independent reviews and a committed checkpoint before
implementation. The operator authorized the checkpoint commit and implementation on 2026-11-05.
Checkpoint ancestor: `0b804f1ff`.

## Complexity and security

Budget: one small discovery helper, two GET routes, existing Markdown-link
routing integration, one listing template and two navigation links, scoped tests
and documentation. No dependency, service, queue, datastore, role mutation,
background synchronization or deployment change. Full-text search enrollment and
rewriting old ADR metadata are excluded.

Security impact: low, public repository files through a fixed directory and
strict filename/path checks. Preserve manifest role gates outside this explicitly
public ADR surface. Review traversal, encoded paths, symlinks and title escaping.
A dedicated high-impact security workstream is not required; independent contract
and correctness reviews must cover the bounded filesystem surface.

## Acceptance and evidence

All eligible repository ADRs appear once in deterministic newest-first order.
Opening each link renders its complete Markdown. Adding/editing/removing a
fixture ADR is reflected without index regeneration or process reload. Empty
sources are explained; malformed content errors explicitly. Canonical and
prefix-aware links work, anonymous readers can use the page, and source-manifest
strict mode does not break the dedicated ADR workflow or relax other routes.
Read rendered HTML to establish these outcomes; job/file existence is not
acceptance evidence. Production deployment is outside this request.

## Forest recovery

During implementation, fresh shared templates referenced the new route before
the development web workers loaded it, causing the operator-reported Help 500.
A scoped graceful web-worker reload restored Help and activated the catalog.
External readback covered the index, all 138 ADRs and an existing help document.
See `artifacts/20261105_validation.md` for evidence and test limitations.

## Date authoring enforcement

After the 47-record backfill, the operator requested prevention. The authoring
rule and local command are in `docs/adrs/README.md` **Required Date Check** and
`docs/adrs/AGENTS.md`. The checker shares the catalog parser and is wired into the
existing Docs Quality job; it rejects absent, placeholder and invalid dates.
No runtime publication behavior changes. See `artifacts/20261105_date_enforcement.md`
for failure-class assessment, validation and review.
