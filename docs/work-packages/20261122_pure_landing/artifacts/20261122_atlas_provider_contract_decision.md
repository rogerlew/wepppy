# Deck.gl Atlas provider and detail correction

Starting committed revision `5e668846260a145c63e3a3e41f57cb484a87276d`.
The operator asked to remove “Browse project locations and details” and
reported CARTO's API-key watermark on the Forest preview. Visual readback
confirmed the watermark even though tile requests returned HTTP 200.
[CARTO's key requirement](https://carto.com/basemaps/apikey/index.html).

The [landing contract](../../../ui-docs/contracts/pure-landing-contract.md)
keeps the approved section order, Deck.gl runtime, and absence of year
controls. It replaces the preview's CARTO raster endpoint with the Google
Terrain provider already used by WEPPcloud's Deck.gl pages. This reuses
the current renderer, shared tile factory and shared provider definition.
It avoids a new account, key, provider configuration or client library.
The legacy light landing retains its CARTO credit. Preview tiles use
the same fixed HTTPS Google template and subdomains as the shared map.

The project-details disclosure and its paging UI are removed. The map's
text summary, native zoom and reset, keyboard panning and Enter readout
retain nonvisual access to map information without a separate panel.
The shared [presentation contract](../../../ui-docs/controller-contract.md)
and [Forest Service credit and delivery contract](../../../ui-docs/contracts/forest-service-basemap-contract.md)
continue to apply. The existing table-overflow contract has no Atlas
table to govern after this change. Project authorization, publication
boundary, existing route URLs and application configuration keep their
current scope. The preview-only security impact is low because it
uses existing fixed external origins and public escaped row data.

Verify visually that actual geography renders on Forest and the
watermark is absent, exercise the new keyboard readout and confirm
the removed controls are absent. Verify theme styling, initial load,
failure and existing home and variant delivery.

## Independent reviews

Independent accessibility and compatibility reviews found no high
issues. The contract now names visible instructions, newest-first
project position, forward and reverse keyboard readout, and shared
tooltip fields. Check the actual fixed Google Terrain requests and
rendered geographic pixels, absence of cookies and preview referrers,
separate script and tile failures, and same map label treatment across
themes. A hardware assistive-technology pass remains part of acceptance.
