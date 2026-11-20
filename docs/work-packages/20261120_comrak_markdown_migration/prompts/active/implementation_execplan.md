# Comrak Markdown migration execution plan

## Purpose

WEPPpy should render Markdown with Comrak everywhere and let Python callers
opt into extensions. A successful migration keeps existing Usersum links
and headings, project README preview, and Browse documentation usable.

## Progress

- [x] Inventory renderer use and inspect published Python sources and wheels.
- [ ] Review and commit the durable contract.
- [ ] Implement the adapter, AST link integration, and complete dependency cutover.
- [ ] Follow the migrated routes and inspect rendered artifacts.

## Surprises & Discoveries

The plain Python binding bundles the vulnerable Comrak 0.54 release.
The extended binding bundles 0.59 and exposes editable links.
The two Python packages use the same import name.

## Decision Log

Use the extended binding as the single runtime dependency. Keep renderer
safety settings private to the shared adapter. Preserve existing heading
fragment semantics to avoid breaking saved links.

## Plan of Work

Update the canonical Markdown rendering contract. Implement a shared
adapter for rendering and AST link inspection and rewriting. Migrate
Usersum, the vendor graph and heading checker, project README, Browse
and Docs Quality. Compare the existing manual corpus, exercise every
affected route and verify the resulting dependency set from a clean
candidate runtime.

## Outcomes & Retrospective

Dependency discovery is complete. Implementation conformance is pending.
