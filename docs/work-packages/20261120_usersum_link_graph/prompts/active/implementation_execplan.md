# Usersum vendor link graph execution plan

## Purpose

When a guide links to another committed Markdown page in its source repository,
the built Usersum manual should open the linked page. Diagnostics should name
missing files and unresolved fragments so authors can repair upstream links.

## Progress

- [x] Audit source links and prototype AST link rewriting.
- [x] Complete the contract checkpoint and independent reviews at `3aae1556e`.
- [x] Implement traversal and Docs Quality integration.
- [x] Exercise real vendor artifacts and render linked routes.

## Surprises & Discoveries

The current sync uses working-tree files and ignores the configured ref. The
WBT checkout uses `master`. Comrak default heading IDs differ from Usersum IDs
on 19 of 72 files in a smoke comparison.

## Decision Log

The operator authorized publishing reachable committed pages. Retain Usersum's
heading IDs and check those IDs in Docs Quality to preserve existing deep links.

## Plan of Work

Read the canonical Usersum specification in
`wepppy/weppcloud/routes/usersum/specification.md`. Resolve vendor refs and
walk Markdown links in the committed trees. Share heading ID generation with
Docs Quality. Validate cycles, missing targets, working-tree-only files,
existing role checks, and rendered links to copied pages. Run the actual
vendor command and inspect a linked WBT artifact and its rendered URL.

## Outcomes & Retrospective

The real build copied 94 pages from three vendors. Blob readback verified
every page against its authoritative commit. The heading and link check
reported one missing cross-repository WEPP Forest target. The isolated
focused test suite passed 123 tests. The full suite requires a runtime
with both configured native parser artifacts. The borrowed browser runtime passed preflight.
