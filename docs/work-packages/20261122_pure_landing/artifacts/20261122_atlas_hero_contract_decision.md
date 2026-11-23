# Run Atlas hero correction

Starting revision `2e4c3a081`. The operator clarified during Forest review
that the Run Atlas is meant to be the hero visual. This authorizes correcting
the preview presentation. Public home cutover and UI Lab retirement remain
subject to their separate human approval gate.

The [landing contract](../../../ui-docs/contracts/pure-landing-contract.md#run-atlas)
supersedes the table-only presentation. The shared
[controller contract](../../../ui-docs/controller-contract.md),
[overflow contract](../../../ui-docs/contracts/table-overflow-discoverability-contract.md)
and [Forest Service credit and delivery contract](../../../ui-docs/contracts/forest-service-basemap-contract.md)
still apply. No other domain, production route, auth behavior or data contract
changes.

The visual is a bundled transparent land silhouette from Natural Earth
1:110m physical vectors and coarse project clusters rendered with Jinja and
CSS. This keeps the map visible and responsive without client map code or
external tiles. The year filter affects the visual and text details. Pagination
affects only which project rows are shown. The details disclosure provides
coordinates and project fields in an accessible form. Basemap credit is
shown on the preview and the existing provider credits remain in their
actual scope. [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/).

Compatibility impact is limited to the review page and its filter anchor.
The read-only snapshot, path, fields and run authorization are unchanged.
The new chart derives only bounded numeric positions and counts. It makes no
external requests and creates no new client-controlled URL or markup. Security
impact is low.

Verify geographic enrollment and boundaries against synthetic fixture coordinates,
marker stability across pagination, and empty, malformed, hostile and supported
legacy snapshot states. Verify the full-size and narrow hero across the five AA
themes, keyboard filter and disclosure navigation, no-script rendering and axe.
Check the existing Forest HTTPS review route and home after refreshing preview
assets.

## Independent reviews

Independent accessibility and compatibility reviews on 2026-11-22 UTC
found no high issues. The contract requires a text description, visible
size key, selected-run counts in four geographically defined quadrants,
and open disclosure on all pagination links including page one. The
shared 2:1 projection and edge behavior are explicit. Tests cover
known coordinates, invalid numbers, marker visibility, and no-script
navigation. Retain source and transformation provenance for the bundled
asset and verify the Forest route and existing landings after activation.
