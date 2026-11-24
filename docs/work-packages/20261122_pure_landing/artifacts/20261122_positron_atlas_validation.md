# Production Atlas presentation on Forest

The [production basemap decision](20261122_production_basemap_contract_decision.md)
and [hillslope marker decision](20261122_atlas_hillslopes_contract_decision.md)
were committed before implementation. The Atlas on Forest uses the same
CARTO Positron style URL and MapLibre and Deck.gl rendering arrangement as
the working production landing. The production page was observed read-only.

The focused Flask suite passed all 25 tests. It checked the original
section order, metrics before the map, the zoom control names, absence of
the inspection paragraph and removed controls, and hillslope counters in
the serialized snapshot. Legacy digit strings normalize to integers.
Zero and unknown stay distinct.

Chromium loaded and painted actual Positron vector tiles and sprites on
Forest. The tile request used the approved source and omitted cookies and
referrers. The browser drew run IDs at practical zoom, maintained camera
alignment when panning, zooming and resetting, and contained the map at
mobile width. The Deck radius accessor produced displayed radii of
8 and 16 pixels for 64 and 256 hillslopes despite inverted access counts,
4 pixels for zero and unknown, and 60 pixels at the upper bound.

The production and Forest screenshots showed geographic features rather
than the earlier raster watermark. Axe reported zero violations in the
five AA themes. That result does not establish a keyboard or nonvisual
equivalent for individual labels and hover details. Manual acceptance
remains open before public cutover and UI Lab retirement.
