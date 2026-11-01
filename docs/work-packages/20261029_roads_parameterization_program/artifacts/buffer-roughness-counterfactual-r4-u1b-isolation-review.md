# Independent classification of the U1b isolation failure

Disposition: the declared upstream-isolation gate failed. Do not accept the
experiment as isolated or interpret its sediment improvement. All four native
runs completed and passed their individual audits; the remaining 32 were stopped.
This is independent AI scientific review, not institutional peer review.

The first changed upstream raw contract value is modeled buried residue, not
observer metadata: modern OFE 2, year 4, day 244, SMRM1 changes from
0.00016402760229539126 to 0.0001640275731915608 kg/m². OFE 1 first differs on day
247. All recorded density, porosity and protected driver trajectories remain
exact. Buffer residue had already diverged on day 236.

This is not only tiny residue roundoff. Independent published-table readback
finds the first upstream differences on year 4, day 233: road peak runoff changes
942.874 to 113.080 mm/h, effective duration 0.051 to 0.426 h, and rill width 0.156
to 0.082 m. Fill peak changes 820.359 to 98.387 mm/h and sediment leaving changes
0.441 to 0.648 kg/m. The first published upstream water difference is day 243;
the first SOIL difference is suction on day 268. Across the full period, 718
upstream WAT rows, 148 SOIL rows and 953 ELEMENT rows differ. These counts are
native-study observations, not independent storm samples.

## Source-supported path requiring executed confirmation

IRS finalizes a connected segment using terminal peak and effective duration,
then assigns that duration upstream and recomputes each contributing OFE's peak.
Consequently a downstream roughness intervention can affect upstream reported
hydraulics even with no upstream RRC assignment. XINFLO uses peak-derived flow;
PARAM calls SHEARS, which can increase persistent rill width. On the next storm,
FRCFAC uses width/rill spacing to form equivalent friction, RDAT derives the
routing coefficient, and IRS passes that coefficient into QINF recession
infiltration. This is the most direct hydraulic feedback path to test.
DECOMP/COVCAL also use width in residue partition and cover, INFPAR uses cover,
and DECOMP's decay uses local upper-layer water. These are concrete possible feedback paths, not yet
proof that every link caused this exact divergence. The existing common-duration
approximation must not be mistaken for independently routed upstream hydrographs.

Preserve this failed campaign. The next authorized step is observation-only
localization around years 4/day 233–234 and 243–244, with each modern off/on
ordinary output required to match its retained U1b counterpart exactly. Observe
producer operands and before/after ownership for connected-segment finalization,
persistent rill width, equivalent friction, routing coefficient and recession
infiltration. Residue differences may remain explicitly unproven downstream
associations; a full decomposition attribution is not needed for this bounded
localization. No parameter
retuning, tolerance change or additional state override is warranted.

If the executed source path explains the response, a future campaign would need
an explicitly revised whole-hillslope response contract. That would be a new
predeclaration, not retrospective acceptance of this failed isolation gate.
Global magnitude and physical criteria remain unchanged.

## Reproduction and retention

Run `review_buffer_roughness_isolation_failure_r4.py --root <attempt-u1b> --output
<fresh-receipt.json>` with the repository virtualenv. The companion
`buffer-roughness-counterfactual-r4-u1b-independent-isolation-failure.json` binds
raw traces, records, converted tables, reviewer code and relevant native source
hashes. No native simulation or conversion is run by this check.

The first diagnostic script attempt failed while counting changed column names
(a Python Counter was given dictionary values). Its exact script and error are
retained privately under `buffer-roughness-counterfactual-r4/independent-isolation-readback-attempt-1/`.
The corrected replay changes only that bookkeeping and completed successfully;
no scientific criterion changed and no earlier acceptance receipt was overwritten.
