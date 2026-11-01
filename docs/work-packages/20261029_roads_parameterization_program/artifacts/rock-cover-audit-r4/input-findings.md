# Retained rock and cover inputs

Read-only direct parse of all 36 accepted attempt-u2 histories: nine contrasts,
two soil lanes and two roughness modes. Inputs are bound to the immutable
execution declaration SHA256 and its per-file hashes. Before/after size, mtime
and SHA256 match for all 73 consumed files (declaration plus 72 input files).
The reader has no production imports or native source dependency.

## Results

- 354 soil-file horizon rows and 108 OFE initial-management rows.
- Every initial scenario uses cropland format (landuse 1). The explicit
  rangeland `roki`/`rokr` fields are absent, not asserted to equal zero.
- All four histories of each contrast have identical management bytes. Soil
  bytes are identical across the roughness pair within each lane. There are
  three distinct management files across the complete panel.
- For B1-B6/B8/B9, initial canopy/interrill/rill cover is 0/0/0 for road,
  0.2/0.5/0.5 for fill and 0.8/1/1 for forest. B7 has 0.2/0.5/0.5 for road
  and 0.8/1/1 for both fill and forest. These are input fractions; native
  initialization and subsequent growth/residue processes change them.
- Every legacy profile has first-horizon RFG 65% (gravel) or 95% (paved) for
  road, 42.5% for fill and 20% for forest. Generated first-horizon RFG is the
  same across all three OFEs within a case: B1/B4/B7 48%; B2/B3 0%;
  B5/B6/B9 15%; B8 36.25%. Full deeper-horizon values are retained in the CSV.
  These are profile mass percentages, not measured surface-area cover.

## Boundaries

The `role` column in soil-fragments.csv records the actual soil label (`slid`),
which is a material name for generated soils. OFE 1/2/3 bind to ROAD/FILL/FOREST
through the parsed management indices. File horizons are not native computational
layers. The generated lane is conditioned `erosion_road_cap`, not raw SSURGO.
Input management equality excludes an explicit input cover difference; it does
not prove equal event-day cover or isolate annual sediment causality. The generic
cover inputs do not identify how much is rock versus litter, and their overlap
cannot be reconstructed from these files alone. There are no measured surface
rock values or gridded RUSLE products inside this input audit.

## Reader controls and reproduction

Run `python -B read_inputs_v2.py --repo /home/workdir/wepppy --out NEW_DIRECTORY`.
Output must not already exist. Missing and duplicated management sections,
nonpositive horizon depth, declaration drift, missing/duplicate histories and
cover/fragment bounds fail explicitly. Three CSVs replay byte-for-byte.

Version 1 was retained after its negative-control string replacement failed to
match a decimal-formatted horizon. Version 2 uses a numeric-line expression;
actual parsing and output calculations are unchanged. This was a reader-control
failure, not a model or input failure. Both attempts remain retained.
