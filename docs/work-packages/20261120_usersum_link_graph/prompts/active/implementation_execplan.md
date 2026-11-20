# Usersum vendor link graph execution plan

## Purpose

When a guide links to another committed Markdown page in its source repository,
the built Usersum manual should open the linked page. Diagnostics should name
missing files and unresolved fragments so authors can repair upstream links.

## Progress

- [x] Audit source links and prototype AST link rewriting.
- [ ] Complete the contract checkpoint and independent reviews.
- [ ] Implement traversal and Docs Quality integration.
- [ ] Exercise real vendor artifacts and render linked routes.

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

The initial audit is complete. Implementation results are pending.
