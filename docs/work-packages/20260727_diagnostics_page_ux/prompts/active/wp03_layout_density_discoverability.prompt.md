# WP03 — Diagnostics Card Density and Discoverability Wiring

> **Purpose**: Tighten the diagnostics page layout (denser cards, less vertical spacing) and make the page discoverable from the interfaces "More" dropdown for all users and from usersum.
> **Target**: Codex
> **Created**: 2026-07-27
> **Status**: Active

## Context

The diagnostics page renders two loose card shells with generous stacked spacing; the check list, readiness summary, and report controls sprawl vertically. Separately, nothing links to the page: the interfaces page (`wepppy/weppcloud/templates/interfaces.htm`) renders its "More" dropdown only for authenticated users — anonymous visitors get a lone Login link — and no entry in either state points at diagnostics. There is also no usersum end-user doc yet; Claude Code authors that doc in WP04, but this WP wires the page-side link once the doc's filename is settled.

- Current state: loose two-card layout; More menu auth-only with no diagnostics entry; page links to no documentation.
- Goal state: denser layout per the UI style guide; More dropdown rendered for anonymous and authenticated users with a Diagnostics entry in both; diagnostics page links to its usersum doc.
- Related work: WP01 (adds progress indicator and Re-run button to the same template — land WP01 and WP02 first; this WP styles the final composition), WP04 (usersum doc authoring).

## Objective

The page reads as one coherent, compact diagnostic surface: readiness summary, check list, report controls, and reset section visually tight, with check rows dense enough to scan the full roster without scrolling on a typical laptop viewport. Any visitor to the interfaces page — logged in or not — can find Diagnostics under More.

**Success looks like**: an anonymous user lands on wepp.cloud, opens More, clicks Diagnostics, and reads a compact page that links to its own documentation.

## Working Set

### Files to Read (Inputs)
- `docs/ui-docs/ui-style-guide.md` — spacing, card, chip, and density conventions; this bounds every styling decision
- `wepppy/weppcloud/templates/diagnostics/diagnostics.htm` — post-WP01/WP02 composition
- `wepppy/weppcloud/templates/interfaces.htm` — `header_nav` block structure for both auth states
- `wepppy/weppcloud/templates/controls/_pure_macros.html` — card shell macro and any denser variants
- `docs/ui-docs/diagnostics-page.spec.md` — layout contract to amend

### Files to Modify (Outputs)
- `wepppy/weppcloud/templates/diagnostics/diagnostics.htm` — consolidate/tighten: consider merging the intro and results shells or reducing the intro to a lede line; compact check rows (state chip, name, one-line evidence) rather than tall stacked blocks; keep the report preview collapsed by default
- Page-scoped styles wherever the diagnostics page currently sources them (template style block or the appropriate stylesheet per the style guide) — reduce stack gaps on this page without altering shared `wc-stack`/card primitives used elsewhere
- `wepppy/weppcloud/templates/interfaces.htm` — render the More dropdown for anonymous users too (keeping the Login link) and add a Diagnostics entry visible in both auth states, pointing at the diagnostics route
- `docs/ui-docs/diagnostics-page.spec.md` — amend layout and discoverability sections
- `tests/weppcloud/routes/test_diagnostics_page.py` and any interfaces-page route tests — assert the Diagnostics link renders for anonymous and authenticated responses

### Files to Reference (Dependencies)
- `wepppy/weppcloud/templates/base_pure.htm` — nav styling classes (`wc-nav__menu`, `wc-nav__menu-content`)
- Existing `usersum_doc_link` macro usage in `interfaces.htm` — pattern for linking usersum docs from templates
- `wepppy/weppcloud/static-src/tests/smoke/diagnostics/` — visual smoke specs that may assert on layout landmarks

### Files to Avoid (Exclusions)
- Shared UI primitives (`wc-stack`, card shell macro internals, chip styles) — density changes must be page-scoped; global spacing changes ripple across every pure-UI page
- Other templates' `header_nav` blocks — only `interfaces.htm` is in scope for nav changes
- `wepppy/weppcloud/routes/usersum/` content and manifests — WP04 owns doc authoring and registration

## Instructions

1. Read the style guide first; every density change must cite an existing convention rather than invent one.
2. Restructure the diagnostics template: single readiness header region, dense check list rows, report controls grouped on one line where the style guide permits, reset section compact. Preserve all data attributes, ARIA roles, and live-region semantics WP01/WP02 rely on.
3. Scope spacing overrides to the diagnostics page root so shared primitives are untouched.
4. In `interfaces.htm`, restructure the nav so the More dropdown exists in both auth branches: authenticated users keep their current entries plus Diagnostics; anonymous users get Login plus a More menu containing Diagnostics (or Diagnostics alongside Login if the style guide favors a flat link at that width — follow the guide).
5. Add the usersum doc link to the diagnostics page via the established macro, targeting the WP04 doc filename recorded in the package tracker (coordinate: if WP04 has not landed, use the agreed filename and note it in the tracker so WP04 matches).
6. Amend the spec's layout and discoverability sections.
7. Update route tests for the nav link in both auth states; refresh Playwright visual smoke expectations if landmarks moved.

## Validation Gates

- `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py`
- `wctl run-npm lint` and `wctl run-npm test`
- Manual in the dev stack: interfaces page as anonymous and authenticated (More menu present in both, Diagnostics entry works); diagnostics page renders compactly with WP01 progress and WP02 reset sections intact.

## Deliverables

1. Compact diagnostics layout consistent with the style guide, spec amended.
2. More dropdown with Diagnostics entry for all users on the interfaces page.
3. usersum doc link wired on the page.
4. Passing route tests covering both auth states.

## Handoff Format

Report per the package tracker's Progress Notes convention, including before/after screenshots in `artifacts/` if visual review is wanted.

---

## Outcome (Complete this when retiring the prompt)

**Completed**: YYYY-MM-DD
**Agent**:
**Result**:
**Deviations**:
**References**:
