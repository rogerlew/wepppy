# ADR: Project Config Locale and View Authority

Status: Accepted
Date: 2026-08-27

## Decision Provenance

- **Decision Venue**: active Codex development session, 2026-08-27 06:12 UTC.
- **Participants Present**: project operator and Codex.
- **Decision Owner**: project operator.
- **Implementer**: Codex.

## Context

WEPPcloud currently spreads locale-dependent availability across Builder TOML,
climate and landuse Python catalogs, templates, and route handlers. The first
Builder family covers only continental United States, while runtime catalogs
know about additional regions and methods. Fixed template radio lists can show
methods that a selected dataset or locale does not support.

## Change Summary

Previously, Builder had one partial locale family and flattened capabilities
used coarse dataset lists. After WP12B, every shipped runtime locale token is
classified by a canonical typed profile, supported Builder profiles resolve a
complete dependency closure, and generated configs store separate stable
dataset and method capability axes. Runtime views and paired mutation endpoints
consume the stored per-project authority.

## Decision

Retain `continental-us` as a durable profile ID and normalize it to the same
schema as every locale profile. Map profiles to existing runtime locale tokens;
do not rename stable IDs to tokens. Use the current registry for Builder views
and the flattened config for created-run views. Do not migrate existing runs.

Only explicitly supported and Forest-validated profiles are Builder-selectable.
Inventory-only or specialized profiles remain explicit but unavailable rather
than being silently treated as continental United States.

## Rationale

One typed graph makes dependencies reviewable and prevents presentation from
drifting away from server acceptance. Per-project capability snapshots preserve
reproducibility. Separating datasets from methods lets climate station/spatial
radios and landuse/soil workflows accurately follow their selected inputs.

## Alternatives Considered

Keeping template conditionals was rejected because hidden controls and server
acceptance can diverge. Reading the live registry from run pages was rejected
because registry revisions would retroactively change existing projects.
Treating every shipped config token as a supported Builder locale was rejected
because presets demonstrate deployed behavior but not a validated cross-product.

## Evidence

- WP12B active ExecPlan and locale inventory.
- Generated profile/component/capability matrix.
- Paired template and mutation-route regression tests.
- Presence/health evidence for every advertised provider and every
  Builder-exposed base/overlay, plus representative real execution for each
  distinct provider/method family.

## Risk and Rollback Notes

Incorrect locale dependencies can expose unavailable datasets or hide valid
workflows. Atomic registry validation, fail-closed required axes, paired server
enforcement, Preview maturity, and Forest provider evidence mitigate that risk.
Before the first schema-v2 project exists, rollback may restore prior catalog
filtering and the one-locale Builder. After the first v2 project exists, every
supported rollback revision must retain or redeploy a v2-aware, fail-closed
reader and enforcement path; v2 writers and new views may be disabled, but a
pre-v2 reader is no longer a supported target. Existing flattened projects
remain self-contained and unchanged.

## Consequences

Adding a locale or dataset now requires a stable profile/component definition,
dependency validation, generated capability evidence, and deployed-provider
acceptance. This is more deliberate than editing a template, but it gives views,
APIs, manifests, and Builder review one consistent authority.

## WP12C Decision Amendment - Builder Locale Expansion

### Decision Provenance

- **Decision Venue**: active Codex development session, 2026-08-27 15:40 UTC.
- **Participants Present**: project operator and Codex.
- **Decision Owner**: project operator.
- **Implementer**: Codex.

Expose exactly five Builder base profiles: `continental-us`, `europe`,
`canada`, `australia`, and `global-earth`. A profile's typed DEM, soil,
land-cover, and climate lists are the sole Builder availability authority.
Builder description carries one complete graph per locale rather than a union.

### Old and New Behavior

Before this amendment, only `continental-us` was `builder_exposed`; Builder
always returned and validated one Continental-US capability graph. Europe,
Australia, and Global Earth were supported runtime profiles but unavailable in
Builder, and there was no Canada-wide canonical profile. Climate availability
also depended on catalog-global support flags, while Australia's implemented
land-cover provider was missing from the typed land-cover catalog.

After this amendment, exactly five profiles are exposed. Description returns a
complete graph for each selected locale, server validation uses the same graph,
and profile-owned data lists are the only availability authority. Existing
schema-v2 Continental-US stored bytes do not change. All new profiles,
including Continental US, default to Vanilla CLIGEN in schema v3.

### Exact IDs and Runtime Mappings

