# ADR-0159: Include mapped vehicular roads in default terrain hydroenforcement

Status: Accepted for local implementation
Date: 2026-11-24

## Decision and rationale

Use one default list of mapped vehicular centerlines for the Roads download and TerrainProcessor. Add motorway, trunk, primary, secondary and tertiary links, service roads, living streets and roads of unknown class to the previous motorway, trunk, primary, secondary, tertiary, residential, unclassified and track selection. A service road on private land can cross a stream. Retain access-restricted ways and disconnected lines. Exclude area=yes features. Give the new query a separate cache identity because older tiles can contain areas with the original area tag discarded.

A blanket highway query would include steps and footways. Assuming road surface or drainage design from highway class would introduce unsupported model inputs. Preserve user-supplied terrain class lists and apply the existing Roads surface aliases only to tagged material.

## Decision provenance

The WEPPpy operator requested expanded road acquisition for hydroenforcement and a downloadable model input in the 2026-11-24 Pacific Codex session. Codex implemented the selection and the operator-requested contract-first package. The change can affect the crossings found when terrain processing is run again. To reproduce an earlier result, retain the original road input and project settings. Reverting the selection and cache identity restores the previous acquisition behavior.

## Evidence

[Download contract](../schemas/roads-osm-download-contract.md) and [work package](../work-packages/20261124_roads_osm_download/package.md).
