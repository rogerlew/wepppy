# Reuse the Deck.gl Run Atlas

Starting committed revision `eb09284769708d1b53438e6d10e820b79327990f`.
The temporary Forest preview also served a working-tree CSS map. The
operator rejected it and explicitly requested reuse of the Deck.gl map,
removal of access-year controls, and original content order.

The [landing contract](../../../ui-docs/contracts/pure-landing-contract.md)
supersedes the CSS map decision for the preview. Keep the original light
landing's section sequence and restore the Atlas as the main visual after
About. Keep the data and keyboard-accessible equivalent. Reject the CSS
silhouette, a second renderer, and a React application embedded in Jinja.
Use the Deck.gl 9 distribution already used on Runs, the owned map and
raster tile helpers already used by WEPPcloud, and the existing light
Atlas CARTO provider. Standalone Deck draws CARTO raster tiles and the
same types of centroid and label overlays. Landing CSS still follows the
shared presentation contract.

The [controller contract](../../../ui-docs/controller-contract.md),
[overflow contract](../../../ui-docs/contracts/table-overflow-discoverability-contract.md)
and [Forest Service credit and delivery contract](../../../ui-docs/contracts/forest-service-basemap-contract.md)
still apply. The legacy home, UI Lab variants, run and dashboard basemaps,
published snapshot, auth and model behavior keep their current scope.
The preview adds a browser integration with approved existing resources.
Security impact is low. Tile URLs are fixed to the CARTO provider and
validated numeric tile indexes. Existing public row fields are escaped as
JSON and tooltip text. No auth or run links are forwarded to map providers.

Verify source order and absence of year controls, actual raster and
Deck canvas rendering, pan and accessible zoom, theme updates, empty and
unavailable map states, and no-script project detail access. Recheck the
Forest preview and existing landing variants. The public cutover remains
subject to human approval.

## Independent reviews

Two independent read-only reviews on 2026-11-22 UTC found no high
issues. Addressed the accessibility review by specifying named keyboard
panning, zoom and reset, a normal Tab exit, truthful HTML fallback,
visible marker legend and text equivalents. Addressed the compatibility
review by naming the fixed provider URLs, referrer and credential
boundary, viewport readiness and failure, theme camera preservation,
and handling of valid polar coordinates. The acceptance wording now
identifies the Atlas as the main visual after About.