| Profile | Data stable IDs | Runtime meaning | Default |
| --- | --- | --- | --- |
| `continental-us` -> `us` | DEM `usgs-ned1-2024`, `usgs-ned13-2022`; soil `ssurgo-gnatsgso-2025`; land cover `nlcd-2019`; climate `vanilla_cligen`, `prism_stochastic`, `observed_daymet`, `observed_gridmet` | `ned1/2024`, `ned13/2022`; `ssurgo/gNATSGSO/2025`; `nlcd/2019`; climate modes 0, 5, 9, 11 | first listed DEM/soil/land cover/climate |
| `europe` -> `eu` | DEM `europe-eudem-v1-1`; soil `esdac-europe`; land cover `corine-1990`, `corine-2000`, `corine-2006`, `corine-2012`, `corine-2018`; climate `vanilla_cligen`, `eobs_modified` | `eu/eu-dem-v1.1`; locale-special ESDAC gridded builder; `eu/CORINE_LandCover/<year>`; climate modes 0, 8 | EUDEM; ESDAC; CORINE 2018; Vanilla CLIGEN |
| `canada` -> `canada` | DEM `copernicus-dem-30`; soil `isric-global`; land cover `c3s-landcover-1992` through `c3s-landcover-2020`; climate `vanilla_cligen`, `observed_daymet` | `copernicus://dem_cop_30`; `isric`; `locales/earth/C3Slandcover/<year>` with `c3s-disturbed`; climate modes 0, 9 | Copernicus; ISRIC; C3S 2020; Vanilla CLIGEN |
| `australia` -> `au` | DEM `australia-srtm-1s`; soil `asris-australia`; land cover `australia-landuse-2010-2011`; climate `vanilla_cligen`, `agdc` | `au/srtm-1s-dem-h`; locale-special ASRIS gridded builder; logical adapter token `au/landuse_201011/lu10v5ua`; climate modes 0, 10 | SRTM; ASRIS; Australia 2010-2011; Vanilla CLIGEN |
| `global-earth` -> `earth` | DEM `copernicus-dem-30`; soil `isric-global`; land cover `c3s-landcover-1992` through `c3s-landcover-2020`; climate `vanilla_cligen` | the same global data runtime values as Canada; climate mode 0 | Copernicus; ISRIC; C3S 2020; Vanilla CLIGEN |

Every profile allows TOPAZ and WBT for Single OFE. Multiple OFE is allowed only
with WBT and `wepp_260803`. Every unique value from the canonical WEPP binary
provider remains selectable for Single OFE. All land-cover datasets allow
gridded, single, and upload methods under Single OFE; Multiple OFE allows
gridded and upload. SSURGO allows gridded, single-MUKEY, and single-database
builders; ESDAC, ISRIC, and ASRIS allow only their source-consistent gridded
builder. Climate station/spatial methods and defaults are the ones declared by
each exact climate descriptor.

Locale components write these exact values: Continental US writes
`locales = ["us"]`, map center `[40.0, -99.0]`, zoom 3, and English units;
Europe writes `locales = ["eu"]`, center `[50.0, 10.5]`, zoom 4, and metric
units; Canada writes `locales = ["canada"]`, center `[40.0, -99.0]`, zoom 3,
and metric units; Australia writes `locales = ["au"]`, center `[-27.0, 133.5]`,
zoom 4, and metric units; Global Earth writes `locales = ["earth"]`, center
`[40.0, -99.0]`, zoom 3, and metric units. These Canada/Earth viewport values
preserve their shipped preset baseline and do not imply dataset coverage.

DEM components write `general.dem_db` to the runtime value in the table and
default to 30 m except `usgs-ned13-2022` at 10 m and EUDEM at 25 m. SSURGO and
ISRIC soil components write `soils.ssurgo_db`; ESDAC and ASRIS write no config
key because the gridded soil builder dispatches on runtime locale. NLCD and
CORINE land-cover components write `landuse.nlcd_db` and enable land-use
change. C3S additionally writes `landuse.mapping = "c3s-disturbed"`.
Australia writes no `nlcd_db` because its gridded builder dispatches on `au`;
the adapter resolves its logical token to the deployment-owned geodata path,
which is not stored in provider identity or generated config. It does enable
land-use change. Climate components write no persistent NoDb
mode: the selected ID is stored as `capability_defaults.climate_dataset`, and
run-scoped discovery/build maps it to the exact numeric mode and method defaults
from the stored graph.

Climate-station database is a separate profile-owned axis. Its stable/runtime
mappings are `cligen-stations-legacy` -> `legacy`, `cligen-stations-2015` ->
`2015_stations.db`, and `cligen-stations-ghcn` -> `ghcn_stations.db`.
Continental US exposes all three and defaults to 2015. Europe, Canada,
Australia, and Global Earth expose only GHCN. The selected component writes
`climate.cligen_db`; it is not inferred from the climate dataset.

The climate graph is exact: E-OBS allows station methods `auto`, `distance`,
`multi_factor`, `eu_heuristic`, defaults to `auto`, allows spatial `single` and
`multiple`, and defaults to `multiple`. AGDC allows station `auto`, `distance`
and spatial `single`, `multiple`, defaulting to `auto` and `single`. Daymet
allows station `auto`, `distance`, `multi_factor` and spatial `single`,
`multiple`, `interpolated`, defaulting to `auto` and `single`. Vanilla CLIGEN,
PRISM, and gridMET allow station `auto`, `distance`, `multi_factor`, defaulting
to `auto`. Vanilla CLIGEN and PRISM allow spatial `single`, `multiple`;
gridMET allows `single`, `multiple`, `interpolated`; each defaults to `single`.

