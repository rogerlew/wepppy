# WEPP 260725 Release Notes

## Summary

WEPP `260725` corrects the hillslope-area fields in watershed loss reports.
Annual rows now emit the documented hillslope area, and annual plus average
rows preserve areas smaller than 0.1 ha instead of rounding them to zero.

This is an output-contract correction. Watershed geometry, runoff, erosion,
and sediment calculations are unchanged.

## Compatibility

The hillslope-area column retains its existing 20-character field width but is
written with three decimal places instead of one. Annual hillslope rows now
contain all ten fields advertised by the report header; previously the area
argument was omitted and the three phosphorus fields were shifted left.

Whitespace-delimited consumers remain compatible. Fixed-position consumers
retain the same column boundaries.

## Artifacts

| Artifact | SHA256 |
| --- | --- |
| `wepp_260725` | `7e0ccad2a79cebf63ad821b140ef3007ca5846ca9b646e87559448c38e4d0d91` |
| `wepp_260725_hill` | `968e007ea505c68e85dda2dcd2d851d3aa909d30ba694f356761f489585150ce` |

Both binaries were built sequentially with pinned `/usr/bin/gfortran` and
request `/lib64/ld-linux-x86-64.so.2`.

## Validation

- focused hillslope-area output-contract tests: 2 passed;
- `mdobre-foursquare-fovea` copied watershed replay: completed successfully
  and preserved 0.020-0.040 ha for the seven affected hillslopes;
- permanent hillslope watchlist: 14/14 passed;
- WEPP repository test suite: 86 passed, with two warnings;
- ablation artifact policy: passed;
- source and release binary identity: passed;
- same-build reconciled-condenser replay: 74/74 hillslopes and the 10-year
  watershed simulation completed with empty stderr and no parse/runtime error
  signatures; and
- replacement host smoke using tight-orthodontist `p1`: 43/43 years completed
  for both binaries because the default dumbfounded-patentee fixture is absent.

The canonical watershed capacity include files are unchanged.
