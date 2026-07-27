# Release Validation

## Source and Artifacts

| Repository | Source/release commits | Artifact | SHA256 |
| --- | --- | --- | --- |
| WEPP | `b517d0ab`, `7359673c` | `wepp_260726` | `c3d3588edee7a6376f5685b76ffcafd5eb6c74fae0b6cf1a6605f3d4197b32c7` |
| WEPP | `b517d0ab`, `7359673c` | `wepp_260726_hill` | `d5f0c6797b1a72ac403e4f80ed1bd99491fd07eb3316f58c66f29d25c4c93e6a` |
| WEPPpyo3 | `de575bc`, `926cf16` | `wepp_interchange_rust.so` | `61db1daa36c7383f897e52e640e092b00490d04bab646b95e0b55ed608851777` |

Both WEPP ELF artifacts request `/lib64/ld-linux-x86-64.so.2`. Vendored WEPPpy
copies are byte-identical to the WEPP release artifacts.

WEPP commits and annotated tag `wepp_260726` were pushed to `origin/master`;
WEPPpyo3 commits were pushed to `origin/main`.

## Generated WEPP Evidence

A private copy of `mdobre-foursquare-fovea` was prepared under `/wc1`; the
production run was not modified. The exact release hillslope binary regenerated
587/587 HBP shards. The exact release watershed binary completed all six years
with empty stderr.

Generated `soil_pw0.txt` day 1 contained 238 contiguous numeric identifiers:

```text
    99    1   2020 ...
   100    1   2020 ...
   238    1   2020 ...
     1    2   2020 ...
```

No line began with the historical `**` overflow marker.

## Historical Recovery Evidence

The Python 3.12 release-tree extension converted the original incident SOIL
file without modifying it:

- rows written: 521,696;
- rejected rows: 0;
- OFE range: 1-238;
- first day: 238 rows with exact boundaries 99, 100, 101 and 236, 237, 238.

The Rust suite passed 110 tests, including focused early-marker,
numeric-after-overflow, gap, and inconsistent-day-size rejection cases.

## WEPPpy Consumer Evidence

- `wctl run-pytest tests/wepp/interchange/test_native_only_interchange_facades.py tests/wepp/interchange/test_watershed_interchange_pass_family.py`:
  8 passed.
- `wctl run-pytest tests/wepp_runner`: 38 passed.
- Release-tree import and direct historical conversion passed.
- Canonical smoke fixture `dumbfounded-patentee` was absent, so the standard
  smoke helper could not execute; the exact incident replay is stronger
  generated-output evidence for this output-contract change.
