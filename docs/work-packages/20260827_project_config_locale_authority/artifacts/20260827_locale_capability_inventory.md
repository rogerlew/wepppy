# WP12B Locale and Capability Inventory

**Inventory revision**: `WP12B-INVENTORY-1`
**Repository revision**: `5cd18e61763430863d703d6f56454c1f00fcb2e1`
**Status**: Contract checkpoint input; implementation disposition pending

## Closed Source Boundary

Completeness is measured against all top-level `wepppy/nodb/configs/*.cfg`,
the legacy TOML corpus used by compatibility tests,
`wepppy/nodb/locales/climate_catalog.py`,
`wepppy/nodb/locales/landuse_catalog.py`, climate/landuse/soil/watershed run
templates and mutation routes, and the canonical WEPP binary provider. CI must
regenerate the inventory from those sources and fail on an undispositioned
value. Files under test fixtures, archived work packages, and generated docs
indexes are excluded.

## Locale Token Disposition

The shipped config corpus contains these exact token sets:

- base candidates: `us`, `alaska`, `hawaii`, `virgin_islands`, `eu`, `au`,
  `earth`, `nigeria`, `bc-ca`, `ChileCayumanque`, `oyster-creek`, and `rhem`;
- overlay compositions: `us+laketahoe`, `us+portland`, `us+seattle`, and
  `eu+tenerife`;
- configs without an explicit locale token inherit legacy behavior and are not
  silently classified as a Builder profile.

Canonical profile dispositions are:

- `continental-us` -> base, runtime token `us`, `builder_exposed`;
- `alaska`, `hawaii`, `us-virgin-islands`, `europe`, `australia`,
  `global-earth`, `nigeria`, `british-columbia`, `chile-cayumanque`, and
  `oyster-creek` -> base, `supported_non_builder`;
- `lake-tahoe`, `portland`, `seattle`, and `tenerife` -> overlay,
  `supported_non_builder`;
- `rhem` -> `non_builder_family`, `non_applicable` to the WEPP Config Builder;
- absent locale -> legacy-only, `inventory_only`, with no inferred base.

The exact legacy runtime spelling remains an output attribute. Comparison and
alias lookup use Unicode casefolding, but two canonical spellings that casefold
to the same token invalidate the profile catalog. `ChileCayumanque` therefore
maps through an explicit alias; it is not silently lowercased in generated
config.

Support-state semantics are closed. `builder_exposed` requires every mandatory
axis, complete graph closure, revision-bound provider evidence, and permits
Builder description/creation. `supported_non_builder` permits existing
Interfaces/catalog behavior and inventory-backed snapshotting but never Builder
selection; it need not claim a validated cross-product. `inventory_only`
records a discovered value without authorizing new presentation, snapshot
authority, or mutation. `non_applicable` excludes the value from this WEPP
Builder domain. Promotion to `builder_exposed` is a parameterization decision
requiring profile revision, ADR provenance, and Forest evidence.

For a `builder_exposed` profile, mandatory axes are locale, at least one DEM,
climate dataset with station/spatial adjacency and defaults, soil dataset with
builder adjacency/default, landuse dataset with method adjacency/default,
delineation backend, representation, WEPP binary, and at least one allowed model
tuple. The schema-v2 `mods` axis is mandatory but MAY be serialized empty. A
`supported_non_builder` profile
with an unresolved mandatory Builder axis, including Australia's empty current
landcover catalog, remains valid inventory but cannot emit schema v2 or appear
in Builder.

## Dataset and Method Inventory

The DEM stable-ID/runtime/state mappings are:

- `usgs-ned1-2024` -> `ned1/2024`, `builder_exposed`;
- `usgs-ned13-2022` -> `ned13/2022`, `builder_exposed`;
- `usgs-ned13-2016` -> `ned13/2016`, `supported_non_builder`;
- `australia-srtm-1s` -> `au/srtm-1s-dem-h`, `supported_non_builder`;
- `canada-cdem` -> `ca/ftp.maps.canada.ca/pub/nrcan_rncan/elevation/cdem_mnec`,
  `supported_non_builder`;
- `copernicus-dem-30` -> `copernicus://dem_cop_30`,
  `supported_non_builder`;
- `europe-eudem-v1-1` -> `eu/eu-dem-v1.1`, `supported_non_builder`;
- `aragon-mdt` -> `idearagon://mdt`, `supported_non_builder`;
- `chile-cayumanque-dem` -> `locales/ChileCayumanque/DEM`,
  `supported_non_builder`;
- `hubbar-brook-dem` -> `locales/hubbar_brook/dem`, `inventory_only`;
- `tenerife-mdt25` -> `tenerife/136_MDT25_TF`, `supported_non_builder`; and
- `tenerife-mdt05` -> `tenerife/MDT05_Tenerife`, `supported_non_builder`.

The soil stable-ID/runtime/state mappings are `ssurgo-gnatsgso-2025` ->
`ssurgo/gNATSGSO/2025` (`builder_exposed`), `alaska-gsmsoil` ->
`alaska/gsmsoil`, `hawaii-ssurgo` -> `hawaii/ssurgo`, `usvi-soils` ->
`locales/virgin_islands/soils`, `isric-global` -> `isric`, `chile-soils` ->
`chile`, and `portland-soils` -> `portland/soils` (all
`supported_non_builder`). Raster sources are `chile-cayumanque-soils-map` ->
`locales/ChileCayumanque/soils`, `tenerife-soils-25m` ->
`LOCALES_DIR/tenerife/soils/tf_soil_25.tif`, `tenerife-soils-5m` ->
`LOCALES_DIR/tenerife/soils/tf_soil_5.tif`, and `turkey-soils-map` ->
`MODS_DIR/locations/turkey/data/soil_.asc` (all `supported_non_builder`).
`none-soil-provider` -> explicit `None` is `inventory_only`.

