# M1 predictor decision register

Status: P01–P06 resolved for local implementation, 2026-09-09. Promote accepted choices into current
contracts and a parameterization ADR; this register is not standalone authority.

| ID | Work or decision | Recommendation and gate |
| --- | --- | --- |
| P01 | Verify calibrated K convention versus RUSLE Nomograph raster values. | Trace published Kf units and actual formula/output. Record explicit conversion or identity with analytical evidence; never infer from magnitude or a generic SI label. Research/engineering verification before composing S. |
| P02 | Missing K support and invalid values. | Recommend no additional Staley gap filling and no point S when usable K does not cover the full basin; preserve observed mean/coverage as diagnostics. Owner approval needed; dNBR's accepted partial mean does not automatically authorize partial K. Distinguish valid zero from NoData and nonphysical values. |
| P03 | M1 RUSLE prerequisite. | Recommend usable named Nomograph K plus its provenance, independent of successful unrelated RUSLE R/LS/C calculations. Retain completed WEPP Soils prerequisite. Owner approval needed for workflow policy; local backend consumes explicit artifacts meanwhile. |
| P04 | Upstream K preparation and source freshness. | Inventory RUSLE's existing two-stage source gap filling, depth weighting and optional fragment adjustment. Preserve reported provenance; do not invent a per-cell measured/imputed mask where the source does not provide one. Define legacy missing provenance handling before code. |
| P05 | Prepared raster conversion and invocation. | Lossless copied samples/masks on the authoritative grid; explicit finite collision-free NoData and supported TIFF layout. Palette SBS uses class indices, not RGB. Nearest SBS alignment only under a documented preparation contract; do not change raw DEM grid or invent unburned coverage. Engineering contract before implementation. |
| P06 | Local bundle schema and stale/source-changed states. | Versioned JSON plus referenced artifacts and SHA-256 lineage. Separate successful processing from model availability. Require complete WBT products, verify source identity, and never trust file existence/FNV alone. No live NoDb schema in this package. |

## Already settled

One project watershed/outlet; no nested selection. T preserves unknown
intersection bounds and is null if unresolved. F is the normalized observed-
support dNBR mean, including valid negatives/zero; do not divide by 1000 again.
Each predictor retains its own support over the full basin. A missing T/F/S
prevents a single M1 probability; do not silently switch models or propagate
probability bounds without a separate accepted contract. Area outside inclusive
0.2–8 km² produces warnings, not a hard rejection, per ADR-0057.

## Not blockers for this local package

Climate source/default/scenario catalog, M3 soils, dashboard, locale/UI controls,
live invalidation/publication and RQ wiring remain successor work. Document
which readiness checks the local adapter can actually establish versus future
server enforcement. No implicit source rebuild, metadata repair or acquisition.

## Execution decisions

Owner accepted P02/P03 with "proceed as recommended". P01 identity mapping is
verified in `k_unit_audit.md`. ADR-0059 records the accepted K coverage/readiness
rules. P04–P06 are frozen in the canonical M1 contract: missing legacy metadata
is unavailable, explicit hashes do not prove live freshness, trusted masked
GeoTIFF conversion preserves samples, opt-in nearest SBS alignment, version-1
fresh-directory bundle and retained incomplete failures. Proposal rows above
are retained as decision history, not pending gates.
