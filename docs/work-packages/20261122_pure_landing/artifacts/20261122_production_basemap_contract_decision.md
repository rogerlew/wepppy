# Restore the production Atlas basemap and labels

Starting revision `d0a47929c`. The operator requested removal of the
inspection paragraph, on-map run ID labels, and the basemap already
working on the production landing.

A read-only browser run on the [production landing](https://wepp.cloud/weppcloud/)
confirmed render of CARTO Positron without labels using MapLibre under
Deck.gl. The original style, vector tiles and sprites returned successful
responses and painted actual geographic features. The earlier watermark
came from testing a CARTO raster endpoint. Restore the existing vector
style and shared locked renderer rather than adding credentials or
recreating its cartography.

The [landing contract](../../../ui-docs/contracts/pure-landing-contract.md)
retains the original section order, restores metrics above the Atlas map,
uses Deck.gl text labels for run IDs, restores the original lower-left
zoom/reset control group, and removes the Enter project cycle
and inspection paragraph. Keep map navigation, keyboard panning, readable
load/failure status and the geographic summary. Manual assistive-technology
acceptance remains part of the cutover gate.

The shared [presentation contract](../../../ui-docs/controller-contract.md)
and [Forest Service credit and delivery contract](../../../ui-docs/contracts/forest-service-basemap-contract.md)
remain applicable. The preview uses the existing local MapLibre assets
and sends only constrained requests to the same provider origins as
production. It introduces no new credentials, renderer library, public
data exposure, project authorization change, or configuration. Security
impact is low. The separate Forest Service provider keeps its own
resource boundary.

Verify real visible vector tiles, run ID text in Deck output, synchronized
pan and zoom, provider attribution and failure status. Confirm the
inspection paragraph and year/project disclosure controls are absent
and keep legacy landing responses available.

## Independent reviews

Two independent read-only reviews found no high issues. The preview
restricts production Positron resources to the observed provider style
and versioned tile, font and sprite patterns. Verification checks visible
geography, run IDs and camera alignment through pan, zoom, reset, and
resize. The separate Forest Service adapter keeps its own resource scope.
Both reviews flagged that aggregate text does not replace hover-only
individual project detail. The canonical contract records this as an
open manual Section 508 acceptance item without restoring the removed
controls or bypassing the preview gate.
