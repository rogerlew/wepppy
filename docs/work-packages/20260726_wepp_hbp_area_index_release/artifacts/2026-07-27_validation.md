# Validation Evidence

## Root Cause

The HBP reader exposes one-based hillslope arrays. WEPP's legacy `hlarea`
common array has lower bound zero. Passing the whole actual array associated
reader index 1 with actual slot 0, shifted all subsequent areas, and left
actual slot `nhill` initialized to zero. Explicit one-based actual slices
restore matching indices.

## WEPP Candidate

- Sequential `/usr/bin/gfortran` build completed.
- Focused output contract: 3 passed.
- Executable lower-bound bridge contract passed with zero-slot sentinels and
  exact first/final hillslope placement.
- Permanent hillslope watchlist: 21 passed, zero failed.
- Complete WEPP pytest suite: 211 passed with two warnings.
- Copied `mdobre-foursquare-fovea` same-build gate regenerated all 587 HBP
  shards with `wepp_260727_hill`, then replayed them with `wepp_260727`;
  stderr was empty.
- Generated LOSS contained 4,109 hillslope rows: 3,522 annual rows and 587
  average rows.
- Every area was finite and positive; minimum area was `0.020 ha`.
- Every average area matched its corresponding HBP metadata at three-decimal
  hectare output precision.
- Hillslope 587 reported `0.080 ha`.
- Canonical host smoke fixtures were unavailable at
  `/wc1/runs/du/dumbfounded-patentee`; the full incident replay superseded
  that missing fixture for this defect.

## WEPPpyo3

The existing Python 3.12 release extension required no source or schema change.
It converted the same-build generated output with:

- LOSS: 5,875 accepted records, zero rejected records, and 587 positive-area
  average hillslope rows;
- SOIL: 521,696 accepted records and zero rejected records;
- hillslope 587 parquet area: `0.080 ha`.

The full Cargo workspace test command was blocked by the host PyO3 test-link
configuration (`undefined symbol: PyExc_IOError` and related Python symbols),
not by parser code. Direct release-extension execution is the deployment-path
validation.

## WEPPpy

- Binary provenance: both artifacts request
  `/lib64/ld-linux-x86-64.so.2`, use system libraries, and match release
  hashes.
- Runner and LOSS report tests: 45 passed.
- Omni artifact export tests in the host virtual environment: 8 passed.
- Copied-run `HillSummaryReport`: 587 rows, minimum area `0.020 ha`, hillslope
  587 area `0.080 ha`.
- The combined container collection including Omni was blocked by an
  unrelated container `pyproj.CRS` import failure; the same Omni module passed
  in the canonical host virtual environment.
- Work-package and project tracker documentation lint passed.

## QA Finding Dispositions

- The high-severity mixed-build replay finding is closed by the 587-shard
  same-build gate described above.
- The HBP metadata finding is closed: the generator and both Forest and WEPPpy
  sidecars now advertise the writer's schema 2.0, with focused regression
  coverage.
- The fixture inspection utility remains schema-1-only. Adding schema-2
  compressed-block decoding is a separate tooling feature and is not used by
  the deployed native reader, WEPPpyo3, or WEPPpy execution path.

## Artifact Hashes

- `wepp_260727`:
  `cbcfac30e484613c5314e7a91b694863d26138905fcf04947650bc2c6c148918`
- `wepp_260727_hill`:
  `d79a4bfde31feab8e3aff5ea5ae5d14b898f85b5f8fae5e471bc43d4078eddcc`
