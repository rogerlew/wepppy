# Channel upstream area correctness review

Reviewed 2026-11-23 UTC by independent correctness and QA agents. The repair restores the upstream-node convention documented in TOPAZ NETW.TAB column 12. D8 contributing cells include both tributaries and direct inflow to the node. Each D8 edge is processed once. The receiving cell is excluded. The computation uses the pointer convention already decoded for labeling, including ESRI pointers.

## Cases and findings

- Hand-counted 8 × 8 fixture, twelve watershed cells. For TOPAZ 34, 24 and 44, the previous runtime emitted 0, 20,000 and 0 m². The rebuilt installed runtime emitted 10,000, 70,000 and 20,000 m². Local lateral inflow below the junction and the downstream outlet cell are distinct from inflow into the junction.
- A separate seven-reach Peridot fixture checks each GeoJSON value against the original accumulation raster and checks the serialized outlet slope width. Includes a confluence and branched headwaters. All Peridot tests passed.
- The reviewer found the run README generator and vendored Usersum spec still described the old area. Corrected the source generator and synchronized the upstream spec.
- SWAT+ consumed reach surface area and could join on the network ordinal. Repaired the canonical source and join. Verified colliding identifiers, both width methods, zero-contributor hydraulic behavior, absent records, unit overrides in the existing reader, and the generated connectivity and hydraulic files. QA found a minimal two-column table could apply magnitude-based inference to canonical areaup. The exact field now declares m² in auto mode. A 900 m² regression test covers it.
- Independent QA read every incident reach against its upstream raster pixel and checked the area and width in the GeoJSON and channel Parquet. No open medium or high findings.

## Scope

Output assessment covers raw WBT network tables, Peridot channel geometry and modeled area, emitted WEPP geometry, and SWAT+ hydraulics and connectivity. TOPAZ already carries the correct upstream field. Stream order and non-Bieger width rules use separate inputs. Previously written WBT tables cannot be distinguished by their header and must be regenerated. The replay establishes input correctness. The hydrological impact of rerunning the production simulation remains unmeasured.
