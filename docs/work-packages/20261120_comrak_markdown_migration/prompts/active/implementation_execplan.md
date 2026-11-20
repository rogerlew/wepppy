# Comrak Markdown migration execution plan

## Purpose

WEPPpy should render Markdown with Comrak everywhere and let Python callers
opt into extensions. A successful migration keeps existing Usersum links
and headings, project README preview, and Browse documentation usable.

## Progress

- [x] Inventory renderer use and inspect published Python sources and wheels.
- [x] Review and commit the durable contract at `4d9d7416b`.
- [x] Implement the adapter, AST link integration, and complete dependency cutover.
- [x] Follow the migrated routes and inspect rendered artifacts.

## Surprises & Discoveries

The plain Python binding bundles the vulnerable Comrak 0.54 release.
The extended binding bundles 0.59 and exposes editable links.
The two Python packages use the same import name.
Ordinary repeated renders exposed an AST retention issue in the extended
binding. The adapter releases native parent references before callback
execution and matches direct HTML output after doing so.

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

The focused container run passed 363 tests. All 152 manual pages retain
their published heading IDs and link sequence. A 1,000-render and
inspection run showed stable memory after warm-up. The repository-wide run excluding slow-marked tests passed 14,033 tests.
