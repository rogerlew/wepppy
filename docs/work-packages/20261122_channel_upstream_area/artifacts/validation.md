# Validation evidence

Collected on forest, 2026-11-23 UTC. Original run inputs on wepp1 were read only.

## Native producer and consumers

Whitebox used a locked release build of whitebox-tools-app and whitebox_plugins. The installed dispatcher SHA-256 changed from `28208e075a51f37d254a51b2a9f27c0ef7e5f273344c8665a0749b4714766777` to `fad79e67c4307eb76b3661245afe23de05b12adcc8546c7216868ac7660db94c`. The rebuilt bundled plugin files were checked against the release build. The 158 Rust tests and 23 Python tests passed. The installed dispatcher in the WEPPcloud validation image produced all three hand-counted areas. Both upstream CI test runs passed.

Peridot passed 52 tests with `cargo test`, including the independent raster/GeoJSON/SLP test in `tests/wbt_bieger_width.rs`. The existing vendored WEPPpy binary consumes the corrected table without a binary change. [Peridot integration receipt](peridot-main.json) and [WBT integration receipt](wbt-master.json).

## Diagonal-intersection

Copied the run's bound, flovec, chnjnt, netw0, strahler, relief, outlet and floaccum artifacts to a disposable run. Rebuilt the network and subcatchment raster with HillslopesTopaz. Ran the vendored wbt_abstract_watershed with `--bieger2015-widths --skip-flowpaths --clip-hillslopes` and the run's fvslop and taspec rasters. Ran post_abstract_watershed and Wepp._prep_channel_slopes. For all 22,081 reaches, matched the following:

1. TSV area equals (flow accumulation at the upstream row/column minus one) × 900 m².
2. GeoJSON area equals TSV area. GeoJSON and Parquet widths equal the floored Bieger relation.
3. Each WEPP pw0.slp width, joined by chn_enum, agrees after slope-file precision and the WEPP minimum.
4. SWAT+ chandeg.con area and hyd-sed-lte.cha depth/width agree for every reach in both Bieger and QSWAT modes.

| Outlet reach 24 | Verified value |
| --- | ---: |
| Cumulative upstream-node area | 2,653,066,800 m² |
| Full-precision Bieger width | 38.26063253486773 m |
| WEPP pw0.slp width | 38.3 m |
| SWAT+ connectivity drainage area | 265,306.68 ha |
| SWAT+ hydraulic width, Bieger / QSWAT | 38.26063 / 51.50793 m |
| SWAT+ depth, both modes | 11.70764 m |

SWAT+ readback used WM = 1, WE = 0.5, DM = 0.5 and DE = 0.4. The regenerated modeled hillslope plus channel area was 249,532.72 ha. The upstream geometry correction affects channel surface area. Outlet drainage and modeled surface totals serve different purposes.

## SWAT+ executable smoke

Used the seven-reach amiss-polyhedron fixture's outlet geometry as the single channel in the bundled ref_1hru template. Ran the normal template preparation, wrote chandeg.con, channel-lte.cha and hyd-sed-lte.cha, and removed the template's example recall rows for this zero-recall smoke. Both modes ran the bundled SWAT+ executable for 2010–2023. Both produced success.fin and a channel_sd_aa.txt record for GIS ID 24 in 2023. This checks that the native reader and simulation accept the changed geometry. The smoke does not estimate changes to production hydrology.

An initial direct copy of the raw template omitted standard plant and water initialization and retained an example recall with no data file. Normal template preparation and a consistent recall count resolved both smoke setup failures.
