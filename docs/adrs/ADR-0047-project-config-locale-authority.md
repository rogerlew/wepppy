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
dataset and method capability axes. Flattened schema-v2/schema-v3 runtime views
and paired mutation endpoints consume the stored per-project authority.

## Decision

Retain `continental-us` as a durable profile ID and normalize it to the same
schema as every locale profile. Map profiles to existing runtime locale tokens;
do not rename stable IDs to tokens. Use the current registry for Builder views
and the flattened config for created-run views. WP12D later adds the bounded
non-flattened legacy live-authority and acknowledged-refresh exceptions without
migrating existing runs.

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
acceptance can diverge. Reading the live registry implicitly from complete
schema-v2/schema-v3 flattened run pages was rejected because registry revisions
would retroactively change stored authority; WP12D preserves that rule while
allowing non-flattened legacy pages, the bounded schema-v1 preset climate/land-
cover correction, and an explicit acknowledged stored-envelope refresh.
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

This table records the ratified WP12C creation matrix. Amendment 5 below
supersedes only its climate and land-cover columns; its DEM, soil, station-
database, viewport, and model-option values remain normative.

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

## WP12D Decision Amendment - Effective Config and Refresh Authority

### Decision Provenance

- **Decision Venue**: active Codex development session, 2026-08-27 22:23 UTC.
- **Participants Present**: project operator and Codex.
- **Decision Owner**: project operator.
- **Ratified Amendment**: `PC-24/WP12D-20260827-3`.
- **Implementer**: Codex.

### Change Summary

Before this amendment, shipped configs could inherit or carry incomplete locale
identity, recognized non-flattened runs used independent domain catalogs, and a
flattened capability graph was permanently frozen. After this amendment, exact
shipped configs resolve the normalized locale values below, five recognized
legacy base locales share the current Builder authority for the scoped
landuse/soil/climate surfaces, and eligible Builder-source schema-v3 projects
may deliberately replace only their same-locale capability envelope after the
versioned acknowledgment. Stored authority remains frozen by default and every
project selection remains unchanged.

### Decision

Locale is executable configuration owned by effective `.cfg`, not Interface
links, query state, registry labels, or persisted `Ron._locales`. Shared
defaults supply historical Continental US. Exact Canada, Portland, RHEM,
Tenerife, Turkey, established US, and general configs override or state their
canonical composition. Legacy project-local configs retain explicit locale and
receive non-persisting `["us"]` only when locale is absent; files are never
rewritten.

A recognized non-flattened single-base `us`, `eu`, `canada`, `au`, or `earth`
run uses the current Builder graph for landuse, soil, and climate presentation,
discovery, and submission. Flattened schema-v2/schema-v3 projects remain frozen
to stored authority. Flattened no-capability, schema-v1 outside amendment 5's
exact valid-preset climate/land-cover projection, and non-Builder/overlay/RHEM
modes retain their compatibility catalogs.

An owner/Admin/Root user may explicitly refresh a congruent Builder-source
schema-v3 project's same-locale capability envelope. The user must preview the
complete delta and accept the versioned warning that strict provenance
continuity is diminished and Preview/unstable features may be exposed. Refresh
preserves all project selection defaults, mods, and the climate station runtime
selector. If a selection no longer fits, refresh is unavailable rather than
silently substituting the locale's current default. Schema-v2 and preset-source
refresh remain unavailable.

### Rationale and Rejected Alternatives

Strictly immutable stored graphs maximize creation-time reproducibility but
prevent an old project from deliberately adopting new maps or capabilities.
Always-live stored authority maximizes on-demand access but silently changes
modeling behavior and erases the distinction between creation and later use.
The selected policy freezes by default, copies current authority only after an
explicit versioned acknowledgment, appends a reversible provenance record, and
freezes again.

Locale-bearing Interface links were rejected because they create a second
authority and do not help existing runs. Replacing project selections with
current Builder defaults was rejected because it could silently change Daymet
to Vanilla or alter the model tuple. Retaining an incompatible removed default
inside the refreshed graph was rejected because it would invalidate graph
closure. Silent migration, background refresh, and capability rollback UI were
also rejected.

### Parameterization and Structural Evolution

The parameterization change is the explicit locale normalization: shared US;
Canada token correction without changing its global datasets; canonical
Portland/RHEM/Tenerife/Turkey identity; and the exact Turkey supported-non-
Builder profile. Dataset lists, scientific formulas, provider algorithms, and
Builder defaults do not change in WP12D.

