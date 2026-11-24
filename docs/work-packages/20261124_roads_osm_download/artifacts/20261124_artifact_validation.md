# Artifact and workflow validation

The actual configured client fetched 26 mapped ways from the Swiss Overpass instance for longitude 8.539–8.541 and latitude 47.376–47.378 on 2026-11-24. The [17,763-byte GeoJSON](zurich-osm-roads.geojson) retains attribution and the OpenStreetMap copyright/license link. The standard endpoint reported a gateway capacity error during this session. The production default was preserved.

GDAL converted the download to a GeoPackage. An SQL edit assigned Inslope_bd and low traffic for this round-trip check only. Conversion back to GeoJSON preserved all 26 way IDs and original tag dictionaries, including fields that the GIS emitted as an object on export. This exercise does not represent a field survey of those roads.

The Flask multipart upload in an isolated WBT run accepted the edited GeoJSON. A detached Roads controller reopened the staged file, recognized DESIGN, SURFACE and TRAFFIC and resolved Inslope_bd and low traffic on every feature. The HTTP fixture supplied project context, test identity and retention bookkeeping; the Roads publisher, parsing, on-disk file and model attribute resolution were exercised. Receipt 5dc617f1a44545fcae7b15b0b5700fbb. The permanent HTTP regression uses a loopback interpreter and repeats the download after a populated upload to verify preservation.

Chromium exercised the rendered Roads template and production controller/HTTP helpers using a controlled response. Pressing Enter on the action started an osm-roads.geojson browser download with the expected contents. A second request returned empty, updated the status, and kept upload available. No page overflow at 920 or 390 CSS pixels. See the [visual review](20261124_correctness_review.md).
