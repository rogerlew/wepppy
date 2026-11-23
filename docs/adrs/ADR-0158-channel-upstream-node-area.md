# ADR-0158: Restore cumulative upstream-node drainage area for channel geometry

Status: Accepted  
Date: 2026-11-22

## Context

On diagonal-intersection, WBT reported 195,300 m² of lateral hillslope area at the outlet reach. Peridot consequently supplied a 0.6 m WEPP channel width. SWAT+ also used channel surface area for drainage and could join network rows by an unrelated ordinal.

## Decision and rationale

Retain the TOPAZ field name `areaup`. It measures all channel and overland inflow into the reach's upstream cell, in square meters. Exclude the receiving cell. Compute it over the masked D8 flow graph. This restores the original TOPAZ UPSTR. definition for headwaters and confluences. Basin totals, downstream endpoints and the reach's lateral subcatchments describe different areas.

Peridot converts square meters to square kilometers and uses the existing Rocky Mountain Bieger relation, width in meters = max(0.324017, 1.24 × area_km²^0.435). WEPP retains its slope-file rounding and configured minimum.

SWAT+ joins the network to channel geometry by TOPAZ identifier. It uses drainage area in hectares in chandeg.con and square kilometers for the configured hydraulic regressions. A zero-contributor headwater has zero drainage area. Retain the existing 1 km² hydraulic calculation default for that case to generate positive geometry. Reject a missing, negative or nonfinite drainage area before generating a channel with invented geometry. Historical network header aliases and explicit unit overrides remain supported.

## Decision provenance

The WEPPpy operator approved restoring the original field contract and including SWAT+ during the 2026-11-22 Pacific Codex work session (implementation logged 2026-11-23 02:59 UTC onward). Decision owner: WEPPpy operator. Implementer: Codex.

## Consequences and recovery

Network keys and units remain compatible. Corrected values change model inputs, including channel surface area and resulting modeled watershed area. A legacy WBT table has the same header and requires regeneration. Rebuild WBT network and Peridot abstraction together, then prepare WEPP inputs and rebuild SWAT+ TxtInOut before rerunning affected models. Preserve previous run inputs and outputs together for comparison or rollback. An input-width correction alone cannot certify predicted flows or sediment yields.

## Evidence

[Channel upstream-area work package](../work-packages/20261122_channel_upstream_area/package.md)