The exact old-to-new deltas are: shared `_defaults.cfg` absent to `['us']`;
three Canada configs `['earth']` to `['canada']`; five Portland configs absent
to `['us', 'portland']`; `rhem_rap.cfg` absent to `['rhem']`; `yasin.cfg`
absent to `['turkey']`; and two Tenerife configs `['tenerife', 'eu']` to
`['eu', 'tenerife']`. The seven named established/general US configs listed in
the canonical contract change from absent to explicit `['us']`.

Schema-v3 structure authorization is append-only. A deterministic structural
hash includes axes, relations, and per-dataset method defaults but excludes
project `capability_defaults`, dynamic provider/binary identity, and the binary
member of model tuples. Current and `280cf7e84` share one production identity;
WP12D uses a test-only distinct pair to prove evolution mechanics. The first
real map-axis change requires its own ratified identities and reader-first
Forest gate.

### Risk, Evidence, and Rollback

The main risks are broadening an old run through an unsafe fallback, resetting
user selections, accepting an injected self-consistent graph, or rolling back
to a reader that cannot understand a refreshed structure. Explicit 409/503
diagnostics, selection-preserving validation, append-only known structures,
auth-before-resolution, exact preview binding, journal recovery, and direct
paired-boundary tests contain those risks.

WP12D first deploys a reader floor with the refresh writer absent and existing
additive behavior unchanged. Forest then validates the writer with a real
provider/binary refresh and rolls back only to that compatible reader floor.
Reader `187a856d4` is supported only before refresh exposure. Production remains
owned by WP12.

Evidence is recorded in
`docs/work-packages/20260827_project_config_run_ui_authority/`, including the
128-config inventory, surface matrix, ratified contract decision, binding
reviews, regression results, and exact-host Forest acceptance evidence.

## WP12D Amendment 5 - Climate and Land-Cover Envelope Correction

### Decision Provenance

- **Decision Venue**: active Codex development session, 2026-08-28 10:00 UTC.
- **Participants Present**: project operator and Codex.
- **Decision Owner**: project operator.
- **Ratified Amendment**: `PC-24/WP12D-20260828-5`, exactly ratified by the
  operator on 2026-08-28 16:29 UTC.
- **Implementer**: Codex after contract checkpoint.

### Decision

The current locale graph is the shared climate and land-cover hotpath for new
Builder description/creation, recognized non-flattened legacy bases, explicit
schema-v3 capability refresh, and valid flattened schema-v1 named presets. The
schema-v1 projection is limited to climate and land cover, requires a valid
preset manifest, byte-exact rematerialization from current server-owned parent
sources and recorded allowlisted overrides, and exactly one congruent recognized
Builder base locale, and never rewrites the run. Other schema-v1 axes and non-
preset compatibility remain unchanged. Self-asserted project hashes and
descriptive `source_revision` do not authenticate this classification.

The exact climate envelopes are Continental US: Vanilla CLIGEN, PRISM,
observed Daymet, observed gridMET, DEP NEXRAD Breakpoint, Future CMIP5, and
User-Defined Climate; Europe: exactly Vanilla CLIGEN, E-OBS Modified (Europe),
and User-Defined Climate; Canada: Vanilla CLIGEN, observed Daymet, and User-
Defined Climate; Australia: Vanilla CLIGEN, AGDC, and User-Defined Climate; and
Global Earth: Vanilla CLIGEN and User-Defined Climate. Vanilla remains every
locale's default.

The exact stable-ID/runtime-mode mapping is:

| Stable climate ID | Runtime mode | Station methods | Spatial methods | Defaults | Additional contract |
| --- | --- | --- | --- | --- | --- |
| `vanilla_cligen` | 0 | `auto`, `distance`, `multi_factor` | `single`, `multiple` | `auto`; `single` | none |
| `prism_stochastic` | 5 | `auto`, `distance`, `multi_factor` | `single`, `multiple` | `auto`; `single` | US only |
| `observed_daymet` | 9 | `auto`, `distance`, `multi_factor` | `single`, `multiple`, `interpolated` | `auto`; `single` | US and Canada |
| `observed_gridmet` | 11 | `auto`, `distance`, `multi_factor` | `single`, `multiple`, `interpolated` | `auto`; `single` | US only |
| `dep_nexrad` | 13 | `auto`, `distance`, `multi_factor` | `single`, `multiple` | `auto`; `single` | US only; existing NEXRAD inputs |
| `future_cmip5` | 3 | `auto`, `distance`, `multi_factor` | `single`, `multiple` | `auto`; `single` | US only; existing future-year inputs |
| `user_defined_cli` | 12 | `user_defined` | `single`, `multiple` | `user_defined`; `single` | all five locales; `.cli` upload required |
| `eobs_modified` | 8 | `auto`, `distance`, `multi_factor`, `eu_heuristic` | `single`, `multiple` | `auto`; `multiple` | Europe only |
| `agdc` | 10 | `auto`, `distance` | `single`, `multiple` | `auto`; `single` | Australia only |

