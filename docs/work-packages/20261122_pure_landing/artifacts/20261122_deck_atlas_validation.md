# Deck.gl Run Atlas preview validation

The reviewed [Deck.gl decision](20261122_deck_atlas_contract_decision.md) and
[provider and detail correction](20261122_atlas_provider_contract_decision.md)
govern this preview. It restores introduction, About and Run Atlas order.
The landing uses the standalone Deck.gl runtime plus WEPPcloud's existing
controller, raster tile factory and Google Terrain provider definition.
The year controls and browse-project disclosure and paging are gone.

The source review raised dateline placement, fatal canvas focus, severity
encoding and figure semantics. The implementation normalizes dateline
rendering only, hides map controls after renderer failure, adds a thicker
severity outline and matching plain text, and moves controls after the
figure. Tooltips and keyboard readouts identify unknown fields and report
the validated position. A server-rendered geographic summary and aggregates
remain available when the map cannot run.

All 25 focused preview and legacy route tests passed. The focused test
fixtures cover original order, the absence of controls, ignored old query
parameters, empty and malformed snapshots, polar positions in the summary,
and the safe public JSON allowlist.

The Forest preview uses the compiled public snapshot at the existing source.
The HTTPS bridge serves only the preview and its allowlisted assets.
Production and existing Forest landing variants retain their primary
routes. Temporary preview routing is held in the active development Caddy
configuration. The mounted development Caddyfile restores the pre-preview
routing on reload.

A browser render confirmed that the prior CARTO response contained a
watermark despite an HTTP 200. The revised screenshot shows terrain,
rivers, coastlines and project centroids. The preview makes no CARTO tile
requests and sends no cookies or referrers to the Terrain provider.

Chromium verified keyboard panning, forward and reverse project readout,
Tab exit, zoom, and responsive layout on the Forest page. All five
AA-validated themes had zero axe violations. Separate browser checks
blocked the Deck download and Terrain tiles and confirmed that readable
status, metrics and geographic summary survived both failures. Manual
assistive-technology acceptance and public cutover remain gated.
