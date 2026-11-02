# Retained surface artifact review

Disposition: **PASS for actual RUSLE artifact propagation and paired numeric parity.**
This closes the retained-artifact limitation in surface-implementation-review.md.
Broad-suite completion and final publication/archive checks remain parent-owned.
No model/producer was rerun and no raw file was written by this reviewer.

## Independent readback

Read all four distinct retained roots under
`out/rock-water-development-20261101/surface-artifacts-v1`: observed_rap and
scenario_sbs, each with auto and explicit manual settings. Verified the complete
45-file inventory: 44 files declared by the receipt plus the receipt itself.
Every declared SHA256 matched, and the complete inventory/hashes remained identical
before and after review. Current implementation and test-helper hashes match the
receipt's bound identities.

Used DuckDB directly to read each actual parquet; used rasterio directly to read
RAP/landuse/C rasters; parsed the retained SBS lookup CSV, mapping JSON and all
four manifest JSON files. This readback did not import the production loader,
producer script or its test helpers. Each manifest remained in its own root and
its source report matched the corresponding receipt entry.

For both auto cases, independent row accounting yields nine records, one NULL
cover, two nonfinite covers, zero unparseable covers, two finite out-of-range
covers, one reported-zero cover and four used records. Two records have unknown
or nonpositive area. Known positive area totals28 in source units; used area is7;
the known-area support fraction is0.25. These values exactly match persisted
support metadata. The independently reconstructed legacy weighted mean is
28.571428571428573 percent, yielding proxy0.28571428571428575.

## Numeric and override evidence

| Mode | Actual bare fraction | Effective rock fraction | Stored C value in both pixels |
| --- | ---: | ---: | ---: |
| observed_rap | 0.5 | 0.5714285714285715 | 0.04315930977463722 |
| scenario_sbs | 0.09999999999999998 | 1.0 | 0.018315639346837997 |

Bare fractions were independently derived from the RAP input band or actual
retained SBS lookup, not taken only from the source report. Stored C values match
the existing exponential formula at float32 precision. Each raster is1×2 with
finite non-nodata values. Within each mode, auto/manual arrays and raster profiles
are exactly equal, and the entire C GeoTIFF bytes are identical. Manual manifests
retain source=user and their explicit requested/effective values; they do not
invent an auto-source support object.

RAP paired C SHA256:
`f8344482ccb81fddc5e7c6c7b6c855cee034128ecdb2a82d24533b986807e869`.
SBS paired C SHA256:
`7500067b9f671fadd95113557fc25f51a8b5b05d09503320a64e4aa3e7a561d5`.
Receipt SHA256:
`729829f4e58fb1b68d47f27dd1e957bb484fc27c3463d72e508205f533438516`.

## Scientific scope

These are deliberately controlled synthetic support records and small real-format
artifacts, not field observations, NRCS-derived aggregate cover, measured Roads
armor, or native WEPP surface-mechanism validation. They establish that incomplete
support is exposed in actual generated manifests while the existing auto/manual
numerical policy remains reproducible. Invalid numeric source values are diagnosed
without being silently excluded from the old calculation. The prior scientific
limitations of the proxy remain unchanged.

Reviewer writers are clear after scoped Markdown lint.
