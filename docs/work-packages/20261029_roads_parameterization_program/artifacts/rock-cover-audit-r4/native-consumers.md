# Native rock and cover consumers

Read-only audit, 2026-10-31. No native source, equation, input or output was
changed and no model was executed. Line references below identify the frozen
`buffer-roughness-hillslope-response-r4/attempt-u1/build/src/` tree. The u2
`binary-reuse.json` binds that exact reused binary and its u1 build receipt.
All 977 postbuild members reproduce their recorded hashes; relevant source,
includes, objects and binary are not inferred from a small observer-source folder.
The reader verifies before/after hashes, sizes and mtimes for all 977 members.
See the retained `consumers/readback-v2/source-identity.json` for bindings and active-reference indices.

## Quantities and consumer map

| Quantity | Origin and support | Native consumers | Evidence |
| --- | --- | --- | --- |
| RFG | Soil horizon mass percent, capped at 85 then divided by 100; depth-weighted to computational layers and tillage layers | Profile water, infiltration and a consolidation coefficient | INPUT 616, 633, 804, 885; TILAGE 568, 595, 652 |
| CPM | SCON mass-to-volume conversion using RFG and density; dimensionless fine-earth share | Corrected field/dry water contents; initial stored water; effective infiltration porosity | SCON 233-234, 305-307, 510-519; INFPAR 257, 637-642 |
| ROKCOV, FROKR, FROKI | Rangeland management rock cover and spatial partition, initialized only in `lanuse=2` branch | Rock-specific rill/interrill friction; rangeland cover aggregation | INFILE 815-883, 1465-1499; FRCFAC 253-323; RNGINT 519-540; PATRIB 372-404 |
| INRCOV, RILCOV | Cropland management initial generic cover; subsequently residue/stubble-derived cover | Interrill protection, rill/interrill friction and associated hydraulics | INFILE 1351-1352, 1442-1443; COVCAL 158-176; SOIL 1004; FRCFAC 210-246 |
| RESCOV | Width-weighted interrill/rill cover | Crusting/cover conductivity mixture | COVCAL 174-176; INFPAR 323, 487-527 |

RFG denotes the native fraction after input conversion in equations below.
With bulk density in kg/m3, the implemented fine-earth fraction is
`CPM = 1 - RFG*BD / (RFG*BD + 2650*(1-RFG))`. This is not an areal surface-cover
estimate. Initial water uses `SAT*POR*CPM`; the absolute initialized UL ceiling
uses POR without CPM, as established by the separate physical-capacity review.

There is an additional active *potential* erosion pathway from RFG. SCON
741-747 sets a consolidation coefficient to
`0.00035 - 0.0014*THETFC + 0.00068*SILT + 0.0049*RFG`, bounds it to
`[0.00001, 0.004]`, and divides it by baseline KR to form KRCRAT. SOIL
1113-1129 consumes KRCRAT in the cropland time-since-disturbance adjustment
and multiplies it into KRADJF, with a final floor. A change in RFG is therefore
not intrinsically a pure storage experiment. Bounds, other multipliers and
actual state can mask a numerical response; this audit does not quantify it.

## Which branch applies to the retained panel

The sibling input audit directly parses all 36 accepted management files and
finds all 108 OFE initial scenarios use `lanuse=1`. All four histories of each
contrast have identical management bytes. The rock-specific rangeland branch
therefore cannot be invoked merely by calling the modeled area ROAD, FILL or
FOREST. INFILE uses those management land-use codes to select native behavior.

The full active-reference scan finds no direct conversion from soil RFG to
ROKCOV in these sources. For the panel, surface protection uses the crop
INRCOV/RILCOV/RESCOV pathway. Absence of a separate rock field is not evidence of
zero actual surface rock, nor proof that historical generic cover values were
intended to exclude armor. The historical meaning of those generic cover
assignments remains an explicit provenance gap.

## Overlap and time dependence

The crop COVCAL implementation computes flat-residue cover from the exponential
of the sum of residue mass times its cover coefficient, adds standing-stem
cover, bounds the result, and forms width-weighted RESCOV. It is called by
DECOMP (977). CONTIN invokes DECOMP before SOIL (811-812); SOIL calls INFPAR
(855), and CONTIN later calls FRCFAC (1047). This is static execution-order
support, not a new per-day observation. Initial management cover values must
not be represented as constant storm-time cover.

SOIL uses `exp(-2.5*INRCOV)` as one crop interrill adjustment. FRCFAC uses
`14.5*INRCOV^1.5544` and `4.5*RILCOV^1.5544` for the respective cover friction
terms. SHEARS (134-135) uses the soil-to-total-friction ratio in effective
shear. INFPAR combines canopy and residue cover with an overlap subtraction
where applicable and mixes covered and bare conductivity. Thus appending rock
to generic cover can affect hydraulics as well as erosion and can double-count
protection if existing cover already represents it.

These are source-supported mechanisms. They do not establish observed annual
sediment causality or a justified parameter correction. RUSLE's fraction-of-bare
control cannot be copied into RFG, ROKCOV, INRCOV or RILCOV without specifying
the destination's units, spatial support, overlap, persistence and branch.

## Decision and evidence gaps

Keep profile mass fraction and initialized capacity fixed during any future
surface-cover-only experiment. First establish whether generic Roads cover
already includes armor, what independent surface evidence exists for each role,
and how an added persistent surface component should enter the active crop
consumers without biomass creation or double counting. Do not switch the
management land-use code to rangeland just to expose a rock field: that would
change many other equations and violate one-mechanism attribution.

No new observation probe is needed to establish these source branches. A future
behavioral experiment may need measured daily cover/consumer observations and
an independently reviewed overlap/persistence contract. Initial file values
alone are insufficient for a final output sensitivity claim.
