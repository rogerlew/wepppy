# WEPP 260723 Release Notes

## Summary

WEPP `260723` preserves daily deep-percolation (`Dp`) values at scientific
precision in the standard hillslope water-balance output. This is an output
contract correction: the deep-percolation equations and parameter behavior are
unchanged.

The release also includes opt-in diagnostic sidecars for bottom-boundary and
Penman-Monteith state. They are emitted only when `wepp_observe.on` is present.
Normal runs retain the standard output set.

## Compatibility

The `Dp` field is now written with `E15.7` rather than fixed two-decimal
formatting in the daily, hourly, and shared water-balance writers. Consumers
must accept both the legacy fixed-decimal representation and the widened
scientific-notation representation.

WEPPpyo3 includes regression coverage for both forms and preserves the
alignment of all fields that follow `Dp`.

## Artifacts

| Artifact | SHA256 |
| --- | --- |
| `wepp_260723` | `a36be787816662d8d9e658c723e373342ccc982efb037749545a8cb26f5e4af4` |
| `wepp_260723_hill` | `61ec752fc9e130ef8dce18a5dd0a63dd8e0ee5e11c41ab8b4900e274322ce900` |

Both binaries were built sequentially with pinned `/usr/bin/gfortran` and
request `/lib64/ld-linux-x86-64.so.2`.

## Validation

- permanent hillslope watchlist: 14/14 passed;
- WEPP repository test suite: 84 passed, with two warnings;
- ablation artifact policy: passed;
- source and release binary identity: passed;
- same-build reconciled-condenser replay: 74/74 hillslopes and the 10-year
  watershed simulation completed with empty stderr and no parse/runtime error
  signatures; and
- replacement host smoke using tight-orthodontist `p1`: 43/43 years completed
  for both binaries because the default dumbfounded-patentee fixture was no
  longer available.

The canonical watershed capacity include files are unchanged.
