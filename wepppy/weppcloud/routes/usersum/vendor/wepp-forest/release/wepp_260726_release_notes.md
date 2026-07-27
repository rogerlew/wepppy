# WEPP 260726 Release Notes

## Summary

WEPP `260726` prevents watershed SOIL output from losing OFE identifiers above
99. The daily and hourly water-balance writers now reserve five characters for
the OFE identifier instead of two.

This is an output-contract correction. Soil measurements, water-balance
equations, routing, erosion, and sediment calculations are unchanged.

## Compatibility

Whitespace-delimited SOIL consumers retain the same column order and values.
Fixed-position consumers must accept the OFE field widening from `I2` to `I5`.
WEPPpyo3 accepts the widened output and separately provides strict recovery for
historical files whose identifiers 100 and above were emitted as `**`.

## Artifacts

| Artifact | SHA256 |
| --- | --- |
| `wepp_260726` | `c3d3588edee7a6376f5685b76ffcafd5eb6c74fae0b6cf1a6605f3d4197b32c7` |
| `wepp_260726_hill` | `d5f0c6797b1a72ac403e4f80ed1bd99491fd07eb3316f58c66f29d25c4c93e6a` |

Both binaries were built sequentially with pinned `/usr/bin/gfortran` and
request `/lib64/ld-linux-x86-64.so.2`.

## Validation

- The focused source contract test passed.
- A copied 587-hillslope `mdobre-foursquare-fovea` run regenerated all 587 HBP
  shards with the release hillslope binary.
- The six-year watershed replay completed successfully with empty stderr.
- Generated SOIL day 1 contained 238 contiguous numeric OFEs, including 99,
  100, and 238, and contained no overflow markers.
- WEPPpyo3 converted the historical 521,696-row incident file and reconstructed
  exact daily identifiers 1 through 238.