Add `canada` as a distinct stable ID and runtime token. It uses Copernicus DEM
30 m, ISRIC global soil, C3S global land cover for 1992-2020, and offers Vanilla
CLIGEN plus observed Daymet, with Vanilla CLIGEN as the default. Canada CDEM and Canada Land Cover 2020 were
rejected for this profile because the operator explicitly selected global
datasets for all of Canada. Reusing `earth` was rejected because it would erase
the project's intended geographic identity and would remove Canada's explicit
Daymet option.

Europe uses EUDEM v1.1, ESDAC, CORINE 1990/2000/2006/2012/2018, Vanilla CLIGEN,
and E-OBS. Australia uses SRTM 1 second, ASRIS, Australian 2010-2011 land
cover, Vanilla CLIGEN, and AGDC.
Global Earth uses Copernicus DEM, ISRIC, C3S 1992-2020, and Vanilla CLIGEN.
Continental-US behavior and defaults are unchanged. These choices reflect the
existing locale-specialized execution paths and deployed provider families;
each remains gated by revision-bound Forest execution evidence.

Vanilla CLIGEN is the climate-mode default for all five profiles. Regional
observed modes remain available only through explicit selection; locale choice
does not silently select E-OBS, Daymet, or AGDC.

Europe alternatives included global Copernicus/ISRIC/C3S; they were rejected
because the implemented EUDEM, ESDAC, CORINE, and E-OBS paths are the
locale-specialized providers. Australia global datasets were likewise
rejected in favor of SRTM, ASRIS, the existing 2010-2011 land-cover raster, and
AGDC. Global Earth E-OBS, AGDC, and Daymet were rejected because none is a
global observed-climate provider; Vanilla CLIGEN preserves the existing global
stochastic path.

### Evidence and Acceptance

The current runtime evidence is the shipped `eu.cfg`, `au.cfg`, `earth.cfg`,
and Canada presets; the provider implementations under `wepppy/eu/`,
`wepppy/au/`, and `wepppy/locales/earth/`; and typed descriptors in
`wepppy/nodb/locales/`. WP12C must add generated matrix tests and revision-bound
Forest provider probes/real execution before acceptance. Existing configs are
evidence of runtime mappings, not a live availability authority.

WP12C writes capability schema version 3 because Climate Station Database is a
new mandatory axis and default. Schema-v2 Continental-US bytes remain valid and
unchanged; they retain their existing configured `climate.cligen_db` without a
new station-database capability restriction. Every schema-v3 graph must include
`climate_station_databases` and
`capability_defaults.climate_station_database`. After any expanded-profile
project is created, a rollback target that only understands schema v2 is
unsupported.

Builder description schema version 2 exposes schema-v3 locale-keyed graphs and
components. Its singular graph/components retain the frozen Continental-US v2
shape only so older clients can parse the response. Old clients cannot supply
the new mandatory station-database selection, so validation and creation without
`builder_description_schema_version = 2` fail with
`unsupported_builder_schema` before mutation.

Historical schema-v2 update availability, preview, and apply continue through
the frozen v2 resolver and original manifest parent chain. They do not add or
infer a station-database component. Schema-v3 update resolution retains its
selected station component.

CLIGEN database and PAR-root resolution is instance-local. The station
component identity binds stable ID, exact manager selector, and resolver adapter
revision. This prevents concurrent requests for Legacy, 2015, and GHCN from
combining one database's rows with another database's PAR root.

The reader stores these rules as an append-only set of frozen structural
contracts. Creation uses the current contract for a stable profile ID. Stored
validation accepts a graph only when its complete axes, adjacency, defaults,
and model policy match one frozen historical contract. A later compatible
dataset addition appends a new structural contract and never changes the old
one; the stored graph's structure selects the match without consulting the live
registry.

Frozen equality covers locale, data, method, relation, and default structure.
The WEPP axis remains provider-dynamic: stored binary IDs must satisfy the
canonical ID grammar, stored role revisions must satisfy the role-digest shape,
all stored binaries may appear only in TOPAZ/WBT Single-OFE tuples, and the only
Multiple-OFE tuple is `wbt|multiple-ofe|wepp_260803`. Stored validation never
requires the current deployment to return an identical historical binary list.

### Amendment Risk and Rollback

The principal risk is advertising a provider outside its actual coverage or
validating a cross-locale dataset union. Closed profile lists, locale-keyed
graphs, paired UI/server tests, direct provider execution, and failure before
run mutation contain this risk. A candidate must first deploy with creation
disabled and prove all five stored graph contracts. Only that proven revision
or a newer compatible reader is a valid rollback target after the first
expanded-profile project is created.
