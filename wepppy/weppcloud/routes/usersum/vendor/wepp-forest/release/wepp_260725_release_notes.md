# WEPP 260725 Release Notes

## Summary

WEPP `260725` is rebuilt from the canonical
`wepp_260430_negmeltfix_comparator` default branch. It combines the negative
melt correction with the AgFields hillslope-capacity and roughness fixes, soil
layer cursor alignment, deep-percolation output precision, and hillslope-area
reporting correction.

Annual loss-report rows now emit the documented hillslope area, and annual plus
average rows preserve areas smaller than 0.1 ha instead of rounding them to
zero.

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
| `wepp_260725` | `2d9d9e4f8c6c1ef957aad687c1dd4d18eed55b2b0c1a2069add8f5c9d2b4f87b` |
| `wepp_260725_hill` | `7d04bc92a3d23ca5bed18344595196fa37e26b0d935645377dbea43abd284fc6` |

Both binaries were built sequentially with pinned `/usr/bin/gfortran` and
request `/lib64/ld-linux-x86-64.so.2`.

## Validation

- focused AgFields and precision contract tests: 6 passed;
- permanent default-branch hillslope watchlist: 12/12 passed;
- WEPP repository test suite: 86 passed, with two warnings;
- ablation artifact policy: passed;
- source and release binary identity: passed;
- same-build reconciled-condenser replay: 74/74 hillslopes and the 10-year
  watershed simulation completed with empty stderr and no parse/runtime error
  signatures; and
- replacement host smoke using tight-orthodontist `p1`: 43/43 years completed
  for both binaries because the default dumbfounded-patentee fixture is absent.

Both ELF interpreters resolve to `/lib64/ld-linux-x86-64.so.2`. The canonical
watershed capacity include files are unchanged.
