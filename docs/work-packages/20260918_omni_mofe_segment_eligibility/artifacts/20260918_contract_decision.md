# Contract decision — Omni MOFE segment eligibility

Starting revision: `ac106a9c3237b79945f165e31aeec523651f98c2`.
Operator approval: "for the mofe the landuse is assigned per segment, so the
treatment needs to apply the eligibility criteria per sgment" followed by
"scaffold and execute a work-package to address this defect" (2026-09-18).

Applicable authority: MOFE management artifact contract, NoDb persistence and
concurrency contract, generated-artifact validation standard, contract-first
change standard. Only the MOFE contract requires amendment. Other obligations
remain unchanged. This is a bounded intended selection correction; conformance
is pending. No persistence or security boundary changes.

Omni must inspect segment classes before excluding a MOFE hillslope. Existing
Treatments per-segment rules remain authoritative for application: thinning uses
forest/deciduous forest/mixed forest; prescribed fire maps forest/shrub/grass;
mulch requires a fire class. Existing single-OFE rules and hillslope filters stay
unchanged. No new model parameters or classification thresholds are introduced.

State matrix: single-OFE absent/empty segment state uses existing scalar behavior;
MOFE populated state uses segment classes, including mixed and all-ineligible
hillslopes. MOFE absent map, present-empty map, missing hillslope entry, empty
per-hillslope map, and malformed map must each fail explicitly; named parameterized
regressions cover these separately from valid all-ineligible no-op cases.
Missing/malformed MOFE assignments must fail explicitly rather than
silently use dominant landuse. Unknown management keys retain explicit failure.
Filtered and channel elements remain excluded. Working/failed/completed child
files, archive inspection and restoration retain their existing paths and behavior.

Evidence: regression for each treatment with an ineligible scalar class and
eligible OFE; mixed/all-ineligible/channel/filter cases; real treatment application
and parsed combined/prepared managements. Existing soils propagation tests and
focused/broad suites verify compatibility. No data/schema migration is needed.
