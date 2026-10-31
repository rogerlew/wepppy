# Versioned particle audit scope

Declared before the complete rerun. Version 1 remains immutable. Version 2
changes ELEMENT field boundaries, preserving the original three-OFE EVENT
selection, calendar mapping, units, width and Decimal printed-value criteria.
It does not re-run native models or approve parameters.

The first full attempt validated both legacy panels, then correctly stopped
under an overly broad numeric-presence requirement: ELEMENT Sm contains
`*******` in a generated-soil diagnostic row. Native fixed-width fields can
publish overflow markers. Canonical Rust ELEMENT conversion explicitly treats
all-star tokens as missing, rather than misaligning or guessing their value.
The first row is Birmingham/2711184/inveg/gravel/low, road_off_baseline,
year 2 March 12 OFE 1, line 249. Its particle export field remains available.

Before rerunning, distinguish three contracts. Structural validity requires
exact field widths, valid date/OFE, no trailing payload and unique row keys.
Numeric availability retains every all-star non-particle diagnostic as an
explicit unavailable-field record; it is never treated as a valid measured
number, zero, or native particle-budget failure. Particle mass requires finite
SedLeave, declared width, PASS volume and every concentration/fraction. Missing
required values, malformed tokens or nonfinite values reject the record; strict
fraction and mass checks remain unchanged. Duplicate or invalid records are
reported as audit failures and cannot be counted as successfully audited.

New receipts must report unavailable diagnostics separately from fraction/mass
flags and must not claim complete numeric availability. Original rows,
verification files, audit dependencies and failed setup/run artifacts remain
unchanged. The previous broad parser failure is retained as scope-development
evidence, not silently erased or interpreted as a new engine accounting defect.