The exact stable-ID/runtime/support mapping for all 164 unique landcover values
is enumerated in `20260827_landcover_inventory.md`. The Australia catalog is
explicitly empty. The canonical landcover provider must synthesize the same
stable IDs, runtime mappings, source revision, and provider digest; no second
hand-maintained allowlist may omit catalog values.

Climate `builder_exposed` datasets are `vanilla_cligen`, `prism_stochastic`,
`observed_daymet`, and `observed_gridmet`. `dep_nexrad`, `future_cmip5`,
`user_defined_cli`, and `eobs_modified` are `supported_non_builder`.
Deprecated `single_storm` and `single_storm_batch`, plus hidden `observed_db`,
`future_db`, and `agdc`, are `inventory_only`; none is omitted.

| Climate dataset | Station methods; default | Spatial methods; default | State |
| --- | --- | --- | --- |
| `vanilla_cligen` | `auto,distance,multi_factor`; `auto` | `single,multiple`; `single` | `builder_exposed` |
| `prism_stochastic` | `auto,distance,multi_factor`; `auto` | `single,multiple`; `single` | `builder_exposed` |
| `observed_daymet` | `auto,distance,multi_factor`; `auto` | `single,multiple,interpolated`; `single` | `builder_exposed` |
| `observed_gridmet` | `auto,distance,multi_factor`; `auto` | `single,multiple,interpolated`; `single` | `builder_exposed` |
| `dep_nexrad` | `auto,distance,multi_factor`; `auto` | `single,multiple`; `single` | `supported_non_builder` |
| `future_cmip5` | `auto,distance,multi_factor`; `auto` | `single,multiple`; `single` | `supported_non_builder` |
| `single_storm` | `auto,distance,multi_factor`; `auto` | `single`; `single` | `inventory_only` |
| `single_storm_batch` | `auto,distance,multi_factor`; `auto` | `single`; `single` | `inventory_only` |
| `user_defined_cli` | `user_defined`; `user_defined` | `single,multiple`; `single` | `supported_non_builder` |
| `observed_db` | `auto,distance`; `auto` | `single`; `single` | `inventory_only` |
| `future_db` | `auto,distance`; `auto` | `single`; `single` | `inventory_only` |
| `eobs_modified` | `auto,distance,multi_factor,eu_heuristic`; `auto` | `single,multiple`; `multiple` | `supported_non_builder` |
| `agdc` | `auto,distance`; `auto` | `single,multiple`; `single` | `inventory_only` |

Climate station-method mappings are `auto` -> `-1`, `distance` -> `0`,
`multi_factor` -> `1`, `eu_heuristic` -> `2`, `au_heuristic` -> `3`, and
`user_defined` -> `4`. Spatial-method mappings are `single` -> `0`, `multiple`
-> `1`, and `interpolated` -> `2`. Dataset-specific adjacency must preserve the
tuples already declared by each `ClimateDataset` descriptor.

Landuse method mappings are `gridded` -> `0`, `single` -> `1`, `rred_unburned`
-> `2`, `rred_burned` -> `3`, and `upload` -> `4`. Soil builder mappings are
`gridded` -> `0`, `single_mukey` -> `1`, and `single_database` -> `2`; RRED-only
internal modes remain mod-owned and cannot be inferred from the public list.
The representation dependency is closed: `single-ofe` permits `gridded`,
`single`, and `upload`, while `multiple-ofe` permits `gridded` and `upload` but
not `single`.

Delineation IDs are `topaz` and `wbt`; representation IDs are `single-ofe` and
`multiple-ofe`. WEPP binary IDs are exactly the canonical runtime provider
output and retain the existing provider-wide atomic validation contract.

## Unresolved/Non-Exposure Dispositions

Australia has no cataloged landcover dataset, hidden AGDC has no public UI
contract, specialized raster maps require deployed mount checks, and legacy
single-storm climate modes are deprecated. These are explicit blockers to
Builder exposure of their dependent tuples, not reasons to fall back to
continental-US data. Domain-owner and Forest evidence is required to change a
profile or component from `supported_non_builder` or `inventory_only` to
`builder_exposed`.

## Provider Identity Contract

Every provider-backed component has two identities. Its definition identity is
SHA-256 over canonical stable ID, runtime mapping, normalized descriptor fields,
dependency edges/defaults, and support state. Its deployment identity records
the application revision plus the provider's verifiable resource identity.

- DEM records the exact database/URI token, adapter module Git blob identity,
  and a successful metadata/coverage probe tied to deployment revision.
- Climate records the normalized `ClimateDataset` descriptor digest, adapter
  module Git blob identity, configured database/version token, and successful
  catalog/provider health probe.
- Soil records the stable runtime token or contained raster token, adapter
  module Git blob identity, configured dataset/version, and successful
  lookup/contained-resource probe.
- Landcover records SHA-256 over ordered normalized catalog records
  `(stable_id, runtime_value, label, locale group, support state)`, adapter
  module Git blob identity, and successful dataset metadata probe.
- WEPP binaries retain their role-resolved executable SHA-256 identity.

Definition identities contribute to the registry revision and manifest parent
chain. Deployment identities, observation time, and exact deployment revision
belong in Forest evidence. Secrets, credentials, and unrestricted filesystem
paths are never identity material.
