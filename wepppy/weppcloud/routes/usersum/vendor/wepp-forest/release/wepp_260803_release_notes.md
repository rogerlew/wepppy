# WEPP 260803 Release Notes

## Summary

WEPP `260803` widens the watershed SOIL output OFE identifier from two to
five digits. Watersheds with OFE identifiers above 99 now emit numeric values
instead of `**`. No model equations, parameterization, or pass-file format
changed.

This release was built from the canonical remote-default branch
`wepp_260430_negmeltfix_comparator` at source commit
`f24c957e3633898e0fd4cbbea5ae08c781f29dba`. It retains the legacy
`H*.pass.dat` hillslope/watershed contract and does not support HBP.

## Artifacts

| Artifact | SHA256 |
| --- | --- |
| `wepp_260803` | `4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5` |
| `wepp_260803_hill` | `86ef065c8d8c6c1e644db40c022c7c850701c0c174d3c622dfa28f1d6da122e7` |

Each binary has a paired JSON sidecar recording the source branch, source
commit, binary hash, legacy pass capabilities, and release-gate status.

## Validation

- focused SOIL OFE, hillslope-area, and deep-percolation contracts: 4 passed;
- complete WEPP pytest suite: 87 passed with two warnings;
- replacement host smoke on `tight-orthodontist` `p1`: 43/43 years for both
  watershed and hillslope binaries;
- permanent hillslope watchlist: 12/12 passed;
- ablation artifact policy: passed;
- ELF interpreter: `/lib64/ld-linux-x86-64.so.2` for both binaries; and
- same-build `reconciled-condenser` replay: 74/74 legacy `H*.pass.dat` files,
  successful 10-year watershed completion, and empty watershed stderr.