The profile climate ID order is exactly: Continental US
`vanilla_cligen`, `prism_stochastic`, `observed_daymet`,
`observed_gridmet`, `dep_nexrad`, `future_cmip5`, `user_defined_cli`; Europe
`vanilla_cligen`, `eobs_modified`, `user_defined_cli`; Canada
`vanilla_cligen`, `observed_daymet`, `user_defined_cli`; Australia
`vanilla_cligen`, `agdc`, `user_defined_cli`; and Global Earth
`vanilla_cligen`, `user_defined_cli`.

The Builder Land-cover selection sets `capability_defaults.landuse_dataset`
and the runtime selection but does not restrict the stored graph or run
control. Each graph carries its complete locale envelope: Continental US
annual NLCD and NLCD Ever Forest for 1985-2024 plus eMapR vote for 1984-2017;
Europe CORINE 1990/2000/2006/2012/2018; Canada and Global Earth C3S 1992-2020;
and Australia Land Use 2010-2011. Canada token `canada` resolves C3S rather
than the default US catalog.

The exact land-cover stable-ID/runtime mapping is:

- Continental US, in descending year order: `nlcd-ever-forest-<year>` to
  `nlcd/ever_forest/<year>` for every year 2024 through 1985, then
  `nlcd-<year>` to `nlcd/<year>` for every year 2024 through 1985, then
  `emapr-vote-<year>` to
  `islay.ceoas.oregonstate.edu/v1/landcover/vote/<year>` for every year 2017
  through 1984;
- Europe: `corine-<year>` to `eu/CORINE_LandCover/<year>` for years 1990,
  2000, 2006, 2012, and 2018;
- Canada and Global Earth: `c3s-landcover-<year>` to
  `locales/earth/C3Slandcover/<year>` for every year 2020 through 1992; and
- Australia: `australia-landuse-2010-2011` to
  `au/landuse_201011/lu10v5ua`.

Every listed land-cover ID permits `gridded`, `single`, and `upload` under
Single OFE and `gridded` and `upload` under Multiple OFE; its method default is
`gridded`. The Builder-selected ID remains the runtime/default selection but
does not narrow these ordered profile axes.

### Rationale and Rejected Alternatives

Treating the Builder selection as a singleton capability conflates a project
default with a locale constraint and prevents users from changing to another
applicable map. Retaining the coarse schema-v1 climate list reproduces the
opposite failure: Europe displays globally cataloged modes it cannot support.
The selected policy makes locale graphs authoritative for both domains while
preserving file provenance and every unrelated schema-v1 compatibility axis.
Broad live projection for arbitrary schema-v1 projects, manifest-free
classification, silent fallback on registry failure, migration, and run-file
rewrites are rejected. Trusting a merely self-consistent manifest was also
rejected: parent hashes and byte-exact canonical rematerialization bind
eligibility to deployed sources. Source drift intentionally returns to
compatibility rather than weakening this proof; an unreadable preset-policy
corpus fails diagnostically instead of masquerading as an inactive preset.

### Parameterization, Structure, and Rollback

This amendment changes dataset parameterization and all five schema-v3
structural identities; it does not change climate numeric modes, algorithms,
providers, year bounds, upload validation, or the Vanilla default. The prior
identities remain append-only valid. A standalone reader floor must register
all resulting identities before any Builder or refresh writer emits them.
Exact host `forest` must prove Europe schema-v1 projection and one new schema-
v3 create/refresh/reopen/reader-floor rollback path. Merge and production
remain reserved to WP12.

### Amendment-Specific Evidence

- Exact decision and state matrix:
  `docs/work-packages/20260827_project_config_run_ui_authority/artifacts/20260828_climate_landcover_contract_decision.md`.
- Runtime surface inventory:
  `docs/work-packages/20260827_project_config_run_ui_authority/artifacts/20260827_surface_matrix.md`.
- Pending independent correctness, governance, and security records:
  `20260828_amendment5_contract_correctness_review.md`,
  `20260828_amendment5_contract_governance_review.md`, and
  `20260828_amendment5_security_contract_review.md` in that work package's
  `artifacts/` directory.
- Reader-floor and exact-host Forest evidence will be recorded in the tracker
  and a dated amendment-5 acceptance artifact before implementation closure.
