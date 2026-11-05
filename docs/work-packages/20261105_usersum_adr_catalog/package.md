# Automatic ADR catalog in WEPPcloud Help

Status: contract checkpoint preparation; implementation not started.

## Purpose and scope

The operator requested a Usersum listing that automatically detects and renders
all ADRs newest first. Add a dynamic catalog and document view under the existing
Help shell, discovered from `docs/adrs/`, and expose links on the Help index and
sidebar. Preserve current Markdown rendering, source links and non-ADR access.
Ordering follows the original request: recorded dates descending, undated
records last, with numeric ID and filename tie breaks. No source ADR content is changed.

## Authority and execution

Current authority is the **Automatic ADR catalog** section of
`wepppy/weppcloud/routes/usersum/specification.md` (proposed, not implemented).
Execute `prompts/active/implementation_execplan.md`. The repository contract-first
standard requires two independent reviews and a committed checkpoint before
implementation. Commit authority for this new work package has not been granted;
prior commit/push requests concerned completed documentation edits.

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
acceptance evidence. Deployment is outside this request.
