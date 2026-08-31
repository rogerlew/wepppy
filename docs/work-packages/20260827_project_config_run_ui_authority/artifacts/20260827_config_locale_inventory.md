# WP12D Config Locale Inventory

**Date**: 2026-08-27
**State**: ratified normalization; no `.cfg` edited
**Named configs**: 128
**Current literal locale omissions**: 71
**Ratified geographic compositions**: 126
**Ratified non-Builder family compositions**: 2
**Ratified invalid compositions**: 0

Shared `_defaults.cfg` supplies `["us"]` only where the table marks the
ratified source as inherited. An explicit row overrides shared defaults.
`general.cfg` is explicitly US because its `name = "seattle"` is stale
display metadata while its map/default data contract is Continental US;
labels never determine locale. `yasin.cfg` is explicitly Turkey and requires
the ratified canonical supported-non-Builder `turkey` profile. That profile is
classification-only: its five closed dataset axes are empty because Yasin's
fixed DEM, land-cover, and soil maps are config-owned inputs outside Builder
dataset authorization; its localized legacy controls remain in the existing
catalog mode.

| Config | Current literal | Ratified effective | Ratified source | Classification | Legacy authority |
| --- | --- | --- | --- | --- | --- |
| `0-wbt.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `0.cfg` | absent | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `13.cfg` | absent | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `2006.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `ChileCayumanque.cfg` | `["ChileCayumanque"]` | `["ChileCayumanque"]` | explicit `.cfg` | base supported | localized legacy catalog |
| `ag-fields.cfg` | `["us"]` | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `au-disturbed.cfg` | `["au"]` | `["au"]` | explicit `.cfg` | Builder base | live `australia` graph |
| `au-fire.cfg` | `["au"]` | `["au"]` | explicit `.cfg` | Builder base | live `australia` graph |
| `au.cfg` | `["au"]` | `["au"]` | explicit `.cfg` | Builder base | live `australia` graph |
| `august_complex.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `baer-exp.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `baer-legacy.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `baer-rred.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `baer-ssurgo.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `baer.cfg` | absent | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `bc-ca-disturbed9002.cfg` | `["bc-ca"]` | `["bc-ca"]` | explicit `.cfg` | base supported | localized legacy catalog |
| `beachie-fire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `ca_disturbed.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `ca_hindcast.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `ca_hindcast_2015.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `ca_hindcast_2015_smallbasins.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `ca_hindcast_2016.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `ca_hindcast_2016_smallbasins.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `ca_hindcast_2017.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `ca_hindcast_2017_smallbasins.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `ca_hindcast_2018.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `canada-wbt-mofe.cfg` | `["earth"]` | `["canada"]` | explicit `.cfg` | Builder base | live `canada` graph |
| `canada-wbt.cfg` | `["earth"]` | `["canada"]` | explicit `.cfg` | Builder base | live `canada` graph |
| `canada.cfg` | `["earth"]` | `["canada"]` | explicit `.cfg` | Builder base | live `canada` graph |
| `cda.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `cedar23.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `creek_fire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `culvert.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `czu_region.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-ak.cfg` | `["alaska"]` | `["alaska"]` | explicit `.cfg` | base supported | localized legacy catalog |
| `disturbed-anu-ash.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-caldor.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-hi.cfg` | `["hawaii"]` | `["hawaii"]` | explicit `.cfg` | base supported | localized legacy catalog |
| `disturbed-hubbar-brook-10m.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-hubbar-brook-2m.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-hubbar-brook.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-mofe-us-rap-covers.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-mofe.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-tree-observed.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-treecanopy.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-us-rap-covers.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed-vi-10m-mofe.cfg` | `["virgin_islands"]` | `["virgin_islands"]` | explicit `.cfg` | base supported | localized legacy catalog |
| `disturbed-vi.cfg` | `["virgin_islands"]` | `["virgin_islands"]` | explicit `.cfg` | base supported | localized legacy catalog |
| `disturbed-wbt-profile.cfg` | `["us"]` | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `disturbed.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed10-oyster-creek.cfg` | `["oyster-creek"]` | `["oyster-creek"]` | explicit `.cfg` | base supported | localized legacy catalog |
| `disturbed10.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed60.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed9002-10-mofe.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed9002-10m-wbt.cfg` | `["us"]` | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `disturbed9002-10m.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed9002-alexash.cfg` | `["us"]` | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `disturbed9002-mofe.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed9002-wbt-mofe.cfg` | `["us"]` | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `disturbed9002.cfg` | `["us"]` | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `disturbed9002_wbt.cfg` | `["us"]` | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `disturbed9003-10m.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `disturbed9003.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `dolan.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `earth.cfg` | `["earth"]` | `["earth"]` | explicit `.cfg` | Builder base | live `global-earth` graph |
| `eu-75.cfg` | `["eu"]` | `["eu"]` | explicit `.cfg` | Builder base | live `europe` graph |
| `eu-aragon-disturbed.cfg` | `["eu"]` | `["eu"]` | explicit `.cfg` | Builder base | live `europe` graph |
| `eu-disturbed-50.cfg` | `["eu"]` | `["eu"]` | explicit `.cfg` | Builder base | live `europe` graph |
| `eu-disturbed-75.cfg` | `["eu"]` | `["eu"]` | explicit `.cfg` | Builder base | live `europe` graph |
| `eu-disturbed.cfg` | `["eu"]` | `["eu"]` | explicit `.cfg` | Builder base | live `europe` graph |
| `eu-fire.cfg` | `["eu"]` | `["eu"]` | explicit `.cfg` | Builder base | live `europe` graph |
| `eu-fire2.cfg` | `["eu"]` | `["eu"]` | explicit `.cfg` | Builder base | live `europe` graph |
| `eu-schandau-disturbed.cfg` | `["eu"]` | `["eu"]` | explicit `.cfg` | Builder base | live `europe` graph |
| `eu.cfg` | `["eu"]` | `["eu"]` | explicit `.cfg` | Builder base | live `europe` graph |
| `fishfire-fire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `fishfire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `gaviota_2004_fire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `general.cfg` | absent | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `lt-fire-future-snow.cfg` | `["us", "laketahoe"]` | `["us", "laketahoe"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `lt-fire-snow-caldor-tr.cfg` | `["us", "laketahoe"]` | `["us", "laketahoe"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `lt-fire-snow-caldor.cfg` | `["us", "laketahoe"]` | `["us", "laketahoe"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `lt-fire-snow.cfg` | `["us", "laketahoe"]` | `["us", "laketahoe"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `lt-wepp_347f3bd.cfg` | `["us", "laketahoe"]` | `["us", "laketahoe"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `lt-wepp_bd16b69-snow.cfg` | `["us", "laketahoe"]` | `["us", "laketahoe"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `lt-wepp_latest.cfg` | `["us", "laketahoe"]` | `["us", "laketahoe"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `lt.cfg` | `["us", "laketahoe"]` | `["us", "laketahoe"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `nigeria.cfg` | `["nigeria"]` | `["nigeria"]` | explicit `.cfg` | base supported | localized legacy catalog |
| `omni.cfg` | `["us"]` | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `or-disturbed-beachie-fire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `or-disturbed-holiday-fire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `or-disturbed-riverside-fire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `or-disturbed.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `oregon.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `palouse.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `palouse9002.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `portland-10-mofe.cfg` | absent | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-disturbed-simfire-eagle.cfg` | absent | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-disturbed-simfire-norse.cfg` | absent | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-disturbed.cfg` | absent | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-disturbed9003.cfg` | absent | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-simfire-eagle-snow.cfg` | `["us", "portland"]` | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-simfire-norse-snow.cfg` | `["us", "portland"]` | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-snow.cfg` | `["us", "portland"]` | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-wepp_347f3bd.cfg` | `["us", "portland"]` | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-wepp_64bf5aa_snow.cfg` | `["us", "portland"]` | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-wepp_bd16b69.cfg` | `["us", "portland"]` | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland-wepp_bd16b69_snow.cfg` | `["us", "portland"]` | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `portland.cfg` | `["us", "portland"]` | `["us", "portland"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `reveg-10m-mofe.cfg` | absent | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `reveg-mofe.cfg` | absent | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `reveg.cfg` | absent | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `rhem.cfg` | `["rhem"]` | `["rhem"]` | explicit `.cfg` | non-Builder family | localized legacy catalog |
| `rhem_rap.cfg` | absent | `["rhem"]` | explicit `.cfg` | non-Builder family | localized legacy catalog |
| `riverside-fire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `salvage_logging.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `scu_lightning_complex.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `seattle-simfire-eagle-snow.cfg` | `["us", "seattle"]` | `["us", "seattle"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `seattle-simfire-norse-snow.cfg` | `["us", "seattle"]` | `["us", "seattle"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `seattle-snow-9002-simfire.cfg` | `["us", "seattle"]` | `["us", "seattle"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `seattle-snow-9002.cfg` | `["us", "seattle"]` | `["us", "seattle"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `seattle-snow.cfg` | `["us", "seattle"]` | `["us", "seattle"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `soberanes_fire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `tenerife-5m-disturbed.cfg` | `["tenerife", "eu"]` | `["eu", "tenerife"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `tenerife-disturbed.cfg` | `["tenerife", "eu"]` | `["eu", "tenerife"]` | explicit `.cfg` | base + overlay | localized legacy catalog |
| `us-ash.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `wepp-swat-wbt.cfg` | `["us"]` | `["us"]` | explicit `.cfg` | Builder base | live `continental-us` graph |
| `whis_carr_fire.cfg` | absent | `["us"]` | inherited `_defaults.cfg` | Builder base | live `continental-us` graph |
| `yasin.cfg` | absent | `["turkey"]` | explicit `.cfg` | base supported | localized legacy catalog |

## Validation and Compatibility

The proposal was simulated in memory against all rows. Geographic values
resolve through the canonical profile inventory; a lone `rhem` token is the
only accepted `non_builder_family` case. The binding test must repeat this
against edited files through `wctl` and fail unknown, empty, duplicate,
multiple-base, incompatible-overlay, or mixed-family state.

A legacy project-local defaults/config chain that omits `general.locales`
uses the contracted non-persisting compatibility value `["us"]`; an explicit
empty or invalid value fails. A project-local explicit value, including an
old Canada file that still says `["earth"]`, remains authoritative and is
not reinterpreted from its filename. No run file is rewritten.
