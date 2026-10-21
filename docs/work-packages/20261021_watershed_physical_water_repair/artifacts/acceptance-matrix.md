# Repair acceptance matrix

Status: narrow source/allocation/groundwater controls validated; full routing acceptance remains open. Evidence baseline:
[committed audit](../../20261021_watershed_physical_water_audit/artifacts/findings.md).

| ID | Required cases | Acceptance |
| --- | --- | --- |
| WPA-01 | No side hills; side hills with zero/nonzero surface flow; positive/zero/negative local net exchange; lateral/baseflow-only days; tributaries and cascades | Independently integrated channel inflow accounts for selected sources and physical exchanges exactly once; no water assigned to a nonexistent side source; negative sinks respect available water |
| WPA-02 | 900 m³/900 s/600 s step; 1,000 m³/600 s/1 m³/s; aligned 1,200 m³ control; duration shorter than one step; both `nt0` paths; point/cell-average modes; exponential/mixed/return components | Reconstructed source volume equals the requested physical volume within derived precision bounds; finite rates, documented timing support and endpoint continuity; explicit treatment of incompatible peak/duration operands |
| WPA-03 | Positive/negative/zero infiltration; below/at/above 0.00001 m; one/multiple soil layers; dry/saturated/frozen soil; single and unequal multiple OFEs | Each hourly water input is assigned to a legitimate store or flux; no cutoff remainder vanishes; no over-withdrawal, negative storage or manufactured ET/Dp/export; unaffected daily path preserved |
| WPA-04 | 0/100 mm initial groundwater; single, 50/50, 60/40, 40/60, 20/30/50; different total areas and successive hills; both water-balance modes; nonzero deep-seepage coefficient | Initial volume equals depth × full hillslope area; 10,000 m²/100 mm/0.04 per day yields 40 m³ initial baseflow with zero first-day recharge; recurrence timing, year transitions and zero-initial behavior preserved |
| Combined | Five OFE layouts × daily/hourly; top/side placement; 100 m and longer channels; unequal tributaries; two-channel cascade; dry/wet/snow days; calendars through years 100/200/300/400 | Complete paired execution, per-OFE/PASS/channel/outlet ledger, no missing or duplicate dates; independently measured sources, sinks and storage; explain every changed term and all residuals above justified bounds |

## Rules for numerical acceptance

Establish absolute-volume, relative, serialization and integration bounds before
judging candidate cases. WAT fixed-point lateral fields round at 0.01 mm; the
retained ordinary WAT scientific fields have seven significant digits, and ASCII
PASS has five. Derive each field’s actual quantization; do not use one global
relative tolerance for near-zero water. Report signed and absolute sums, maxima,
worst dates/elements and normalized errors. Include first/last states and unprinted
stores where they participate; do not certify an incomplete control volume.

Measure observation noninterference using candidate-off versus candidate-on
scientific output parity. Do not require baseline/candidate parity for outputs
intentionally repaired; require it on unaffected modes/paths and attribute intended
changes per lane. At least duplicate/missing transfers, wrong area, storage-sign
and date-shift corruption controls must fail with the expected error.

## Coverage and publication boundaries

Positive tile flows, contour/variable widths, impoundments, channel algorithms
and groundwater routing thresholds require explicit impact review. Exercise
changed common paths with bounded cases; if unsupported, explain the limitation
and prevent broader compatibility/certification claims. Ordinary constant-width
success is not evidence for all geometries. Scientific review must assess the
large daily/hourly partitioning differences independently of conservation.

Required regressions must be portable. Original private donor replays supplement
those gates when available and cannot be substituted with a truncated successful
window. If residual channel state/transport inconsistency survives the four fixes,
record the first remaining failing boundary and block closure pending a bounded
repair or explicit operator re-scope; do not silently declare success.

## MC authority clarification

Per the operator decision recorded in ADR-0101, assess MC using its implemented
continuity increment, coefficient/grid transitions and accepted transfers.
Geometric storage is diagnostic; equality to it is not a routing acceptance gate.
The added interior-state control must route a nonzero internal profile despite
dry inlet/outlet boundaries while preserving the all-zero fast path and equations.
