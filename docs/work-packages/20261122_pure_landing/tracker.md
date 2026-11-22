# Pure CSS landing migration tracker

Started 2026-11-22 19:02 UTC.

- [x] Inventory current landing sections, theme patterns and shared assets.
- [x] Commit the contract checkpoint and review disposition.
- [x] Render and verify the initial review route.
- [ ] Reuse the Deck.gl Atlas and restore the original section order.
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
