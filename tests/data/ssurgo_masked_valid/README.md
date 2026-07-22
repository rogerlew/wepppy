# SSURGO Masked-Valid Raster Fixtures

Each GeoTIFF is a small EPSG:5070 categorical MUKEY raster used only for
deterministic candidate-discovery scenarios. The companion manifest supplies
one or more native-kernel cluster requests, valid candidates, search radii,
and expected local-majority result. It covers direct success, expansion,
numeric tie-breaking, exhaustion, and two separated clusters in one query.

The GeoTIFFs are intentionally tracked with Git LFS. After cloning, use
`git lfs pull` before running the fixture test.

`scoring_cases.json` is a compact, no-network failure-class corpus for the
research scorer. It preserves only the evidence permitted for each invalid
class: `no_components` and `no_horizons` use geometry and terrain, partial
profiles use explicitly supplied raw fields, and nonphysical texture input is
excluded. It also pins missing-DEM, no-candidate, unclassified, and stable-tie
fallback behavior. It is not a production-policy fixture.
