# Phase 0 Post-Hardening 1,000-Cell Replay

**Executed**: 2026-08-20 00:16 UTC

**Execution boundary**: direct `ESDAC.build_wepp_soil` diagnostic campaign in
the `weppcloud` development container. This does not exercise NoDb,
Disturbed, WEPPcloud routes, or RQ orchestration.

## Reproduction

The existing Phase 0 runner was used with the established reproducible seed:

```text
wctl run-python tools/eu_invalid_soil_search.py --pilot 1000 --seed 20260819 --output /tmp/eu-invalid-soils-pilot --force
wctl run-python tools/eu_invalid_soil_search.py --screen-manifest /tmp/eu-invalid-soils-pilot/manifest.json --output /tmp/eu-invalid-soils-pilot --controls 20 --build-workers 8 --force
```

The manifest contains 1,000 unique valid anchor cells sampled across the
20×20 strata. The source anchor is `fao90lev1` at
`/geodata/eu/ESDAC_ESDB_rasters/fao90lv1.tif`, with a 7,500×5,500 frame,
10,121,083 valid cells, and nodata value `255.0`.

The campaign output remains in the container at
`/tmp/eu-invalid-soils-pilot`; it is not a repository fixture. Hashes for this
run are:

- `manifest.json`: `7172feab1530c4704b1360472a8bee2819d11da4c01df0fa7810c92820782d63`
- `screen.json`: `0c6fae8b8b1acc9a10bbfa1d9cdf9ff44bbc74ea5b0f519fccfe68a6b61e7f25`

## Results

| Measure | Count |
| --- | ---: |
| Random samples screened | 1,000 |
| Source-suspicious samples | 631 |
| Fixed controls selected | 20 |
| Targeted direct builds | 651 |
| Successful `.sol` builds | 345 (328 suspicious, 17 controls) |
| Structured builder rejections | 306 (303 suspicious, 3 controls) |
| Control candidates intentionally not built | 349 |

The targeted-build policy is the Phase 0 contract: build every source-flagged
location plus a fixed valid-control sample. It is not a claim that all 1,000
locations were fully built.

Rejection diagnostics are overlapping counts because one location can carry
multiple reasons:

| Diagnostic | Locations |
| --- | ---: |
| `horizon.depth_order` | 14 |
| `source.categorical.empty` | 131 |
| `source.categorical.lookup_failed` | 15 |
| `source.textdepchg.no_information` | 99 |
| `source.il.no_information` | 71 |
| `source.usedom.no_information` | 64 |
| `source.stu.bulk_density_nonpositive` | 92 |
| `source.stu.mandatory_profile_empty` | 92 |
| `source.stu.texture_balance` | 5 |
| `source.stu.provider_unavailable` | 9 |
| `source.hydrogrids.all_missing` | 33 |
| `source.hydrogrids.provider_unavailable` | 4 |

## Generated-output check

All 345 successful files contained two parsed horizon rows. The post-build
check found:

- no non-finite horizon values;
- no nonpositive or non-increasing cumulative horizon depths;
- no missing successful-build `.sol` files; and
- eight `smr` (rock-fragment fraction) values equal to zero. No other horizon
  parameter column contained a zero.

The 14 depth-order cases that previously could have produced invalid output
are now explicit `ESDACSoilBuildError` rejections. This confirms the direct
builder hardening behavior for the sampled targeted set, while leaving the
NoDb/WEPPcloud integration boundary for the Phase 6 tests and post-deployment
observation window.
