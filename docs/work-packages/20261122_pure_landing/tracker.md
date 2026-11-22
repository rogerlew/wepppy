# Pure CSS landing migration tracker

Started 2026-11-22 19:02 UTC.

- [x] Inventory current landing sections, theme patterns and shared assets.
- [x] Commit the contract checkpoint and review disposition.
- [x] Render and verify the initial review route.
- [x] Reuse the Deck.gl Atlas and restore the original section order.
- [ ] Complete manual screen-reader and assistive-technology acceptance.
- [ ] Obtain human acceptance before cutover and UI Lab retirement.

[Package](package.md) · [Execution plan](prompts/active/implementation_execplan.md) · [Contract decision](artifacts/20261122_contract_decision.md)

The 2026-11-22 inventory found the Forest Service renderer loading from
`static/ui-lab/maplibre/`. Preserve and verify it as part of final cutover.

Contract checkpoint `b3497a19c7b50597d117543cf055e3020e11f394` is the
pre-implementation ancestor. Record the search-indexing policy for atlas
rows on public home HTML in the human-approved cutover disposition.

## Local review

At 2026-11-22 19:19 UTC the isolated WEPPcloud app served
`http://127.0.0.1:18102/weppcloud/landing/preview/` with synthetic atlas
records. The current home and UI Lab routes continued to serve their
existing content. The local preview needs the ordinary Pure CSS shell
assets and has no new environment flag.

Focused pytest passed 333 cases. A final landing-only run passed 24 cases
after adding aggregate readback assertions. Frontend lint, 1,109 Jest
tests, nine Node tests and file-level Markdown lint passed. The broad
preflight stopped before collection because the local image lacks Comrak
and the shape and GeoParquet parser provenance. The isolated preview
instance mounted the pinned Comrak package for the browser run.

[Review findings and browser evidence](artifacts/20261122_correctness_review.md).

The operator's Atlas feedback supersedes the table-only presentation.
The [hero correction](artifacts/20261122_atlas_hero_contract_decision.md)
records the new contract and local review scope.

The CSS-map preview was declined. The operator requested the existing Deck.gl
map, no year controls and the original section order.

CARTO's raster endpoint returned API-key watermark images with HTTP 200.
The operator asked to remove the project browser. The Deck.gl preview uses
WEPPcloud's existing Google Terrain basemap and drops the disclosure.


The Deck.gl preview is live on [Forest](https://forest.tail305ec9.ts.net/weppcloud/landing/preview/).
It uses Forest's compiled public atlas snapshot. The original section order,
Deck.gl reuse, absence of year controls, and removal of the disclosure are
covered in the focused suite. Checkpoints `5e6688462` and `6e4295d88`
precede the implementation. [Verification](artifacts/20261122_deck_atlas_validation.md).

The operator asked to remove the inspection paragraph, draw run IDs on the
map, and restore the production landing basemap. Production rendered CARTO
Positron vector tiles successfully. This supersedes the Terrain preview.

Forest now renders the same Positron vector basemap as the production
landing, with run ID labels and the original lower-left zoom controls.
The metrics are above the map and marker area follows hillslope count.
The inspection paragraph is removed. Checkpoints `16234b319` and
`051eb80ed` precede the correction.
[Rendered evidence](artifacts/20261122_positron_atlas_validation.md).

Checkpoint `d81dafd64` governs the [Atlas wheel gesture and map overlays](artifacts/20261122_atlas_wheel_decision.md).
Chromium on Forest verified native page scrolling and Ctrl-wheel zoom on
the canvas and through the legend and tip, synchronized Deck and basemap
zoom, and uncanceled Ctrl-wheel outside the map. The tip clears the zoom
buttons at 1200, 390 and 320 CSS pixels. Both landing route suites passed
(25 tests).

The [publication review](artifacts/20261122_atlas_publication_security_review.md)
records verification of checkpoint `b69fa6e4c`. Only explicitly public
projects enter a newly compiled Atlas. Normal deployment and the subsequent
successful scheduled compilation roll this into the served feed.

The [design review disposition and Forest verification](artifacts/20261122_design_review.md)
cover checkpoint `05f86c5b2` and its responsive presentation changes.

[Shared masthead decision and verification](artifacts/20261122_shared_header_decision.md)
supersedes the design review's custom header. Contract checkpoint `0489ef246`.

[Direct navigation and mobile hamburger](artifacts/20261122_navigation_decision.md)
supersedes the More menu disposition. Contract checkpoint `67447cc29`.

The [text introduction](artifacts/20261122_intro_decision.md) replaces the
illustrated hero on Forest. Contract checkpoint `738d78146`.

[Plain link labels and decoration](artifacts/20261122_link_decision.md)
were verified on Forest following checkpoint `76bb04deb`.

[Semantic parity and link verification](artifacts/20261122_semantic_parity.md)
covers checkpoint `c7b2bc3d7`.

[Visible funding, credits and disclaimer](artifacts/20261122_visible_references.md)
records Forest verification following contract checkpoint `3ede01d55`.

[Affiliation cards and original captions](artifacts/20261122_affiliation_cards.md)
were verified on Forest following checkpoint `4d0e254dd`.

[Help and resources marks](artifacts/20261122_resource_marks.md) were verified
on Forest following contract checkpoint `25d1b44a4`.

[WEPPcloud Stack directory](artifacts/20261122_stack_directory.md) covers the
twelve repositories selected under checkpoints `51aedcb8e` and `2eedf3a64`.
