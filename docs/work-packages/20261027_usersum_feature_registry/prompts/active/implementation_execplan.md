# Implement the public Usersum feature catalog

## Purpose and Scope


Visitors should see every registered WEPPcloud feature and interface with its
maturity classification without signing in. Visit `/weppcloud/usersum/features/`
after deployment; the Usersum home page will link there. Metadata is public,
including Internal entries, but displaying it grants no feature permissions.

## Progress


- [x] Inspect Usersum Jinja precedent and registry loaders.
- [x] Scaffold package and amend current contracts before code.
- [x] Obtain two independent contract reviews and disposition findings.
- [ ] Obtain commit authority and create standalone contract ancestor.
- [ ] Implement route, template, discovery link, and supporting docs.
- [ ] Validate rendered output, run gates, and close review findings.

## Surprises & Discoveries


Usersum already renders its index and search with Jinja through
`_render_with_usersum_shell`. Registry loaders provide validated dataclasses;
config loader applies maturity overrides. No new Markdown templating pipeline
is needed. Existing unrelated query-catalog edits must be preserved.

## Decision Log


2026-10-27 UTC: Public information is independent of runtime authorization,
per explicit operator instruction. Reuse live loaders and Jinja to avoid stale
metadata copies. Include configurations in a separate table because maturity
classification applies to both. The existing role selector affects document
navigation only, never registry rows. Do not add curated section entries.

## Context and Orientation


Work from `/home/workdir/wepppy`. Read local AGENTS files. Authoritative new
sections are Public Feature Catalog in
`wepppy/weppcloud/routes/usersum/specification.md` and Public Metadata Catalog
in `wepppy/weppcloud/feature_registry/specification.md`.
Implementation belongs in `wepppy/weppcloud/routes/usersum/usersum.py` and
`templates/usersum/` within that directory. Existing index/search templates
extend the shared Usersum shell. Registry data comes from
`wepppy/weppcloud/feature_registry/runtime.py` functions
`load_feature_registry()` and `load_config_registry()`.

## Milestones and Concrete Steps


First review the contract decision artifact and the two amended specifications
with two independent read-only reviewers. Resolve findings, then obtain explicit
commit authority and commit only checkpoint documents as a standalone ancestor.
Record the revision in tracker.md before implementation. Do not stage unrelated
working-tree changes, including preexisting PROJECT_TRACKER edits.

Second add GET `/usersum/features/` to the Usersum blueprint (no blueprint
prefix). Pass both validated collections to a new Jinja template through
`_render_with_usersum_shell`. Use the existing shell, semantic tables with
captions/header scopes, maturity pills, and responsive table patterns. Escape
all metadata. Explain role-or-group versus group-only access accurately; include
optional reason/date, prerequisites and replacement metadata. Link maturity
definitions with URL helpers. Add a Usersum index link outside curated nav
sections and describe the page in the user guide and developer authoring guide.
No JavaScript or generated search-index mutation is needed.

Third extend `tests/weppcloud/routes/test_usersum_bp.py` and
`tests/weppcloud/test_usersum_template_wiring.py` after reading tests/AGENTS.md.
Test anonymous rendering, identical rows under role filters, complete real
registry coverage, effective config maturity, group policy, empty collections,
escaping, and prefix-safe links. Keep at least one real loader/renderer test.
Run `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py tests/weppcloud/routes/test_feature_registry_runtime.py`,
then `wctl run-pytest tests --maxfail=1`, `wctl run-npm lint`, and
`wctl run-npm test`. Lint changed docs with `wctl doc-lint --path <file>`.
Retain direct HTTP HTML evidence and final independent correctness/security
reviews in artifacts, using repository review templates. Record limitations
honestly and update package, plan, tracker, and root board before handoff.

## Validation and Acceptance


Anonymous HTTP returns 200 and all feature/config ids in source order. Roads
shows Experimental and PowerUser. Internal and group-only entries are present;
group-only labels do not promise role-based entitlement. Config maturity agrees
with runtime overrides. Empty state is explicit, malformed loader input fails
rather than producing a partial success, and hostile text remains escaped.
No run initialization or membership lookup is introduced. Browser inspection
checks readable tables at narrow widths and keyboard-accessible links.

## Idempotence and Recovery


Changes are additive source edits; no migration or production mutation is
required. Repeat tests safely. Revert only this package's edits to remove the
page. Never reset unrelated dirty files. Production rollout remains separate.

## Artifacts and Interfaces


Contract decision and review dispositions live under artifacts/. The route
consumes existing immutable FeatureSpec/ConfigSpec objects; no schema changes
are needed. Current shell APIs and URL helpers own rendering/prefix behavior.

## Outcomes & Retrospective


Checkpoint prepared and approved by two independent reviewers. Documentation lint passes. Route implementation and validation pending required commit authority.

Revision note: 2026-10-27 UTC, initial plan and contract checkpoint prepared from
operator-approved public catalog intent; commit authority remains outstanding.
