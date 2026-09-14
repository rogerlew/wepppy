# Development source audit — 2026-09-14

Read-only audit at revision `c81635b43804a11642e6c777ae725aa4a7fa7b78`.
Project: `/wc1/runs/ad/addicted-reservist`. No builders, cache refresh,
checkpoint, journal-mode changes or project mutations were invoked.
SQLite WAL readers can touch sidecar coordination state; this audit does not
claim byte-for-byte preservation of WAL/SHM files or complete noninterference
validation. Those remain required isolated regression tests.

## Terrain and original soil mapping

`ron.nodb` records 10 m `ned13/2022`. DEM, `dem/wbt/bound.tif` and
`soils/ssurgo.tif` share EPSG:32612, 2,991 rows, 3,097 columns and transform
`(10, 0, 638238.5085711605, 0, -10, 3749754.426840995)`.
The boundary has 4,311,420 cells equal to 1 (431.142 km²); outside is -32768.
Recorded outlet pixel coordinates are `[1083, 1767]`.
The existing relief file is not proof of raw-DEM M3 terrain conformance.

`soils/ssurgo.tif.meta` identifies `ssurgo/gNATSGSO/2025`, retrieved on
2026-09-11 with nearest-neighbor resampling. `ssurgo_substitution_d` is empty.
Do not infer survey-level SSURGO versus STATSGO lineage merely from this
combined spatial product's name or the cache filename.

| Original key | Basin cells | Strict offline mean cm |
| --- | ---: | ---: |
| 53947 | 3,105 | 152 |
| 53958 | 5,600 | 152 |
| 658465 | 161,807 | unavailable |
| 658489 | 84,418 | unavailable |
| 658497 | 175,366 | unavailable |
| 658498 | 696,867 | unavailable |
| 658504 | 2,274,002 | unavailable |
| 658566 | 9,169 | unavailable |
| 658580 | 314,822 | unavailable |
| 665730 | 586,264 | unavailable |

## Raw cache and material evidence

Opened `soils/ssurgo_tabular_cache.sqlite` with `mode=ro`, `query_only=ON`
and one explicit read transaction
covering both tables. Journal mode is WAL; committed records comprise 63
components, 178 horizons and 34 map units. All component totals are 100;
no repeated `(cokey, hzdept_r, hzdepb_r)` groups occur. Core columns required
by the offline helper exist. Tables for mapunit/legend/sacatalog do not exist;
survey lineage/version is not recoverable from those absent tables.
The `.sqlite.meta.md` sidecar records retrieval at 2026-09-11T00:23:03+00:00
and the SDA endpoint, but its generic SSURGO label does not establish collection
lineage. A new SDA query cannot establish the historical vintage of cached rows.

The unchanged `derive_mapunits` helper yields 16 valid and 47 unavailable
components: 29 ambiguous-material, 11 missing-horizons, six bedrock-excluded
with thickness conflict, and one thickness conflict. These are cache-wide
counts, not basin-weighted counts.

The eight unavailable basin keys have legacy H layers. Example: key 658504,
component 14179042, horizon IDs 40779500–40779503: H1 0–5, H2 5–41,
H3 41–89 and H4 89–170 cm, all master H, reported thickness absent.
Their contiguous depth does not establish material identity. Strict support
is 8,705 / 4,311,420 = 0.0020190563665799205 before SBS intersection.
Thus 99.798094363342% of basin cells need fallback under this policy.
This is a scientific policy consequence, not evidence of broken WEPP soils.

Frozen fixtures evaluated with the unchanged strict helper:

| Fixture | Valid components | Unavailable | Nonsoil | Complete / partial / unavailable map units |
| --- | ---: | ---: | ---: | --- |
| Moscow Mountain | 68 | 23 | 0 | 1 / 39 / 4 |
| Topanga | 9 | 55 | 0 | 0 / 8 / 5 |
| az_ponderosa | 172 | 61 | 2 | 16 / 36 / 2 |

These counts do not prove WEPP builder parity or validate a new policy.
The live WEPP `Horizon.valid` predicate uses hydraulic/texture readiness;
it does not reject H based on designation. No builder was instantiated.

## THICK delivery

Filename searches found no THICK asset under this project or `/wc1/geodata`.
The repository has three bounded historical fixture windows; none is a prepared
input for this basin. A broader `/workdir` search did not establish an additional
asset. This is a bounded inventory, not a claim about every mounted filesystem.

The retained USGS metadata names this object:
`https://prod-is-usgs-sb-prod-publish.s3.amazonaws.com/675721b9d34e5c5dfd05c575/STATSGO-THICK.tif`.
A HEAD request on 2026-09-14 returned 200, `Accept-Ranges: bytes`, length
352422285, ETag `b7d0951296a03041416c7a3c6c1e1b11`, last modified
2024-12-10 19:41:05 UTC. No raster acquisition was performed.
Availability of HEAD is not proof of a successful bounded raster read.

## Reproducibility identities

Logical hashes use `SELECT * ... ORDER BY cokey/chkey` in the same read
transaction, serialized as JSON arrays with separators `(',', ':')` and
`allow_nan=False`, then SHA-256. These identify the observed core rows;
they are not a full source preservation or concurrent-writer test.
Schema was inspected using `PRAGMA table_info(component)` and
`PRAGMA table_info(chorizon)`; groups used `GROUP BY mukey` and
`GROUP BY cokey,hzdept_r,hzdepb_r HAVING COUNT(*)>1`. A retained machine-readable
schema/row snapshot is still due before production derivation.

| Input | SHA-256 |
| --- | --- |
| component logical rows | `069a7f36562d26b2a7c7b4129bf1917544c1648f65a514fcb4e027d8d3016c5d` |
| chorizon logical rows | `5a9c66ddb6f3976ef49a24aab54774cd83a6eb0b7e5bfa4d6684fcd903b2d181` |
| ron.nodb | `30c7f9729cf0b6649f24cd05f1c7e678a69b688712ff46e3b57138f8baa40e74` |
| soils.nodb | `d5bc2805c0938fd58850b5a23359e60fc9aff971130001f264a10837b6516ee9` |
| soils/ssurgo.tif | `a182a66e3cae3c8858255a7e7d155ce14e82c73db35dbcddb6f2b45343439180` |
| soils/ssurgo.tif.meta | `ebe0aad41086df12f61f277625a46e7e12533f1439d8d8b46f07b8f891e1994c` |
| dem/dem.tif | `5467d79d71a98146f8b123a4c1c151117438f209de0db7264787a093c36f814a` |
| dem/wbt/bound.tif | `1c8f53a0fd66bfbd009d311b2c4a9ecf659566a190c75a015fd9466ba9b52e67` |

Next: resolve H/source lineage and authorize bounded source delivery before
claiming the milestone-1 checkpoint is complete.
