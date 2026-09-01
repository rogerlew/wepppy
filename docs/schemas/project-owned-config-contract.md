# Project-Owned Configuration Contract

> **Status:** Ratified 2026-08-04 by WP00R for implementation on
> `feature/project-owned-config`; noncanonical until roadmap promotion to
> `master`.
>
> **Scope:** Project creation, configuration composition, NoDb configuration
> resolution, capability presentation/enforcement, fork/archive preservation,
> and legacy fallback behavior.

## 1. Purpose

WEPPcloud currently resolves a named configuration from shared repository files
and layers it over the shared `wepppy/nodb/configs/_defaults.toml`. The first
implementation will make `_defaults.cfg` the canonical name while retaining
`_defaults.toml` as a legacy input alias. A later edit to either effective
defaults or the selected preset can change the configuration of an existing
legacy project.

This draft defines a project-owned configuration boundary. New projects receive
one fully resolved `.cfg` file in their working directory. That file contains
all effective defaults, locale attributes, component selections, capabilities,
mods, and explicit overrides. Runtime code reads the project-owned file without
reapplying shared defaults or locale profiles.

Existing projects without a project-owned flattened config continue using the
current shared-config behavior.

## 2. Goals

- Make a new project's effective configuration deterministic across later
  shared-config and locale-profile edits.
- Support a typed configuration builder composed from locale, terrain,
  delineation, watershed representation, capabilities, and mods.
- Make the resolved project config authoritative for available climate, soil,
  land-cover, and future build choices.
- Preserve existing projects without an automatic migration.
- Preserve existing NoDb `config_get_*` consumers and INI-style parsing in the
  first implementation.
- Ensure fork, archive, and restore preserve the configuration and its
  provenance with the rest of the project tree.

## 3. Non-Goals

- Migrating the runtime configuration system to real TOML.
- Making arbitrary user-supplied paths, sections, or option names available in
  the configuration builder.
- Snapshotting every external dataset or executable required for complete model
  reproducibility.
- Automatically rewriting existing projects.
- Providing a general fall-forward config migration engine.
- Automatically recomposing or refreshing a flattened project's stored locale
  or capability envelope when it is opened. WP12D's non-flattened legacy live-
  authority mode is the bounded exception.
- Removing shared named configs or their legacy fallback path.
- Standardizing how preexisting persisted selections affect surfaces outside
  WP12D's enumerated landuse, soil, and climate visibility/rebuild boundary or
  changing model routing.

## 4. Terminology

- **Shared defaults:** The canonical
  `wepppy/nodb/configs/_defaults.cfg`. During compatibility rollout, the legacy
  shared `_defaults.toml` path is a relative symlink to `_defaults.cfg`, not a
  second copy. Despite its old suffix, project-local legacy `_defaults.toml`
  files are parsed by `RawConfigParser`; they are not TOML.
- **Shared preset:** A named `.cfg` under `wepppy/nodb/configs/`.
- **Component source:** A typed builder definition for a locale, DEM, terrain
  resolution, delineation backend, watershed representation, capability
  profile, or mod.
- **Resolved config:** The complete effective option set produced at project
  creation.
- **Project-owned config:** The flattened `.cfg` stored in the NoDb working
  directory and used as runtime authority.
- **Legacy project:** A project whose working directory does not contain a
  project-owned config marked as flattened.
- **Config token:** The configuration identifier carried in run routes and
  stored by NoDb, with an optional `.cfg` suffix.

## 5. File Contract

For config token `<config>`, a new project MUST contain:

```text
<working-directory>/<config>.cfg
<working-directory>/config-manifest.json
```

The `.cfg` file MUST be compatible with the existing
`CaseSensitiveRawConfigParser` and `config_get_*` accessors. It MUST contain:

```ini
[config]
schema_version = 1
flattened = true
resolver_version = 1
```

The project-owned config MUST contain every effective runtime configuration
option from all applicable sections. It MUST NOT require shared defaults,
locale fragments, or builder component files to supply an omitted runtime
configuration value. Runtime secrets and credentials are not configuration
provenance and MUST NOT be copied into a project-owned config.

The project-owned config MUST retain the resolved `[general] locales` value for
provenance and existing locale-aware runtime behavior. Runtime capability
availability, however, MUST come from the resolved project config rather than
from recomposing the current shared locale profile.

The project-owned config is application-managed infrastructure after project
initialization. Ordinary controls MUST persist user/project state in their
existing NoDb stores rather than editing the config. The only version 1
post-creation edit is the registered additive amendment process below.

### 5.1 User-initiated additive configuration updates

Flattened configs support explicit, user-initiated additive updates when the
current parent build chain supplies registered configuration attributes that
did not exist when the project was created. This is not a bulk migration
framework and does not silently re-flatten a project when it is opened.

Page load MAY asynchronously call a read-only rq-engine availability endpoint.
The check MUST NOT mutate the config or manifest. When an update is available,
the run-page header MUST show a notice immediately after the Archive action,
linking to an accessible modal panel.
The panel MUST list every section, option, value, owning parent-chain source,
and source revision that the merge would add. It MUST provide an explicit
button to request the update and MUST explain that version 1 only adds missing
attributes. The review dialog MUST provide a wide-table viewport, and its table
captions, headers, and acknowledgment control MUST use the active WEPPcloud
theme. After a verified successful or recovered apply, the dialog MUST replace
the apply action with a primary `Reload run to continue` action.

The availability response MUST include an opaque preview identity. The
authenticated apply endpoint MUST re-resolve and revalidate the update under
the project lock. If the preview no longer identifies the same complete merge,
the endpoint MUST return a conflict and require the UI to refresh the preview;
it MUST NOT apply an unreviewed delta. An accepted request MUST enqueue an
rq-engine job that:

1. reconstructs the project's parent build chain from the immutable selections
   and source identities in `config-manifest.json`;
2. resolves the complete current attribute set for that chain using its
   declared precedence;
3. verifies that every contributing component/mod remains active for the
   project;
4. acquires the project config amendment lock and re-reads both files;
5. calculates the set difference and adds every applicable registered
   attribute that remains absent, including newly introduced sections;
6. validates the complete merged result;
7. atomically replaces the project-owned config; and
8. appends one batch amendment record and the new digest to the manifest as one
   crash-recoverable logical transaction.

A missing `config_get_*` lookup MUST retain its existing explicit
missing/default/error behavior. It MUST NOT trigger a configuration write.

This is a merge-only operation: the process MUST never overwrite or remove an
existing section or option. It MUST never add a new mod, capability, backend,
representation, locale, or DEM merely because a current profile contains one.
Adding a new NoDb mod therefore does not affect an older project unless that
project's resolved `[nodb] mods` already names the mod. A newly introduced
section or option owned by an already-active mod may be added with the rest of
the missing build-chain attributes.

An arbitrary miss, misspelled section/option, or unregistered attribute MUST
NOT mutate either file. If the registered build chain does not produce one
unambiguous merge result, the lookup retains its explicit missing/default/error
behavior and records no amendment. The reconciliation is all-or-nothing; it
MUST NOT write a partial subset when another applicable missing attribute is
ambiguous or invalid. The resolver MUST NOT search unrelated shared configs for
values.

The parent-chain resolution uses current registered definitions. Historical
registry documents do not need to remain executable or retrievable. Stable
source IDs identify which current definitions to consult; the revisions in the
manifest record what created the project and what supplied each later update.
If a recorded source ID no longer resolves unambiguously, the system reports no
applicable update and MUST NOT mutate the project. Once an added value is
written, later source changes MUST NOT alter it. An additive update does not
increment the config schema version.

Ordinary additive updates remain merge-only. The one bounded overwrite
exception is an explicitly acknowledged capability-authority refresh for a
complete schema-v3 Builder project. Schema-v2, schema-v1, no-capability,
preset-source, overlay, specialized, RHEM, malformed, and incongruent projects
MUST remain refresh-unavailable.

A refresh MUST use the same public locale-to-graph resolver as Builder
description/creation and recognized legacy live authority. It replaces only
the current same-locale capability envelope: axes, relations, per-dataset
method defaults, provider revision, binary revisions, and structural identity.
It MUST preserve every `capability_defaults` value, `[nodb] mods`, and
`[climate] cligen_db` exactly. Preserved selections MUST remain valid in the
current envelope; otherwise preview returns `409 config_update_unavailable`
with diagnostic stable IDs and performs no substitution, reservation, write,
or enqueue.

Refresh eligibility requires exact congruence between `[general] locales`, the
one stored graph locale, `capability_defaults.locale_profile`, manifest
`selections.locale`, manifest `selections.capability_profile`, and every
selection-bearing manifest/config value. The manifest MUST have
`source_kind = "builder"`. Locale never changes through refresh.

Availability is read-only. Preview MUST bind the complete delta, current and
resulting config digests, preserved project selections, warning revision, and
prior/resulting graph identities to one opaque `preview_id`. Its
`update_kind` is exactly `additive`, `capability_refresh`, or `combined`.
The opaque ID's deterministic binding input is exactly the current config
bytes, current manifest bytes, complete additions value, complete nullable
`capability_refresh` object, and warning revision. Omitting any of these inputs
is non-conformant.
Capability or combined preview MUST display this exact initially unchecked
acknowledgment:

> I understand that refreshing capability authority changes this project's
> modeling envelope, diminishes strict provenance continuity with its original
> configuration, and may expose Preview or otherwise unstable features.

Apply MUST remain disabled until checked. Browser and direct API apply MUST
send `capability_acknowledgment = {"accepted": true, "revision":
"PC-24-capability-refresh-v1"}` exactly when the preview has a capability
delta. `preview_id` is always required. The additive `{section, option}`
trigger is required only when additions exist. Missing, false, or mismatched
acknowledgment fails with `400 capability_refresh_acknowledgment_required`
before reservation. Config, manifest, graph, warning, or delta drift fails with
`409 stale_config_preview`.

The browser MUST reset acknowledgment on every preview load, stale/error
response, modal close, and successful apply. No acknowledgment state is stored
client-side. Refresh is never automatic, on-open, or background migration.
Other overwrite, removal, locale-change, mod-change, backend-change, and
representation-change updates remain outside this contract.

## 6. Resolution Modes

### 6.1 Flattened project mode

When `<working-directory>/<config>.cfg` exists and contains
`[config] flattened = true`, the loader MUST:

1. load that file alone;
2. apply no shared `_defaults.cfg` or `_defaults.toml` values;
3. apply no shared preset values;
4. apply no current locale or component-source values; and
5. reject a malformed or unsupported flattened-config schema explicitly.

It MUST NOT silently fall back to shared configuration after recognizing a
flattened project config.

If the flattened config is valid but `config-manifest.json` is missing,
malformed, or inconsistent with the config filename, ordinary project loading
and existing model operations MUST continue with an operator-visible warning.
Configuration update availability and apply operations MUST be disabled until
the manifest is repaired through a separately authorized maintenance action.
The loader MUST NOT synthesize a manifest or fall back to shared defaults. A
malformed flattened config itself retains the explicit failure behavior above.

Every reader supporting project-owned configs MUST continue reading manifest
schema version 1. An unknown newer manifest schema is treated like an invalid
manifest: a valid flattened config still loads, restore is not blocked solely
for that reason, updates are disabled, and no shared fallback occurs. Removing
version 1 reader support requires a separately ratified migration contract.

### 6.2 Legacy project-local mode

When a project-local config exists without the flattened marker, the loader
MUST retain current behavior: defaults are loaded first and the local config is
layered over them. Defaults resolution MUST use this precedence:

1. project-local `_defaults.cfg`;
2. project-local `_defaults.toml`;
3. shared `_defaults.cfg`; and
4. shared `_defaults.toml`.

A legacy project-local `_defaults.toml` MUST win over either shared defaults
name. The rename MUST NOT silently replace project-local defaults with current
shared defaults.

This mode preserves any existing manually or historically copied project-local
configs.

For non-flattened legacy run-control authority, locale is read from this exact
effective defaults-plus-local chain rather than persisted `Ron._locales`.
When the complete project-local chain omits `[general] locales`, the reader
uses non-persisting compatibility value `["us"]`; it MUST NOT rewrite any run
file. An explicit empty, unknown, duplicate, multiple-base, or incompatible
composition fails with `409 locale_authority_invalid`. An explicit historical
value remains authoritative, including a Canada project that explicitly says
`["earth"]`.

### 6.3 Shared fallback mode

When no project-local config exists, the loader MUST retain current behavior:

1. load shared `_defaults.cfg`, falling back to shared `_defaults.toml` during
   the compatibility period;
2. load the named shared preset; and
3. apply supported config-token query overrides.

Missing or malformed shared files retain their existing explicit failure
behavior. The new resolver MUST NOT mask those failures.

Shared `_defaults.cfg` supplies historical `[general] locales = ["us"]`.
Named configs override it for Canada, Portland, RHEM, Tenerife, Turkey, and
other explicitly specialized compositions. The effective shared-defaults-plus-
named-config locale is the non-flattened run's locale authority; link state,
request query, config labels, feature-registry metadata, and persisted
`Ron._locales` MUST NOT override it. Locale-bearing query/config-token creation
overrides fail before directory publication or controller initialization with
HTTP 400 `project_config_validation_failed` in the canonical envelope. This
does not reject Config Builder's typed, server-validated locale selection,
which writes `[general] locales` through the flattened resolver rather than a
legacy query/config-token override.

Flattened projects MUST be classified before this legacy locale path. A
flattened config without capability authority and a schema-v1 project outside
section 9's exact named-preset climate/land-cover exception retain their
existing compatibility behavior without new locale validation or live-registry
consultation.

### 6.4 Nested project and PUP authority

The validated top-level project run root is the sole version 1 owner of a
project-owned config, manifest, update history, and update lock. Nested/PUP
working directories inherit that authority. The builder and update flow MUST
NOT create a config or manifest inside `_pups` or another nested run directory.

For a persisted nested controller, config resolution MUST preserve a
preexisting legacy child-local config when present. Version 1 MUST NOT create a
child-local flattened config. Otherwise the controller MUST resolve the config
token against the validated top-level run root before using shared fallback.
The parent lookup MUST use explicit run context or persisted `parent_wd`
identity and MUST validate containment; it MUST NOT discover a parent by
searching path strings. The equivalent parent-root lookup applies to legacy
project-local defaults when the nested controller currently inherits them.

A nested UI MAY display the top-level project's update notice, but preview and
apply target the top-level authority. Fork, archive, and restore carry the one
root-owned pair with the complete project tree. Independent nested composition,
per-child updates, and reconciliation of intentionally divergent legacy child
configs are out of scope for version 1.

## 7. Project-Creation Paths

### 7.1 Named-preset creation

The existing Interfaces page and its config-based project creation links remain
a supported creation path. For those projects, the project-owned config MUST
retain the original shared preset basename. For example, a project created from
`disturbed9002_wbt.cfg` MUST contain and use `disturbed9002_wbt.cfg` in its
working directory, and its route config token remains `disturbed9002_wbt`.

Creating a new project from an existing named preset MUST:

1. resolve shared defaults;
2. overlay the named shared preset;
3. materialize supported config-token query overrides;
4. validate the resulting effective configuration;
5. durably write the flattened project-owned config and manifest before
   publishing project readiness; and
6. initialize Ron and all other NoDb controllers only after both files are
   durable.

The new project MUST NOT depend on later reads of the shared preset or shared
defaults.

The manifest MUST record the named preset's parent chain as canonical shared
defaults followed by the named preset. Normalized supported query overrides are
immutable selections applied after that chain; they are not source nodes. A
later user-initiated additive update resolves the current versions of the same
defaults and preset, then reapplies the project's recorded overrides.
It adds missing registered attributes only. Developers who change shared
defaults, a named preset, or a feature that consumes them are responsible for
keeping every supported preset complete and compatible. The update mechanism
MUST NOT infer a different component profile or silently repair an invalid
preset.

Each named preset MUST declare an explicit allowlist and validator for durable
query overrides. Accepted overrides are normalized, materialized into the
project-owned config, and recorded in `selections.overrides` with their key,
effective serialized value, and source `query`. Unknown override keys MUST be
rejected for flattened creation rather than silently persisted. Authentication,
CAPTCHA, CSRF, routing, and transport fields are never configuration overrides.
This narrowing applies only when the flattened writer is enabled; it MUST NOT
silently change legacy project-creation behavior.

Named configs own their runtime locale through effective `.cfg`, never through
their Interface link. Shared defaults and shipped configs MUST use this exact
normalization: shared `_defaults.cfg` and `0`, `13`, `baer`, `reveg`,
`reveg-mofe`, `reveg-10m-mofe`, and `general` resolve to `["us"]`; the three
Canada configs (`canada`, `canada-wbt`, and `canada-wbt-mofe`) resolve to
`["canada"]`; `portland-10-mofe`, `portland-disturbed`,
`portland-disturbed9003`, `portland-disturbed-simfire-eagle`, and
`portland-disturbed-simfire-norse` resolve to `["us", "portland"]`;
`rhem_rap` resolves to `["rhem"]`; `yasin` resolves to
`["turkey"]`; and both Tenerife configs resolve in canonical base-first order
`["eu", "tenerife"]`. The Canada change MUST NOT change its global DEM, soil,
land-cover, climate, or station-database selections. These names refer to the
corresponding `.cfg` files.

The canonical Turkey profile has stable ID/runtime token `turkey`, label
`Turkey`, base classification, `supported_non_builder` support, source revision
`WP12D-1`, no overlay metadata, and empty closed Builder dataset axes. Yasin's
fixed maps remain config-owned and `enable_landuse_change = false`; no Turkey
Builder graph or invented dataset stable ID is permitted.

### 7.2 Builder creation

The builder MUST accept typed, allowlisted selections rather than arbitrary
configuration keys. Its initial component model MUST cover:

- locale/profile, such as `continental-us`;
- locale-supported DEM source and resolution, with an associated default cell
  size;
- an authorized cell-size override from the closed set defined in section 7.5;
- delineation backend, initially TOPAZ or WBT;
- watershed representation, initially single-OFE or WhiteboxTools-dependent
  Multiple OFE;
- a registered WEPP binary version compatible with the selected representation;
- additional mods after they are registered beyond the initial family; and
- resolved climate, soil, land-cover, and related capability profiles.
- a locale-supported CLIGEN climate-station database.

The builder MUST validate the complete combination before creating the project.
It MUST reject incompatible selections with a field-addressable explanation and
MUST NOT silently substitute a different locale, DEM, cell size, backend,
representation, WEPP binary, capability, or mod.

Component sources are creation-time inputs. They MUST NOT become runtime
dependencies of the generated project.

#### 7.2.1 Initial registered family

Version 1 MUST launch with one conservative `continental-us` family. Stable
IDs are semantic builder identifiers and are not shared preset filenames or
route tokens. The initial matrix is:

| Dimension | Stable IDs and resolved meaning |
| --- | --- |
| Locale | `continental-us`: explicit `[general] locales = ["us"]` and existing continental-US units/map behavior |
| DEM | `usgs-ned1-2024`: `dem_db = "ned1/2024"`, default 30 m; `usgs-ned13-2022`: `dem_db = "ned13/2022"`, default 10 m |
| Delineation | `topaz`; `wbt` |
| Representation | `single-ofe`: `[wepp] multi_ofe = false`; `multiple-ofe`: `[wepp] multi_ofe = true`, exposed by Builder V1 only with `wbt` and `wepp_260803` |
| WEPP binary | Every value returned by `wepp_runner.wepp_runner.get_linux_wepp_bin_opts()`; `wepp_260803` is the default and the only value eligible for Multiple OFE |
| Soils | `ssurgo-gnatsgso-2025`: `soils_db = "ssurgo/gNATSGSO/2025"`, existing gridded mode |
| Land use | `nlcd-2019`: `landuse_db = "nlcd/2019"`, existing gridded mode and general mapping |
| Climate | `vanilla_cligen`; `prism_stochastic`; `observed_daymet`; `observed_gridmet` |
| Climate station database | `cligen-stations-legacy`; `cligen-stations-2015`; `cligen-stations-ghcn` |
| Mods | none |

The supported Single OFE tuples are the cross-product of two DEMs, both
delineation backends, and every binary returned by the canonical provider on
that deployment. WBT, Multiple OFE, and `wepp_260803` adds two tuples. Provider
output is deployment availability, not a promise that different hosts expose
identical historical binaries. Dataset and binary identifiers MUST be verified
against deployed services, mounts, and role-resolved executables at the Forest
gate.
A provider-supplied value that cannot pass the required gate makes Builder
binary availability fail explicitly until the provider or deployed binary set
is corrected. Builder MUST NOT filter individual provider values through a
second availability list or inferred substitution.

Builder V1 defaults to `wbt`, `single-ofe`, and `wepp_260803`. The WBT-only
Multiple OFE rule is a conservative Builder eligibility policy, not a statement
that legacy TOPAZ MOFE presets are technically invalid. Those existing presets
remain unchanged. The Builder MUST NOT infer defaults from lexical component
ordering.

WP12C adds four Builder families without changing this historical V1 matrix.
The complete exposed base-profile set is `continental-us`, `europe`, `canada`,
`australia`, and `global-earth`. Every generated configuration remains Preview.
The exact dataset and default matrix is maintained by the current canonical
locale profiles under section 7.2.2 and ADR-0047; specialized bases and overlays
remain unavailable unless a later approved amendment exposes them.

#### 7.2.2 Comprehensive locale and dependency authority

Before initial production promotion, the registry MUST classify every runtime locale token used by shipped
configs or domain catalogs as a canonical base profile, an overlay profile, or
an explicitly non-Builder model family. A profile MUST declare a durable stable
ID, its exact runtime locale tokens, classification, support/exposure state,
referenced component IDs, and resolved capability IDs. Unknown tokens,
duplicate base authority, cyclic overlays, unknown references, contradictory
requirements, and empty mandatory capability axes MUST invalidate the registry.

Profile classification MUST be one of `base`, `overlay`, or
`non_builder_family`. Support state MUST be one of `builder_exposed`,
`supported_non_builder`, `inventory_only`, or `non_applicable`. Geographic
profile composition is exactly one base plus zero or more overlays. Each
overlay MUST reference exactly one compatible base; overlay ordering and write
precedence MUST be explicit and unique. A `non_builder_family` does not
participate in base/overlay composition and MUST be `non_applicable` to Builder.
Cycles and duplicate precedence invalidate the registry.

Runtime tokens retain their exact canonical spelling in generated config.
Lookup MAY use an explicit alias table and Unicode casefolding, but alias and
canonical-token casefold collisions MUST invalidate the registry. A locale
token tuple has one ordered canonical composition; no token or tuple may map to
two base authorities.

`continental-us` remains the durable stable ID for the profile whose runtime
locale token is `us`. Normalization MUST NOT rename that component or rewrite
existing manifests. Specialized tokens such as municipal, watershed, or
research-area overlays MUST NOT be treated as interchangeable base locales.
`canada` is the durable stable ID and runtime token for Canada-wide Builder
creation. It MUST NOT alias `global-earth` or `british-columbia`/`bc-ca`.

The registry MUST track dependencies between locale, DEM, delineation,
representation, WEPP binary, climate dataset, climate-station database and
methods, soil dataset and builder, landuse dataset and methods, and mods. The dependency language MUST be
typed and closed; component documents MUST NOT contain executable expressions.
Only profiles with explicit Builder support and completed deployment evidence
may be offered for creation. Evidence MUST bind the profile/component IDs,
source revisions, registry revision, provider revisions, deployment revision,
and observation date. Every DEM, climate, soil, landuse, method, backend,
representation, binary, and mod value referenced by the closed inventory source
boundary MUST have one support disposition. Inventory generation MUST fail on
an undispositioned value.

Each canonical profile MUST own closed `dem_sources`, `soil_sources`,
`landuse_sources`, `climate_sources`, and `climate_station_databases` lists. For
Builder presentation and submission, those profile lists are the sole dataset authorization source;
catalog-wide support state, component-global flags, template conditionals, and
frontend lists MUST NOT add a value. In particular, the Land-cover dataset
control and its server validator MUST derive only from the selected profile's
`landuse_sources`.

The selected Builder Land-cover dataset is the project default and runtime
selection. It MUST NOT narrow the profile's `landuse_sources`, the stored
`capabilities.landuse_datasets`, or the run control to a singleton. Run
presentation and submission use the complete locale-applicable land-cover
envelope, subject only to the disabled exact-current carveout in section 9.

The current schema-v3 Builder matrix is:

| Stable profile | Runtime token | DEM | Soil | Land cover | Climate | Station DB | Data defaults |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `continental-us` | `us` | NED1 2024; NED1/3 2022 | SSURGO/gNATSGO 2025 | annual NLCD and NLCD Ever Forest, 1985-2024; eMapR vote, 1984-2017 | Vanilla CLIGEN; PRISM stochastic; observed Daymet; observed gridMET; DEP NEXRAD Breakpoint; Future CMIP5; User-Defined Climate | Legacy; 2015; GHCN | NED1 2024; SSURGO/gNATSGO 2025; NLCD 2019; Vanilla CLIGEN; 2015 |
| `europe` | `eu` | EUDEM v1.1 | ESDAC | CORINE 1990, 2000, 2006, 2012, 2018 | Vanilla CLIGEN; E-OBS Modified (Europe); User-Defined Climate | GHCN | EUDEM v1.1; ESDAC; CORINE 2018; Vanilla CLIGEN; GHCN |
| `canada` | `canada` | Copernicus DEM 30 m | ISRIC global | C3S 1992-2020 | Vanilla CLIGEN; observed Daymet; User-Defined Climate | GHCN | Copernicus DEM; ISRIC; C3S 2020; Vanilla CLIGEN; GHCN |
| `australia` | `au` | Australia SRTM 1 second | ASRIS | Australia 2010-2011 | Vanilla CLIGEN; AGDC; User-Defined Climate | GHCN | SRTM; ASRIS; Australia 2010-2011; Vanilla CLIGEN; GHCN |
| `global-earth` | `earth` | Copernicus DEM 30 m | ISRIC global | C3S 1992-2020 | Vanilla CLIGEN; User-Defined Climate | GHCN | Copernicus DEM; ISRIC; C3S 2020; Vanilla CLIGEN; GHCN |

Stable IDs and exact runtime mappings for this matrix are domain-owned and
recorded in ADR-0047. Canada MUST use only the listed global terrain, soil, and
land-cover datasets; Canada CDEM and Canada Land Cover 2020 remain outside this
Builder profile. Vanilla CLIGEN MUST be available for every exposed locale.
Vanilla CLIGEN is the climate-mode default for every exposed locale. E-OBS,
Daymet, and AGDC remain explicit regional choices and are never selected
implicitly. Continental US exposes Legacy, 2015, and GHCN station databases and
defaults to 2015; every other exposed locale exposes and defaults only to GHCN.
User-Defined Climate MUST be available for every exposed locale. Europe MUST
expose exactly Vanilla CLIGEN, E-OBS Modified (Europe), and User-Defined Climate.
The unchanged numeric runtime modes are 13 for DEP NEXRAD Breakpoint, 3 for
Future CMIP5, and 12 for User-Defined Climate.

The station-database stable/runtime mappings are
`cligen-stations-legacy` -> `legacy`, `cligen-stations-2015` ->
`2015_stations.db`, and `cligen-stations-ghcn` -> `ghcn_stations.db`. The
selected component writes `[climate] cligen_db`, participates in the registry
digest and manifest chain, and is stored as both a capability axis and a
capability default.

The closed inventory boundary is every top-level
`wepppy/nodb/configs/*.cfg`, the legacy config corpus exercised by compatibility
tests, `wepppy/nodb/locales/climate_catalog.py`,
`wepppy/nodb/locales/landuse_catalog.py`, the climate/landuse/soil/watershed and
WEPP run controls plus their mutation/discovery routes,
`wepppy/climates/cligen/cligen.py`, and the canonical WEPP binary provider. Test
fixtures, archived work packages, and generated docs indexes are excluded.
Domain specifications own each stable-ID/runtime mapping; the omission gate
compares those definitions to this source boundary.

`builder_exposed` requires complete mandatory axes, graph closure, and
revision-bound provider evidence and permits Builder presentation/creation.
`supported_non_builder` records supported Interfaces/catalog behavior but does
not permit Builder presentation and need not claim a valid Builder
cross-product. `inventory_only` records discovery without authorizing new
presentation, capability snapshot authority, or mutation. `non_applicable`
excludes the value from the WEPP Builder domain. For `builder_exposed`, all axes
and relations in capability schema v2 are mandatory and non-empty except the
mandatory `mods` axis, which MUST be serialized and MAY be empty.
`mod_requires` and `mod_conflicts` MUST both be
present-and-empty exactly when `mods` is empty; otherwise their keys MUST
exhaust `mods`. Per-mod `mod_conflicts` values MAY be empty. A profile with an
unresolved mandatory axis remains
`supported_non_builder` or `inventory_only` and MUST NOT emit a Builder
capability graph. WP12B schema-v2 graphs retain their complete historical
contract. WP12C `builder_exposed` profiles MUST emit schema v3 with every v2
axis/relation plus the mandatory climate-station database axis/default.

Every provider-backed definition MUST contribute a deterministic SHA-256
identity to the registry revision and manifest chain. DEM identity includes its
exact database/URI token and adapter revision; climate identity includes its
normalized descriptor, configured database/version token, and adapter revision;
CLIGEN station-database identity includes its stable component ID, exact manager
selector, and resolver adapter revision; it MUST NOT include a deployment path;
soil identity includes its runtime or contained raster token, dataset/version,
and adapter revision; landcover identity is over ordered normalized stable ID,
runtime value, label, locale group, support state, and adapter revision; WEPP
binary identity remains the role-resolved executable digests. Forest evidence
adds successful provider metadata/coverage/lookup probes, observation time, and
deployment revision. Secrets and unrestricted filesystem paths MUST NOT enter
either identity.

Builder views consume the current validated registry. A created run's views and
mutation/build endpoints consume only the resolved capability authority stored
in its flattened config. They MUST NOT consult the current registry to broaden
or restrict an existing run.

Builder description schema version 2 MUST provide a complete schema-v3
capability graph keyed by each exposed stable locale ID. Validation and
resolution MUST select the submitted locale's graph and MUST NOT validate
against a union of locale axes. The response MUST include
`builder_description_schema_version = 2`.

The singular `capability_graph` response member remains the frozen historical
Continental-US schema-v2 graph, and the top-level `components` member remains
its historical Continental-US component population. These two members provide
read-only response-parsing compatibility only; they cannot express the mandatory
schema-v3 Climate Station Database selection. The
`capability_graphs_by_locale` and `components_by_locale` members are
authoritative for description-schema-v2 clients and contain schema-v3 graphs
and complete component populations for all exposed profiles. A new client MUST
read both locale-keyed members and submit
`builder_description_schema_version = 2` with validation and creation. A create
or validation client that omits that version, submits a different version, or
omits `climate_station_database` MUST receive `409
unsupported_builder_schema` before directory creation or NoDb mutation. Old
clients may continue to parse the compatibility response but cannot create
WP12C runs. An absent locale graph, an unknown graph key, or a dataset selected
from a different locale MUST fail before run creation or mutation.

The Builder MUST obtain its WEPP binary choices from
`get_linux_wepp_bin_opts()` when loading the runtime registry, without a second
hard-coded binary allowlist. It MUST preserve the provider's complete unique
set, including the provider's `latest` alias. Labels MUST be the provider value
or a neutral humanization of it; they MUST NOT add lifecycle annotations such
as "legacy parity" that the provider does not supply. If the configured default
is absent, Builder description and creation MUST fail explicitly rather than
silently selecting another binary.

For every provider value, the registry MUST resolve the watershed and hillslope
roles exactly as the WEPP runner does and compute a SHA-256 digest of the bytes
of each resolved executable. The ordered pair of role names and digests is the
component's target identity. This definition also applies when `latest` is a
regular executable rather than a symlink. A missing, unreadable, non-regular,
or non-executable role target invalidates Builder binary availability
atomically; the loader MUST NOT omit only that value.

The complete unique provider output and every component target identity MUST
participate in the opaque `registry_revision`. If either changes between
description and creation, creation MUST return the standard stale-schema 409
without creating a project, and the user must reload and review the new list.
Selecting `latest` intentionally records and writes the mutable alias, while
the manifest component revision records its creation-time target identity. A
later run may therefore execute a newer provider target; immutable-release
reproducibility requires selecting a concrete provider value.

TauDEM, alternate soil/land-use methods, designed single-event climate modes,
and optional NoDb mods remain deferred. Amendment 5 registers User-Defined
Climate upload and US Future CMIP5 after their exact definitions and
representative validation; they are no longer part of this deferral. Deferred
values require separate registered definitions and representative validation
before becoming builder-visible. This does not remove or change any Interfaces
preset that already uses them. Later mod IDs SHOULD retain the exact stable
tokens accepted by `[nodb] mods`; filesystem discovery alone MUST NOT register
a mod.

### 7.3 Builder config naming

Builder-created projects MUST use the reserved config token `config` and the
fixed project-owned filename `config.cfg`.

The builder MUST NOT derive the filename or route token from selected locale,
DEM, cell size, backend, representation, WEPP binary, mods, a user-supplied
project name, or the config digest. Those values may change in vocabulary or presentation while
the project's route identity must remain stable.

`config` is reserved for builder-created projects and MUST NOT be registered as
an Interfaces-page shared preset. The builder API MUST assign this token; it
MUST NOT accept a filename or config token from browser input.

Human-readable composition details belong in `config-manifest.json` and the
project UI. They MUST NOT be encoded into the filename. A builder-created
project therefore uses routes containing `/config/` regardless of its selected
component combination.

Creating a different configuration after project initialization creates a new
project. Version 1 does not rewrite `config.cfg` or change a project's config
token in place.

### 7.4 Config Builder UI requirements

The Config Builder is an optional project-creation path. The existing
Interfaces page, its descriptions, and its named-config creation links MUST
remain available. The builder MUST NOT replace, reinterpret, or redirect an
Interfaces link.

Both Config Builder return/navigation links MUST remain plain `/interfaces/`.
The Interfaces page MUST NOT gain locale query grammar, locale filtering, card
remapping, form fields, or locale-bearing config tokens. Its existing cards,
role visibility, order, and actions remain unchanged. Builder creation still
submits its typed selected locale and writes its runtime token into flattened
`[general] locales`; that payload does not authorize locale-bearing established
Interface links.

Version 1 MUST use one page with clearly ordered sections. It MUST NOT use a
multi-step wizard. Sections MAY be collapsible only when their controls,
validation state, and errors remain discoverable and keyboard accessible.

#### Entry and orientation

- Project creation MUST present Config Builder as a distinct choice from the
  existing Interfaces path. On the Interfaces page, that choice MUST appear as
  a **Config Builder** link in the **More** menu and MUST NOT add a separate
  content panel. The link is discoverable only to the canonical power-user
  audience (`PowerUser`, `Dev`, `Admin`, or `Root`); ordinary and anonymous
  users MUST NOT see it. This discovery rule does not replace route or API
  authorization.
- The builder MUST explain that it creates a project-owned `config.cfg` that
  users do not edit. Changing builder selections later requires creating a new
  project; registered missing attributes and an eligible acknowledged same-
  locale capability-envelope refresh may use section 5.1, but refresh never
  substitutes project selections.
- The UI MUST distinguish the project display name from the fixed config token
  `config`. Users MUST NOT enter or edit a config filename or route token.
- Reloading or navigating back after a recoverable validation error SHOULD
  preserve the user's valid selections for the current creation attempt.

#### Required selections

The initial builder MUST present server-described controls for:

1. intended locale/profile;
2. DEM source/resolution available for that locale;
3. the cell size associated with the selected DEM and, for authorized users,
   an optional override;
4. delineation backend, initially TOPAZ or WBT;
5. watershed representation, initially Single OFE or Multiple OFE when
   WhiteboxTools is selected;
6. WEPP binary version from the registered releases compatible with the
   selected representation;
7. climate mode, including Vanilla CLIGEN for every locale;
8. Climate Station Database, separately from climate mode;
9. soil dataset;
10. Land-cover dataset; and
11. optional mods when at least one is registered for the resolved combination.

Labels MUST be human-readable while submitted values use stable registered
component IDs. Technical details such as dataset keys MAY be shown as secondary
help but MUST NOT replace understandable labels.

#### Dependency behavior

- The server-provided builder schema and validation response are authoritative
  for available values, defaults, requirements, and conflicts.
- Selecting a locale MUST limit DEM, cell-size, climate mode, Climate Station
  Database, soil, Land-cover, capability, and mod choices to those supported by
  that locale.
- Selecting a DEM MUST set and display that DEM's associated default cell size.
- Backend, representation, WEPP binary, and mod choices MUST update dependent
  availability when their registered constraints require it. Multiple OFE MUST
  be available only with WhiteboxTools and `wepp_260803`. Changing the backend
  from WBT MUST visibly clear Multiple OFE. Changing the binary away from
  `wepp_260803` MUST visibly clear Multiple OFE. Selecting Multiple OFE MUST
  visibly select its sole compatible binary rather than retain an invalid value.
- The UI MUST NOT merely hide an invalid submitted value and allow it to remain
  in the payload.
- When an upstream change invalidates a downstream selection, the UI MUST clear
  or replace it visibly, explain why, and announce the change. It MUST NOT make
  an unexplained silent substitution.
- A disabled option SHOULD remain discoverable when a concise reason helps the
  user understand the constraint. Options irrelevant to the selected locale or
  component path MAY be omitted.

#### Derived capabilities

The builder MUST show a reviewable summary of the resolved capabilities before
creation, including at least:

- climate datasets/methods that will be available;
- the selected Climate Station Database;
- soil-building methods that will be available;
- land-cover choices when more than one is relevant; and
- initialized mods and material limitations introduced by the combination.

Derived capabilities are explanatory in version 1 unless the component schema
explicitly declares them user-selectable. The client MUST NOT independently
invent or broaden capability lists.

#### Validation and review

- Validation MUST run against the complete proposed combination, not only each
  field in isolation.
- After a successful Builder-description response, the browser MUST populate
  all registered options, apply locale defaults, resolve dependent choices, and
  then automatically validate the complete proposal. Each subsequent
  user-originated form change MUST automatically invalidate the prior review,
  settle dependent choices, and validate the resulting complete proposal.
- The Builder MUST NOT require or present a general-purpose Review Selections
  action. The review is the server-resolved summary, not a separate manual
  validation step. A stale-registry reload MUST use the same hydrate-then-
  validate path.
- Only the response for the latest complete proposal under the latest completed
  Builder-description load may render review/errors or enable Create. Starting a
  description load MUST invalidate pending validation responses and disable the
  selection controls until that load succeeds or fails. A failed description
  load MUST retain its diagnostic and MUST NOT start validation.
- A stale-registry reload MUST preserve every still-registered selection. An
  invalidated selection MUST use its current registered default, and the
  replacement MUST be explained and announced before the refreshed complete
  proposal is validated. A failed refreshed validation MUST retain its own
  diagnostic and keep Create unavailable.
- Field errors MUST be associated with their controls and a page-level summary
  MUST link or move focus to each invalid field.
- The Create action MUST remain unavailable while required selections are
  missing, validation is pending, or the server reports an invalid
  combination.
- Before creation, the UI MUST present a review summary containing the locale,
  DEM, cell size, backend, representation, WEPP binary version, climate mode,
  Climate Station Database, soil, Land-cover, mods, and derived capabilities.
- The review MUST state that the generated runtime filename is `config.cfg` and
  that the complete selections and provenance will be recorded in
  `config-manifest.json`.
- Initial and change-triggered validation, whether successful or failed, MUST
  NOT move focus. Validation failure MUST preserve the proposal and retain the
  linked page summary, field associations, and live announcement. A form change
  or page reload MAY retry a failed validation without adding a permanent manual
  review control.
- Advanced raw `.cfg` editing or arbitrary key/value injection is prohibited.

#### Submission and completion

- Rq-engine MUST provide authenticated server routes for builder description,
  validation, and creation as well as the configuration-update availability,
  preview, and apply flow in section 5.1. Exact route paths remain an
  implementation detail.
- Builder description and validation responses MUST include one opaque
  `registry_revision`. Creation MUST submit that revision. If it is no longer
  current, the server MUST create no project and return canonical `409
  stale_builder_schema`; the UI MUST reload the schema and require the user to
  review the resolved summary again.
- Builder description MUST report `builder_description_schema_version = 2` and
  include `capability_graphs_by_locale` as specified in section 7.2.2. Its
  singular `capability_graph` is the frozen historical Continental-US
  schema-v2 compatibility member.
- Builder description MUST include `components_by_locale`; top-level
  `components` is the matching historical Continental-US-only compatibility
  population.
- Validation and creation MUST require
  `builder_description_schema_version = 2`. Missing or unsupported description
  versions fail with `409 unsupported_builder_schema` before mutation.
- Submission MUST use the existing authenticated project-creation security
  boundary, including its CSRF/CAP/session behavior as applicable.
- The Create action MUST prevent accidental duplicate submissions while a
  request is active.
- The server MUST revalidate every selection; client-side filtering is not a
  security or correctness boundary.
- A successful response MUST navigate to the created project using config token
  `config` and MUST identify the created run ID.
- A failed response MUST retain the proposed selections, show an actionable
  error, and MUST NOT represent a partially initialized project as ready.
- Retry behavior MUST follow section 7.6 and MUST NOT silently create multiple
  projects from one successful request.

#### Accessibility and responsive behavior

- Every control MUST have a programmatic label, instructions, and an associated
  error relationship.
- All selection, review, correction, and submission paths MUST be operable by
  keyboard alone with visible focus.
- Dynamic option, validation, and creation-status changes MUST be announced to
  assistive technology without moving focus unexpectedly.
- Required, unavailable, selected, invalid, and completed states MUST not rely
  on color alone.
- Failed automatic validation MUST announce the linked error summary without
  moving focus. Focus MUST move to a clear creation-status target after
  submission.
- The builder MUST remain usable at narrow viewport widths without horizontal
  scrolling for its primary controls and actions.
- Help text and disabled-reason text MUST remain available at browser zoom up to
  200 percent.

#### UI exclusions for version 1

Version 1 does not include:

- editing a generated configuration after project creation;
- uploading an arbitrary config;
- starting from and modifying an Interfaces preset;
- saving reusable private builder templates;
- exposing raw configuration sections or filesystem paths; or
- migrating an existing project through the builder.

### 7.5 Cell-size defaults and privileged override

Every registered DEM component MUST declare one associated default cell size in
meters. The default MUST be one of these exact integer values:

```text
1, 2, 5, 10, 25, 30, 90, 100
```

For an ordinary authorized project creator, selecting the DEM determines the
cell size. The UI MUST display the effective cell size as read-only explanatory
information and MUST NOT offer an override control.

Only callers with at least one normalized role of `PowerUser`, `Admin`, or
`Root` may override the DEM-associated default. For those callers:

- the UI MUST use a select/radio control containing only the fixed values above;
- the DEM-associated value MUST remain the initial selection;
- selecting a non-default value MUST identify it as an advanced override and
  warn that changing raster resolution does not increase the source DEM's
  native information content; and
- returning to the DEM-associated value MUST clear the override state.

The creation request SHOULD represent this distinction explicitly, for example
with an optional `cellsize_override` field, rather than making the server infer
intent from a required effective `cellsize` value.

The server MUST derive the default from the registered DEM component and MUST
recheck the caller's current roles at submission. A missing override resolves
to the DEM default. An override outside the fixed set is invalid. An override
from a caller without `PowerUser`, `Admin`, or `Root` MUST return the canonical
`403 forbidden` response and MUST NOT create a project. Hiding the override in
the UI is not authorization enforcement.

Role matching MUST be case-insensitive and support the canonical string and
named-role claim representations already accepted by rq-engine authentication.
Role loss between loading the builder schema and submission MUST fail closed.

The review summary MUST show the DEM-associated default, the effective cell
size, and whether a privileged override is active. The flattened config records
only the effective `[general] cellsize`. The manifest MUST additionally record
the DEM default, effective value, and source as `dem_default` or
`privileged_override`. Security/audit logging MUST identify the authenticated
actor for a successful override without writing bearer tokens or other secrets
to the manifest or logs.

### 7.6 Creation idempotency and incomplete initialization

Named-preset and builder submissions MUST include a client-generated,
cryptographically random creation idempotency key of at most 200 characters.
The server MUST reuse the existing bounded Redis `SET NX` idempotency pattern
with a 24-hour retention window; version 1 MUST NOT add a project-creation
database or resumable transaction service.

The request fingerprint MUST include creation mode, preset/component IDs,
normalized builder selections, normalized supported overrides, and builder
registry revision. It MUST exclude credentials, CAPTCHA responses, bearer
tokens, session material, and CSRF values. Authenticated keys are scoped to the
actor. A creation path without a durable actor is scoped by its unguessable
idempotency key and existing creation security boundary.

For the same key and fingerprint, a completed replay returns the original
run ID and redirect/location result. The same key with a different fingerprint
returns canonical `409 idempotency_key_conflict`. A concurrent replay returns
canonical `409 creation_in_progress` with `Retry-After`. Authentication and
validation failures occur before reservation. Initialization or ownership
failure releases the reservation so an explicit retry may allocate a fresh run.

Creation remains synchronous at the existing project-creation boundary; it is
not an RQ job in version 1. Success MUST be recorded before returning the
existing `303` redirect or an equivalent synchronous JSON result. A failed or
crashed initialization MUST never be published as ready. Existing scoped
cleanup MAY remove its newly allocated directory; an undisclosed orphan is an
operator cleanup concern, not a resumable project.

### 7.7 Run page document identity

The established run page's HTML document title MUST be exactly the
route-resolved `runid` for the complete page lifetime. It MUST NOT derive title
content from a legacy config name, config token, config filename, project
display name, scenario, locale, current nested/PUP controller identity, or
stored capability metadata. Saving, clearing, or otherwise changing a project
display name or scenario MUST NOT mutate the document title. Missing metadata
MUST NOT expose `None`, `Untitled`, or an empty suffix in the title.

This rule applies equally to named-preset, project-local, and flattened
project-owned configurations. The run ID is required route identity; config
names, project names, and scenarios are optional metadata and are not document
identity. Invalid or path-dangerous run IDs remain rejected by the existing
route boundary. Values that reach HTML rendering remain subject to the existing
Jinja autoescaping boundary. The title is not persisted and does not rewrite
project files or provenance.

### 7.8 Config Builder run summary

The Config Builder summary surface is selected solely by the route config stem:
`/runs/<runid>/config/` MUST expose a read-only summary of the effective project
configuration, while every other config stem MUST omit the locale pill,
launcher, and dialog. A nested/PUP request whose active route stem is `config`
uses the active resolved run context and follows the same rule. Test-only flags,
including `playwright_load_all`, MUST NOT expose this surface for another config
stem. Existing run-read authorization MUST complete before any summary is
rendered. This summary MUST NOT mutate project state, add a network request, or
replace missing run values with current Builder registry defaults.

When the run has a resolved locale profile, the header MUST render a locale
pill in the metadata sequence immediately after the projection position. The
pill MUST use the effective canonical locale ID with the exact form
`locale: <canonical-id>`; for example, Continental US renders as
`locale: continental-us`. A runtime locale token, translated display alias, or
misspelled alias MUST NOT replace the canonical ID.

The run header's More menu MUST contain a `Config Summary` button that opens an
accessible, read-only dialog. The dialog MUST contain one two-column table with
these row headers in this order:

1. Locale
2. Delineation Backend
3. Representation
4. DEM Data Source
5. Cell Size (m)
6. CLIGEN Database

Locale MUST use the non-empty canonical profile ID resolved from the effective
run config. DEM Data Source and CLIGEN Database MUST use selected canonical IDs
persisted in stored project capability authority; a live legacy/preset graph
MUST NOT supply its defaults as if they were selections. Delineation Backend
MUST use the normalized effective runtime backend ID. Representation MUST be
`Single OFE` or `Multiple OFE` according to the effective runtime model. Cell
Size (m) MUST be the effective runtime cell size expressed as a number in
meters, not a freshly resolved DEM default. When the required persisted or
runtime evidence for a field is absent, the value is `Not available`.

All six rows MUST remain present when the summary is available. If an
individual effective value is absent, the corresponding cell MUST display
`Not available`; the page MUST NOT fail and MUST NOT infer a replacement from
the current registry. If no project capability authority can resolve a locale
for the `/config/` run, the locale pill is omitted while the modal remains
available with honest `Not available` cells.

The dialog MUST follow the shared WEPPcloud modal behavior for accessible name,
focus containment and return, Escape and dismiss controls, and active-theme
styling. Its table MUST use semantic row headers, remain reachable at narrow
viewport widths, and escape all displayed values as text.

## 8. Composition and Precedence

Composition MUST be deterministic and schema-driven. The conceptual order is:

1. shared defaults;
2. locale/profile attributes;
3. terrain and DEM component;
4. delineation backend component;
5. watershed representation component;
6. WEPP binary component;
7. selected mod components;
8. capability profile; and
9. explicit builder selections or supported named-preset overrides.

This order preserves the current build-chain writeover model. Components are
ordered contributors, not exclusive option owners. A later applicable layer
MAY overwrite a value written by an earlier layer, and the last writer
determines the effective value. Each contributor MUST declare the keys it may
write. A write outside that declaration or a collision outside the registered
chain MUST fail validation. The manifest records the complete contributor
order and the effective writer for each value added by an update.

The resolver MUST produce the same canonical `.cfg` bytes for the same schema,
component versions, and selections, excluding fields explicitly documented as
non-deterministic. Timestamps belong in the manifest, not the `.cfg`.

### 8.1 Canonical `.cfg` serialization

Byte identity applies to the resolved configuration map, not to source-file
comments, whitespace, or insertion order. The canonical serializer MUST emit:

- UTF-8 without a byte-order mark;
- LF line endings and exactly one terminal LF;
- case-sensitive section and option names;
- sections and options in ascending Unicode code-point order;
- section headers as `[section]` and options as `option = value`;
- one empty line between sections and no other empty lines; and
- no comments, multiline values, no-value options, interpolation, or
  nondeterministic fields.

The separate sanitization work package MUST inventory the currently accepted
scalar/list forms, define one canonical lexical encoding for every supported
schema type, normalize shared defaults and presets to those forms, and add
golden round-trip and byte-identity fixtures before a flattened writer is
enabled. At minimum it MUST reject duplicate case-sensitive keys/sections,
case-only collisions, unsupported literals, inline comments that are part of a
raw value, non-finite numbers, and secret/runtime-host-bound values. Two source
chains that resolve to the same typed map MUST then produce identical bytes.

This staged normalization is required because current configs contain mixed
quoted/unquoted strings, list spacing, and inline-comment forms. The project-
owned serializer MUST NOT canonicalize those forms by guessing their intended
type.

### 8.2 Component registry format and ownership

Registered builder components and profiles MUST be declarative, real TOML
documents parsed with Python's `tomllib` (or its supported compatibility
equivalent), except for the bounded trusted-provider exceptions below. They
are source definitions for the builder and resolver; they are not runtime NoDb
configuration files. The generated, flattened project-owned configuration
remains INI-style `.cfg` as defined in section 5.

The registry SHOULD use a structure equivalent to:

```text
wepppy/nodb/config_builder/
  schema.py
  registry.py
  resolver.py
  profiles/
    locales/
    dem/
    delineation/
    representation/
    wepp_binary/
    capabilities/
    mods/
```

Each TOML document MUST declare a stable component ID, schema version, source
revision identity, owned configuration attributes, constraints, and any
references to other registered component or capability IDs. The typed Python
registry MUST validate every document before exposing it to the builder or
resolver. Invalid IDs, unknown references, undeclared writes, malformed values,
or contradictory constraints MUST fail explicitly; they MUST NOT be ignored or
repaired through implicit defaults.

WEPP binary components are one runtime-provider exception. The trusted
registry loader MUST synthesize exactly one typed `wepp_binary` component for
each unique value returned by `get_linux_wepp_bin_opts()`; it MUST NOT read a
second binary ID allowlist from TOML. Each synthesized definition uses the
provider value as its stable component ID and `[wepp] bin` write, declares a
provider schema revision, records its resolved role target identity in its
source revision, and participates in the registry digest exactly like a TOML
component. Empty output, an invalid component ID, an unavailable `wepp_260803`
default, or an unusable provider value invalidates the registry atomically.
The canonical typed locale, DEM, soil, land-cover, and climate authorities are
the second bounded exception. The trusted registry loader MAY synthesize their
Builder components directly so a large dataset family such as C3S is not copied
into parallel TOML allowlists. It MUST synthesize only IDs referenced by an
explicitly `builder_exposed` profile, preserve each domain-owned runtime value
and source revision, generate deterministic component writes and constraints,
and include every definition in the registry digest. Unknown IDs, missing
runtime mappings, or partial profile closure invalidate the registry atomically.
No other non-binary component may be synthesized without a later contract
amendment.

For this exception, the complete executable source boundary is
`wepppy/nodb/locales/locale_profiles.py`, `climate_catalog.py`, and
`landuse_catalog.py`, plus canonical WEPP provider functions in
`wepp_runner/wepp_runner.py`. `LocaleProfile` objects themselves MAY be
synthesized into locale components; they need not be copied to TOML. Their
profile source revision, exact runtime token, locale-owned deterministic writes,
and ordered data IDs MUST enter the registry digest. The config-builder owns
composition; the named locale/data domain modules own identities, runtime
mappings, and defaults. Shared presets, archived packages, test fixtures,
filesystem discovery, UI labels, and frontend code are excluded from authority.

The config-builder core owns:

- the component/profile document schema and validation;
- stable-ID registration and reference resolution;
- composition order, option ownership, and declared override relationships;
- constraint evaluation and server-facing builder descriptions;
- canonical `.cfg` serialization, manifest generation, and additive amendment
  resolution; and
- compatibility rules for registry schema versions.

Subsystem/domain owners own the declarative definitions for their behavior:

- locale and DEM/data-source maintainers own locale and terrain definitions;
- watershed maintainers own delineation and representation definitions;
- WEPP binary release maintainers own registered binary definitions and their
  representation compatibility;
- climate, soils, and land-cover maintainers own their capability catalogs; and
- each NoDb mod owner owns that mod's component definition and constraints.

Locale profiles compose allowed component and capability IDs and locale-level
constraints. They MUST NOT duplicate the runtime settings owned by the
referenced DEM, backend, representation, WEPP binary, capability, or mod
components. Shared
named `.cfg` presets remain owned by the existing Interfaces creation path and
are not converted into registry profiles merely to support the builder.

Component IDs are durable provenance identifiers and MUST NOT be renamed or
reused with incompatible semantics. A materially incompatible meaning requires
a new ID, such as `continental-us-v2`. Compatible additions may retain the ID
with an incremented source/schema revision and are eligible for the merge-only
update rules in section 5.1. The immutable parent chain MUST record the exact
IDs and revisions used to create the project. Amendment entries record the
current source revisions used for later updates. Updates resolve the current
definition registered under each stable ID; the registry is not required to
retain executable historical definitions.

For schema-v2 and schema-v3 graphs, a compatible addition to a live profile
does not alter the validity of a previously complete stored graph. The reader
MUST maintain an append-only catalog of immutable canonical structural payloads
and SHA-256 identities per locale. Creation uses only the current identity;
stored validation accepts only a cataloged identity. An identity or payload is
never redefined or removed. Unknown self-consistent graphs fail closed.

The structural payload contains the locale ID; every non-runtime axis; all
climate, landuse, soil, mod, and representation relations; all per-dataset
method defaults; and normalized allowed delineation/representation pairs. It
MUST exclude project selection defaults in `capability_defaults`,
`provider_revision`, `wepp_binaries`, `wepp_binary_revisions`, and the binary
member of model tuples. These exclusions distinguish immutable envelope/method-
default structure from the user's creation selections. Ordinary graph
validation still enforces all stored binary tuples and revisions.

`structure_sha256` is SHA-256 over canonical sorted-key compact JSON encoded as
UTF-8. The accepted catalog retains both payload and hash. Closed stable-ID
vocabularies are the union of accepted payloads; a dataset/runtime catalog ID
referenced by one is retirement-only unless a separately ratified compatibility
plan replaces its runtime mapping.

The initial production entries are the one structure per locale first shipped
by `280cf7e84`; current code has the same identities. A test-only catalog MUST
exercise a distinct same-locale old/new pair, but those identities are not
production authority. The first real structural map/capability change requires
a separately ratified append-only identity, direct fixture, reader-first
deployment, and Forest evidence before its refresh writer is exposed.

The WEPP provider axis remains dynamic and is validated by immutable shape and
policy: stable binary ID grammar, role-resolved digest grammar, exhaustive
binary revision keys, Single-OFE TOPAZ/WBT tuples for every stored binary, and
exactly one Multiple-OFE tuple, `wbt|multiple-ofe|wepp_260803`. A stored graph
does not need to match the current provider's binary population.

## 9. Capability Contract

The resolved config MUST record stable semantic identifiers rather than UI
labels or raw enum values. The following is a historical WP12C Continental-US
schema-v3 example that remains valid stored authority; amendment 5 supersedes
it for current Builder creation/refresh with the exact axes in section 7.2.2
and ADR-0047:

```ini
[capabilities]
schema_version = 3
locale_profiles = ["continental-us"]
dem_sources = ["usgs-ned1-2024", "usgs-ned13-2022"]
climate_datasets = ["vanilla_cligen", "prism_stochastic", "observed_daymet", "observed_gridmet"]
climate_station_databases = ["cligen-stations-legacy", "cligen-stations-2015", "cligen-stations-ghcn"]
climate_station_methods = ["auto", "distance", "multi_factor"]
climate_spatial_methods = ["single", "multiple", "interpolated"]
soil_datasets = ["ssurgo-gnatsgso-2025"]
soil_builders = ["gridded", "single_mukey", "single_database"]
landuse_datasets = ["nlcd-2019"]
landuse_methods = ["gridded", "single", "upload"]
delineation_backends = ["topaz", "wbt"]
watershed_representations = ["single-ofe", "multiple-ofe"]
wepp_binaries = ["wepp_260803"]
mods = []
allowed_model_tuples = ["topaz|single-ofe|wepp_260803", "wbt|single-ofe|wepp_260803", "wbt|multiple-ofe|wepp_260803"]

[capabilities.wepp_binary_revisions]
wepp_260803 = "provider-v1:watershed=<sha256>:hillslope=<sha256>"

[capabilities.climate_station_methods]
vanilla_cligen = ["auto", "distance", "multi_factor"]
prism_stochastic = ["auto", "distance", "multi_factor"]
observed_daymet = ["auto", "distance", "multi_factor"]
observed_gridmet = ["auto", "distance", "multi_factor"]

[capabilities.climate_spatial_methods]
vanilla_cligen = ["single", "multiple"]
prism_stochastic = ["single", "multiple"]
observed_daymet = ["single", "multiple", "interpolated"]
observed_gridmet = ["single", "multiple", "interpolated"]

[capabilities.climate_station_defaults]
vanilla_cligen = "auto"
prism_stochastic = "auto"
observed_daymet = "auto"
observed_gridmet = "auto"

[capabilities.climate_spatial_defaults]
vanilla_cligen = "single"
prism_stochastic = "single"
observed_daymet = "single"
observed_gridmet = "single"

[capabilities.landuse_methods]
nlcd-2019 = ["gridded", "single", "upload"]

[capabilities.landuse_method_defaults]
nlcd-2019 = "gridded"

[capabilities.landuse_methods_by_representation]
single-ofe = ["gridded", "single", "upload"]
multiple-ofe = ["gridded", "upload"]

[capabilities.soil_builders]
ssurgo-gnatsgso-2025 = ["gridded", "single_mukey", "single_database"]

[capabilities.soil_builder_defaults]
ssurgo-gnatsgso-2025 = "gridded"

[capabilities.mod_requires]

[capabilities.mod_conflicts]

[capability_defaults]
locale_profile = "continental-us"
dem_source = "usgs-ned1-2024"
climate_dataset = "vanilla_cligen"
climate_station_database = "cligen-stations-2015"
landuse_dataset = "nlcd-2019"
soil_dataset = "ssurgo-gnatsgso-2025"
delineation_backend = "wbt"
watershed_representation = "single-ofe"
wepp_binary = "wepp_260803"
```

Climate capabilities MUST use climate catalog IDs, not numeric
`ClimateMode` values. Soil capabilities MUST introduce stable IDs rather than
using `SoilsMode` integers because existing enum values include aliases.
Station, spatial, landuse, soil, delineation, and representation methods MUST
likewise use stable semantic IDs with an explicit domain-owned runtime mapping.
Schema v2 MUST persist dataset-to-method adjacency, allowed
backend/representation/binary tuples, representation-to-landuse-method
adjacency, mod-conditioned edges, and defaults. Axis unions alone MUST NOT
authorize a cross-product. Compound tuple serialization
uses `|`, which is forbidden in component IDs; readers MUST validate all tuple
members against their axes.
Relation section keys MUST exhaust the corresponding dataset/mod axis. Each
adjacency value MUST be a non-empty subset of the target method axis, except
that `mod_conflicts` MAY contain an empty list. Each per-source default MUST be
a member of that source's adjacency list. Relation sections MUST reject orphan
keys, missing keys, duplicate values, unknown axes, and values outside their
axes. Every model tuple member MUST exist in its axis, every advertised axis
value MUST participate in at least one valid tuple where applicable, and the
global defaults MUST identify one advertised valid tuple. Stable IDs MUST match
the closed ASCII grammar `[a-z][a-z0-9_-]{0,127}`; therefore `:` and `|` cannot
occur in them. Mod relation tokens use the closed `<axis>:<stable-id>` grammar.
The only permitted relation axes are `climate_dataset`,
`climate_station_method`, `climate_spatial_method`, `landuse_dataset`,
`landuse_method`, `soil_dataset`, `soil_builder`, `delineation_backend`,
`watershed_representation`, `wepp_binary`, and `mod`.
Unknown relation axes, missing mod keys, and invalid targets invalidate schema
v2. Each axis, relation, and tuple list is limited to 4096 unique IDs; IDs are
limited by the stable-ID grammar and serialized capability sections to 4 MiB.
These invariants are checked before description, creation, view rendering,
mutation, or enqueue.

Schema v3 inherits every schema-v2 axis, relation, closure, size, and
fail-closed invariant and adds mandatory `climate_station_databases` plus
`capability_defaults.climate_station_database`. The default MUST be a member of
the axis. Climate-station database IDs use the same stable-ID grammar and the
selected component owns the exact `climate.cligen_db` write. Schema-v3 creation
MUST NOT infer that selection from locale, climate dataset, shared defaults, or
the current runtime catalog. `climate_station_database` is also an allowed mod
relation axis in schema v3.

`capabilities.wepp_binary_revisions` keys MUST exhaust `wepp_binaries`. Each
value MUST bind the ordered watershed and hillslope executable SHA-256 role
identities using the closed
`provider-v1:watershed=<sha256>:hillslope=<sha256>` form. These identities MUST
contribute to `provider_revision`, the capability component revision, and the
manifest parent chain. Changing any advertised role target therefore changes
stored provenance even when its binary ID is not the selected default.

`landuse_methods_by_representation` keys MUST exhaust
`watershed_representations`; each value MUST be a non-empty subset of
`landuse_methods`. A run's current representation intersects this relation with
the selected landuse dataset adjacency before presentation or mutation. In
particular, `multiple-ofe` authorizes `gridded` and `upload`; `single` MUST be
rejected before mutation or enqueue even when present in the project-wide
landuse-method union.

For flattened projects:

- UI option lists MUST be derived from the resolved capability section.
- Server mutation/build endpoints MUST validate new selections against the same
  resolved capability section.
- A hidden UI option MUST NOT remain invokable as an unsupported backend
  selection.
- Dataset and method axes MUST be resolved separately. Templates MUST render
  climate station/spatial radios, landuse modes/datasets, soil modes/datasets,
  and watershed backend/representation choices from those resolved axes.
- Every paired mutation or build endpoint MUST validate a newly submitted value
  against the same stable IDs before NoDb mutation or enqueue.
- Run-scoped rq-engine controller schemas, templates/defaults, aggregated
  endpoint operation documents, pipeline, and readiness metadata MUST report
  only the stored authority. They MUST NOT repopulate an omitted choice from a
  current provider listing.

Run authority is selected in this order:

1. a complete flattened schema-v2/schema-v3 graph is validated and remains the
   stored presentation/submission authority, independent of live registry
   drift until an eligible schema-v3 refresh commits;
2. a flattened schema-v1 project satisfying the projection-eligible preset
   rules below and exactly one recognized Builder base locale resolves the current Builder graph for only
   its climate and land-cover presentation/submission surfaces; its other v1
   axes retain established compatibility behavior;
3. other flattened no-capability and schema-v1 projects retain their
   established compatibility behavior without new locale validation or live
   registry use;
4. a non-flattened legacy run resolves effective `.cfg` locale. Exactly one of
   `us`, `eu`, `canada`, `au`, or `earth` selects the current Builder graph for
   `continental-us`, `europe`, `canada`, `australia`, or `global-earth`; and
5. non-Builder bases, overlays, Turkey, and RHEM retain existing localized
   catalogs without a synthesized Builder graph.

Builder creation, recognized legacy resolution, refresh preview, and refresh
apply MUST share one public server-side locale-to-graph resolver. A required
live registry failure returns `503 builder_registry_error` with diagnostic
details, error ID, and `Retry-After: 5`; it MUST NOT broaden to a fallback
catalog. Invalid non-flattened locale returns `409 locale_authority_invalid`.
Auth and run access checks occur first.

These failures have the same three-boundary transport. HTML run-page requests
render a diagnostic error page with the status, code, diagnostic details, and
error ID. Flask JSON and rq-engine JSON use their canonical envelopes with the
same status/code, diagnostic `details`, and `error_id`. Invalid locale is HTTP
409 on all three boundaries. Registry unavailability is HTTP 503 with
`Retry-After: 5` on HTML, Flask JSON, and rq-engine JSON. Authentication,
authorization, run access, and ownership failures retain precedence over locale
or registry resolution and MUST NOT be replaced by these diagnostics.

Only the enumerated landuse, soil, and climate presentation/discovery/set/build
consumers adopt this resolved run authority. Global `NoDbBase.locales`, other
locale-sensitive controllers, advanced climate toggles, landuse edit/upload,
soil `ksflag`, disturbed soil version, reports, and job lifecycle remain
unchanged.

An eligible refresh adopts current axes, relations, per-dataset method defaults,
and provider/binary identities while preserving project `capability_defaults`,
mods, and `climate.cligen_db`. Preview and manifest delta metadata record the
canonical support state of added IDs; support state is not a stored graph axis.
Persisted controller state
outside a refreshed axis remains visible once as disabled current state and may
be rebuilt unchanged, but cannot authorize a different unsupported value.
Current Builder defaults MUST NOT replace project selections.

User-Defined Climate upload replaces content and is not an unchanged rebuild.
Whenever graph authority is resolved, the upload-cli route MUST require
`user_defined_cli` in the climate axis before multipart read/save, timestamp
removal, reservation, or enqueue. An outside-authority current value does not
authorize upload. A compatibility state with no graph retains its established
upload behavior.

Capability compatibility is versioned as follows:

- no capability section means legacy locale/catalog behavior;
- capability keys without `schema_version` are schema v1, and only present v1
  axes restrict behavior; missing WP12B axes retain legacy behavior except for
  the valid named-preset climate/land-cover projection below;
- a present-empty or malformed mandatory v1 axis is an explicit configuration
  error; optional v1 axes such as `mods` MAY be present-empty;
- schema v2 requires every mandatory axis, relation, tuple set, and default;
  missing, empty, malformed, contradictory, or partial authority fails
  explicitly without consulting the current registry;
- schema v3 requires the complete schema-v2 graph plus the station-database
  axis/default; missing, empty, malformed, contradictory, partial, or newer
  authority fails explicitly without consulting the current registry;
- an already persisted current selection omitted from authority remains visible
  but disabled for reselection, and an ordinary build may consume it; a newly
  submitted different unsupported value fails before mutation or enqueue; and
- merge-only update MUST NOT add WP12B axes to a v1 or legacy project because
  doing so would invent capabilities prohibited by section 5.1.

Schema v1 retains its established coarse-axis authority except for a bounded
named-preset projection. A projection-eligible manifest with `source_kind =
"preset"` and exactly one recognized Builder base locale uses the current
locale graph for only climate and land-cover presentation, discovery, setter, and build
authority. Stored v1 climate/landuse lists remain provenance evidence but do
not broaden or narrow those two domains. Soil, model, mod, and every other v1
axis retain existing behavior. The projection never rewrites the config,
manifest, or NoDb state. The v2 graph rules MUST NOT otherwise be
retroactively inferred for v1.

For this exception, "valid" is intentionally narrower than warning-tolerant
manifest loading. The declared config digest MUST equal current config bytes;
`source_preset` MUST be an active canonical named-preset token and equal the
config filename stem; `parent_chain` MUST be exactly
`defaults/shared-defaults`, then `preset/<source_preset>`; each parent revision
MUST equal SHA-256 of its current server-owned canonical source file; replaying
the recorded allowlisted query overrides through the canonical preset snapshot
resolver MUST reproduce current flattened config bytes exactly; and both the
rematerialized and stored effective configs MUST contain the same exactly one
recognized Builder base with no locale overlay. `source_revision` is descriptive
provenance and MUST NOT authenticate eligibility.
Absent, malformed, newer, digest-mismatched, non-preset, unknown/inactive-
preset, filename-incongruent, chain-incongruent, parent-revision-drifted,
override-invalid, rematerialization-mismatched, locale-incongruent, empty,
unknown-locale, overlay, Turkey, or RHEM state retains schema-v1 compatibility
with no registry call. An unavailable, malformed, or inconsistent canonical
preset-policy corpus is not an unknown-preset fallback: after auth/run access,
it fails with diagnostic HTTP 503 `builder_registry_error`, `Retry-After: 5`,
and no multipart read/save, timestamp removal, reservation, mutation, or
enqueue.

Configuration-update availability, preview, and apply for a historical
schema-v2 Builder run MUST resolve its original parent chain with the frozen
schema-v2 resolver contract. They MUST preserve the original v2 graph and
manifest selection shape, MUST NOT synthesize a Climate Station Database
component or selection, and MUST NOT recompose the run through a current
schema-v3 locale graph. A v2 update may add only attributes authorized by that
v2 parent chain and the existing merge-only update contract. If the frozen v2
chain is unavailable, update availability MUST report unavailable without
altering project bytes. Schema-v3 updates use the corresponding frozen v3
resolver contract and retain the selected station-database component in the
manifest parent chain.

Flattened no-capability projects, schema-v1 projects outside the exact preset
exception, and non-Builder, overlay, Turkey, or RHEM compatibility modes retain
their current locale, mod, catalog, and route behavior. The bounded live-
authority exceptions are a recognized non-flattened legacy base for landuse,
soil, and climate and a valid recognized flattened schema-v1 preset for only
climate and land cover.

## 10. Manifest Contract

`config-manifest.json` MUST be UTF-8 JSON. Schema version 1 MUST contain the
following common fields; none are optional unless explicitly shown as nullable:

```json
{
  "schema_version": 1,
  "resolver_version": 1,
  "source_kind": "builder",
  "source_preset": null,
  "source_revision": "<git revision>",
  "resolved_at": "<RFC 3339 UTC timestamp>",
  "parent_chain": [
    {
      "kind": "component",
      "id": "continental-us",
      "revision": "<source revision>"
    }
  ],
  "selections": {
    "locale": "continental-us",
    "dem": "usgs-ned13-2022",
    "dem_default_cellsize": 10,
    "cellsize": 10,
    "cellsize_source": "dem_default",
    "delineation_backend": "wbt",
    "watershed_representation": "single-ofe",
    "wepp_binary": "wepp_260803",
    "climate": "vanilla_cligen",
    "climate_station_database": "cligen-stations-2015",
    "soil": "ssurgo-gnatsgso-2025",
    "landuse": "nlcd-2019",
    "mods": []
  },
  "config": {
    "filename": "config.cfg",
    "sha256": "<lowercase SHA-256>"
  },
  "amendments": []
}
```

The required common fields are:

- `schema_version`, `resolver_version`, `source_kind`, `source_preset`,
  `source_revision`, and `resolved_at`;
- ordered `parent_chain`, with non-empty `kind`, stable `id`, and source
  `revision` for every source used to construct the original config;
- `selections`, containing normalized creation selections and overrides;
- `config.filename` and `config.sha256`; and
- `amendments`, initially an empty array.

Builder creation MUST set `source_kind` to `builder`, set `source_preset` to
JSON `null`, record all submitted and derived selections shown in the example,
and record the ordered registered component chain.

Builder manifests created before the WEPP-binary component was registered are
not migrated. They remain valid for project loading and model execution, but
configuration-update availability, preview, and apply MUST report unavailable
because their immutable parent chain cannot be re-resolved to the expanded
component chain. The implementation MUST test a real pre-change schema-v1
manifest and MUST NOT synthesize a binary component from its flattened config.

Named-preset creation MUST set `source_kind` to `preset`, set `source_preset`
to the preset basename, and record an ordered parent chain containing shared
defaults and that preset. Its `selections` MUST contain normalized supported
query overrides, or an empty `overrides` object when none were accepted. A fork
MUST copy its parent's complete manifest and parent chain; it MUST NOT derive a
new chain from the fork's route or filename.

The manifest MUST NOT contain secrets, bearer tokens, query credentials, or
environment dumps. Unknown top-level fields MAY be retained for forward
compatibility, but missing or malformed required fields make the manifest
invalid for configuration updates.

In schema version 1, the digest is provenance evidence. A digest mismatch MUST
produce an explicit operator-visible warning, but the mismatch alone MUST NOT
block project loading, ordinary mutation, model execution, or a registered
additive amendment. It MUST NOT automatically delete, rewrite, or repair
project data. Normal parsing, validation, authorization, and downstream model
errors remain enforceable. This warning-only policy avoids bricking an
otherwise usable project; the operation may succeed, or an actionable failure
may surface at the subsystem that cannot use the changed configuration.

The warning MUST be emitted as structured operator logging containing run ID,
config filename, manifest-declared digest, and observed digest, without config
contents or secrets. Authenticated run-page state MUST expose the same
nonblocking warning. Implementations MUST avoid emitting it on every individual
`config_get_*` call; the exact deduplication/rate-limit mechanism is not
contractual.

Each merge-only amendment MUST append one entry containing at least:

- a monotonically increasing sequence number;
- amendment timestamp and application revision;
- resolver version;
- the triggering missing section and option;
- an ordered list of every added section/option, serialized value, owning
  build-chain component, and source revision;
- prior and resulting config SHA-256 digests; and
- reason `missing_registered_attribute_merge`.

Every new amendment entry MUST include `kind` equal to `additive`,
`capability_refresh`, or `combined` and the opaque `preview_id`. Historical
entries without `kind` are interpreted as `additive`; missing `preview_id` is
JSON `null`. A capability or combined entry additionally records:

- acknowledgment revision `PC-24-capability-refresh-v1`;
- prior/resulting config SHA-256 and graph SHA-256 values;
- prior/resulting `structure_sha256` and provider revisions;
- exhaustive prior/resulting WEPP-binary revision objects;
- ordered selected parent-chain `{kind, id, revision}` rows;
- canonical preserved `capability_defaults`, mods, and `climate.cligen_db`;
- one complete reversible changes list; and
- application timestamp and application revision, without actor identity.

Those conceptual values have one durable JSON layout. A capability-only entry
has exactly these required top-level members: integer `sequence`, string
`kind = "capability_refresh"`, non-null string `preview_id`, RFC 3339 UTC string
`applied_at`, string `application_revision`, integer `resolver_version`,
lowercase SHA-256 strings `prior_sha256` and `resulting_sha256`, and object
`capability_refresh`. A combined entry uses `kind = "combined"`, the same
members, and the existing additive trigger/additions/reason members. It MUST NOT
encode a second capability delta elsewhere in the entry.

Manifest `capability_refresh` has exactly `locale_profile`, `locales`,
`preserved_project_selections`, `acknowledgment_revision`, `prior`, `resulting`,
and `changes`. All except `acknowledgment_revision` reuse the exact member
types, nesting, values, null handling, and ordering of preview
`capability_refresh` in section 13.1. `acknowledgment_revision` is exactly
`"PC-24-capability-refresh-v1"`; the preview-only `acknowledgment` object and
warning text are not copied into the manifest. `prior_sha256` and
`resulting_sha256` are the config digests, while the nested `prior`/`resulting`
objects contain graph, structure, provider, binary, and selected-parent-chain
identity. Recovery, availability, and idempotent replay MUST read this layout.

Each change row has string `section` and `option`; `kind` equal to `added`,
`removed`, or `changed`; canonical JSON `before` and `after` with JSON `null`
for absence; lexically sorted `added_ids` and `removed_ids`; and
`added_support` rows sorted by ID with exact `{id: string, support_state:
string|null}` shape. Rows sort by `(section, option, kind)`. `graph_sha256` is
SHA-256 over canonical project-config serialization of exactly the complete
capability sections, including preserved `capability_defaults`.

Prior provenance is limited to stored evidence: aggregate provider revision,
complete stored binary revisions, selected parent-chain revisions, graph hash,
and structure hash. It MUST NOT invent historical per-component revisions for
unselected IDs. Resulting provenance records the corresponding current values.
Canonical support state comes from the registry/provider catalog when defined
and is JSON `null` otherwise; no synthetic maturity value is recorded.

Refresh MUST leave original manifest `selections`, `parent_chain`, source
identity, creation provenance, and prior amendments semantically unchanged. It
appends one entry and updates `config.sha256`. Amendment history is append-only
and MUST NOT contain credentials, bearer tokens, or personal identity.

## 11. Atomicity and Failure Behavior

The config and manifest MUST be completely resolved and validated before NoDb
controller initialization. Each file MUST be written through a temporary file
in the target working directory followed by atomic replacement. The project
MUST NOT be marked or presented as ready until both final files are durable.
The implementation MAY use the existing project-creation boundary and cleanup
mechanisms; version 1 does not require a second two-file transaction protocol
for initial creation.

If resolution, validation, serialization, or persistence fails:

- NoDb initialization MUST NOT begin.
- The project MUST NOT be presented as ready.
- The failure MUST be explicit and actionable.
- Partial temporary files MUST be cleaned up when safely possible.
- Existing project files MUST NOT be silently overwritten.

Concurrent attempts to initialize the same project MUST use the existing
project creation/NoDb concurrency boundary rather than inventing an unrelated
lock.

Every additive, capability-refresh, or combined amendment MUST use one project-
scoped config amendment lock. Both
candidate files MUST be written and fsynced before replacement. Because two
filesystem paths cannot be replaced by one POSIX rename, the implementation
MUST use a small pending-amendment journal containing the expected prior and
resulting hashes. It then replaces the config, replaces the manifest, and
removes the journal. A later reader MUST complete or roll back an interrupted
transaction deterministically before serving configuration.

Before apply can reserve or enqueue, preview MUST validate the complete
resulting config, manifest, pending-amendment journal, and every affected
archive-member size against the existing format and size bounds. An oversized
or otherwise invalid reversible record is diagnostically unavailable. The
writer MUST NOT truncate the delta, omit required provenance, weaken existing
validation, or rely on archive/export to discover the violation after commit.

Before config replacement, recovery retains the prior config/manifest pair.
After config replacement, recovery rolls the manifest forward to the complete
result pair. After manifest replacement, it retains the result pair. Failure or
process death MUST be recoverable from journal bytes without re-resolving a
changed registry value. Concurrent requests for the same preview MUST produce
at most one amendment entry.

Rejection before Redis reservation has no queue or file side effect. Once
accepted, the RQ job is observable history even if its worker fails. A retry is
idempotent only when the latest amendment has the same non-null `preview_id`
and the current config digest equals its `resulting_sha256`; it returns that
result without reservation, enqueue, or another amendment. Null, different, or
non-latest IDs use normal stale handling. A matching ID with digest mismatch
fails `409 config_update_unavailable` diagnostically.

Read-only availability MUST expose `current_digest` and `last_update` for
outcome reconciliation. `last_update` is null or exact `{sequence, kind,
preview_id, prior_sha256, resulting_sha256}`; historical missing kind/preview
report `additive`/JSON `null`. `last_update` contains neither actor identity nor
warning text. When updates are disabled or unavailable, `update_kind` MUST be
JSON `null` and `acknowledgment_required` MUST be false; `current_digest` and
`last_update` remain read-only reconciliation fields. After terminal failure,
browser and direct
clients compare these fields with the preview's prior/resulting digests and
report `not applied`, `committed/recovered`, or an explicit indeterminate
diagnostic. They MUST NOT hide a recovered commit behind a generic failure.

## 12. Fork, Archive, Restore, and Read-Only Behavior

Project fork, archive creation, download, and archive restore MUST preserve the
project-owned config and manifest as ordinary project-root artifacts.

Before copying project artifacts, fork and archive creation MUST acquire the
project config amendment lock and recover any pending amendment transaction.
They MUST copy the config and manifest from one consistent state and MUST NOT
archive a pending-amendment journal as the intended recovery mechanism.

A fork MUST retain the source project's resolved config and manifest by default.
Changing configuration during fork is a separate future contract and MUST NOT
be inferred from the existence of the builder.

Restore MUST use the restored project-owned config when present. Restoring a
legacy archive without one MUST retain shared fallback behavior.

Read-only/public state MUST not change configuration resolution or permit user
config mutation. Opening or reading a project MUST NOT apply an additive
configuration update. An authorized user may request an update only through
the explicit preview-and-apply flow in section 5.1; read-only/public users may
see update availability only if existing project-read authorization permits
the underlying configuration metadata.

## 13. Security Boundary

The builder MUST resolve only registered component IDs and allowlisted values.
It MUST NOT accept arbitrary filesystem paths, configuration section names,
option names, Python literals, environment-variable references, or executable
content from browser input.

The resolver MUST validate configured paths against the existing owned data
roots and config path conventions. Generated files MUST not contain secrets.
Project authorization for creation, read, fork, archive, and restore remains
unchanged.

Before any flattened-config writer is enabled, a separate configuration
sanitization work package MUST inventory shared defaults and named presets,
remove stale credentials, move any live secrets to the existing runtime secret
boundary, and add an enforceable check preventing secret-bearing values from
being materialized into project roots or archives. This contract does not
perform that cleanup. Suspected staleness does not make a credential safe to
copy.

Rq-engine builder and configuration-update routes MUST enforce the existing
project creation/read/mutation authorization boundaries as applicable. The
asynchronous availability check is read-only. Preview and apply require
an authenticated project owner or `Admin`/`Root`; ordinary public/ownerless run
access is insufficient. Apply MUST recheck this authority both when enqueuing
and when the worker begins execution, and it retains all existing
read-only/public project restrictions. The browser MUST request preview and
apply with its authenticated user token directly; it MUST NOT send a session
token first and use an authorization failure as token-class discovery.
Service/session/MCP principals may
mutate only when the existing project-mutation contract explicitly grants it.

Cell-size override authorization is an additional builder-specific privilege.
Possession of ordinary project-creation authority does not grant it. The server
MUST enforce `PowerUser`/`Admin`/`Root` authorization at submission and audit a
successful non-default override.

### 13.1 Rq-engine response boundary

All builder and update routes MUST use the canonical RQ response and error
envelopes. Builder description/validation, update availability, and update
preview are synchronous read operations. Builder creation remains synchronous
as defined in section 7.6. Update apply is asynchronous and MUST return
canonical `202` with `job_id`, except an exact latest-preview idempotent replay
of an already committed amendment returns HTTP 200 without enqueue and exactly
`{applied: true, recovered: true, sequence: integer, prior_digest: string,
resulting_digest: string}`. A normal RQ job result uses the same fields with
`recovered: false`.

Update availability additionally returns read-only `current_digest`, nullable
`last_update`, nullable `update_kind`, and `acknowledgment_required`. Preview
returns `current_digest`, deterministic `resulting_digest`, complete additions,
nullable capability-refresh detail, and the exact update kind. Availability
MUST NOT expose the graph delta.

Preview `update_kind` is exactly `additive`, `capability_refresh`, or
`combined`. `capability_refresh` is JSON `null` for `additive`; otherwise it is
an object with exactly these typed members:

- `locale_profile`: stable-ID string;
- `locales`: the unchanged ordered runtime-token string list;
- `preserved_project_selections`: exactly
  `{capability_defaults: object, nodb: {mods: string[]}, climate:
  {cligen_db: string}}`. `capability_defaults` has exactly the string members
  `locale_profile`, `dem_source`, `climate_dataset`,
  `climate_station_database`, `landuse_dataset`, `soil_dataset`,
  `delineation_backend`, `watershed_representation`, and `wepp_binary`.
  `mods` is the exact ordered stable-ID list from config; no set reordering or
  inferred default is allowed. `cligen_db` is the exact configured manager
  selector string;
- `acknowledgment`: `{required: true, revision:
  "PC-24-capability-refresh-v1", text: string}`, where `text` is the exact
  warning in section 5.1;
- `prior` and `resulting`: objects containing string `graph_sha256`, string
  `structure_sha256`, string `provider_revision`,
  `wepp_binary_revisions` as a stable-ID-to-revision string object, and
  `selected_parent_chain` as an ordered list of exact
  `{kind: string, id: string, revision: string}` objects; and
- `changes`: a list sorted by `(section, option, kind)`. Each row is exactly
  `{section: string, option: string, kind: "added"|"removed"|"changed",
  before: canonical JSON value|null, after: canonical JSON value|null,
  added_ids: string[], removed_ids: string[], added_support: object[]}`.
  Both ID lists sort lexicographically. `added_support` sorts by ID and each row
  is exactly `{id: string, support_state: string|null}`.

The `graph_sha256`, `structure_sha256`, `changes`, preview-ID binding, and
canonical JSON rules are exactly those in sections 5.1 and 8. Availability and
all operation documents MUST describe this complete schema without weakening a
required member to an untyped object.

The UI contract depends on these stable error codes:

- `validation_error` (`400`) with field-addressable details;
- `forbidden` (`403`);
- `not_found` (`404`);
- `idempotency_key_conflict` (`409`);
- `creation_in_progress` (`409`);
- `stale_builder_schema` (`409`);
- `unsupported_builder_schema` (`409`);
- `stale_config_preview` (`409`);
- `capability_refresh_acknowledgment_required` (`400`);
- `config_update_unavailable` (`409`);
- `config_update_in_progress` (`409`);
- `locale_authority_invalid` (`409`);
- `builder_registry_error` (`503`) with `Retry-After: 5`;
- `unsupported_config_schema` (`409`); and
- `capability_authority_invalid` (`409`) with diagnostic `details` when a
  created run's schema-v2/schema-v3 graph is malformed, partial, contradictory,
  or newer than the reader.

Bearer-authenticated rq-engine calls remain outside the browser CSRF boundary.
Cookie-backed calls MUST follow the canonical same-origin/CSRF contract. Exact
route paths, cache implementation, and exception messages are not contractual.

## 14. Compatibility and Rollout

### 14.0 Prerequisite: configuration sanitization

Complete and validate the separate sanitization work package defined in
section 13 before enabling either named-preset or builder flattened-config
creation. Reader compatibility work may land earlier, but writer feature flags
MUST remain disabled until the sanitization gate passes.

### 14.1 Phase 1: Canonical move and symlink compatibility

Move the tracked shared defaults file from `_defaults.toml` to `_defaults.cfg`.
Create the shared `_defaults.toml` path as a relative symlink to
`_defaults.cfg`; it MUST NOT be a second regular-file copy. Update the central
resolver and direct consumers to use the project-local and shared precedence in
section 6.2.

All deployed versions MUST continue to operate during this phase. A bare rename
without both the compatibility reader and symlink is prohibited.

### 14.2 Phase 2: Local automated validation

Complete the defaults-name regression matrix and project-owned config tests in
section 15. Confirm that serialized `.nodb` files retain their config token but
do not embed either defaults filename. Validate new project creation, legacy
project reopen, fork, archive, and restore locally.

The compatibility reader is controlled by
`WEPPPY_PROJECT_CONFIG_READER_ENABLED`. The variable is disabled when absent
and accepts only explicit boolean values (`1/true/yes/on` or
`0/false/no/off`, case-insensitive); ambiguous values fail explicitly. This
reader flag is independent of every writer flag. Enabling it authorizes only
the read-only resolution and warning behavior in sections 6 and 10 and MUST
NOT create, repair, or amend a config or manifest. The reader remains off in
deployment defaults until WP11 records mixed-version and rollback evidence.

This default-off boundary was chosen so the exact reader can land and be tested
before any writer produces project-owned artifacts. Default-on activation or a
silent fallback for invalid flag values was rejected because either would
bypass the roadmap's deployed-fleet acceptance gate.

### 14.3 Phase 3: Forest test-production integration gate

The compatibility release MUST be deployed to the Forest test-production
server before production rollout. This is an integration gate, not an
observation-only deployment.

Forest acceptance MUST demonstrate:

1. the stack starts with canonical shared `_defaults.cfg` present;
2. shared `_defaults.toml` is a relative symlink resolving to that canonical
   file and an older-reader fixture can load through the symlink;
3. a representative legacy project without project-local defaults reopens and
   resolves the same effective values as before deployment;
4. a fixture/project containing only project-local `_defaults.toml` continues
   to prefer that file over shared `_defaults.cfg`;
5. a fixture/project containing project-local `_defaults.cfg` prefers it over
   both `.toml` locations;
6. a new named-preset project initializes with the same effective values as
   before the defaults-name change;
7. the representative project reopens after a stack restart; and
8. normal climate, soils, delineation, and WEPP preparation paths complete for
   the representative configurations.

Record the deployed revision, exact commands, project/config identifiers,
effective-value comparisons, and results in the implementation work package.
Do not record secrets or configuration files containing credentials.

Any changed effective value, failure to honor a project-local legacy defaults
file, malformed project-owned snapshot, or fallback after recognizing a
flattened config blocks promotion. Rollback MUST restore the prior application
revision while the shared `_defaults.toml` alias remains available to that
revision.

### 14.4 Phase 4: Production rollout and shared-alias removal

After Forest acceptance, deploy the compatibility reader and canonical
`_defaults.cfg` to production. The shared `_defaults.toml` symlink MUST remain
through Forest Phase 3, production validation, and the mixed-version deployment
window. Project-local `_defaults.toml` support is permanent for legacy archives
and projects.

The symlink avoids divergent shared contents but the legacy shared name is not
permanent. The shared `_defaults.toml` symlink MUST be removed after Forest and
production validation demonstrates that every deployed application revision
and supported rollback target reads canonical shared `_defaults.cfg`. The
removal MUST occur in the next planned release after that gate; it MUST NOT be
deferred as optional cleanup.

This removal applies only to the shared alias. The reader MUST permanently
retain support for project-local `_defaults.toml` in legacy projects and
archives, with the precedence defined in section 6.2.

### 14.5 Project-owned configuration rollout

After the defaults-name integration gate, continue in this order:

1. Deploy flattened-config detection to every web and RQ reader while
   preserving all legacy modes; keep all flattened-config writers disabled.
2. Verify every active worker and supported rollback revision can read a
   flattened fixture without applying shared defaults.
3. Complete the configuration sanitization gate in section 14.0.
4. Add deterministic resolution and snapshotting for newly created named-preset
   projects.
5. Add manifest generation and diagnostics.
6. Add resolved capability reading without restricting legacy projects.
7. Introduce one builder-supported configuration family.
8. Exercise flattened create, reopen, fork, archive, and restore on Forest
   test production before enabling project-owned configs in production.
9. Enable writer feature flags only after compatible readers are deployed and
   rollback to an incompatible reader is no longer a supported path.
10. Expand registered components and profiles incrementally.

There is no bulk backfill or general re-flattening. A shared config edit
continues to affect legacy projects. Flattened projects stay pinned except when
an authorized user previews and applies an additive update or eligible
acknowledged capability refresh through section 5.1.

### 14.6 WP12D locale authority and refresh rollout

WP12D MUST first commit and deploy a standalone reader floor containing the
append-only structural validator, with the capability-refresh writer absent and
existing additive behavior unchanged. Exact host `forest` MUST prove the reader
opens current schema-v3 identities, historical schema-v2, flattened
compatibility modes, and representative legacy configs before the refresh
writer is deployed.

The writer candidate may then expose refresh on `forest`, apply and reopen one
real provider/binary envelope refresh, and roll back to the recorded WP12D
reader floor. The refreshed config and manifest MUST remain readable and byte-
for-byte unchanged. Reader floor `187a856d4` is a rollback target only before
WP12D refresh exposure and MUST NOT be used after a refresh commits.

Before amendment `PC-24/WP12D-20260828-5`, WP12D had no distinct production
map-axis transition. A real structural map/capability addition requires its
actual prior/resulting identities, direct fixtures, a separately ratified
reader-first amendment, and Forest evidence before its writer is exposed.
WP12D may deploy only to exact
host `forest` without rebuilding the source-mounted development image. WP12
retains merge-to-master and every production action.

Amendment `PC-24/WP12D-20260828-5` is that first real structural transition.
It appends the resulting identities for all five schema-v3 locale graphs while
retaining every prior schema-v3 identity and the historical schema-v2 graph.
The exact prior-to-resulting identities are Continental US
`5296d3519d578164b6a5874a820991c935b394e5336aba41fe3e8f8d0dd4e29b` to
`3151e7e11be97967b32b887c6832b5286d252bf9b85841b889d5dcfbb24a8faf`,
Europe `c05b6a66f823f69cf8f1d44b69c206da1dc9449b278662c680248a3f3b755aeb`
to `18eda2d24f57be54993d2f0b609c59de6c26a17632d8653cc62b5a926e66f2c7`,
Canada `dd7f7cdb0d861a159df64a4806ee5585f0208b93982990e30974055b1f2a41e7`
to `07f733c2b13589ac637fc898859b8e3eac4902199606a2580796eec47765d7b4`,
Australia `bb4bdde8740d689aa378bcf744a942d997b9c69cdc445d80be07c749635efc9a`
to `1fd066a9e5bef26373414988d9f98e04fb84a8d0d08f7af280eef7cb1779a497`,
and Global Earth
`db1c185cf6b5def23064752847f585f3522c0b971460d9c688b424cb04c706ae`
to `b1bbcd60e71b65064455da3abaacdb239a433bafe08c46854a2ffcfc9c50de92`.
Its standalone reader floor MUST reopen every prior identity and recognize all
five resulting identities before Builder description/creation or capability-
refresh writers may emit them. Forest MUST then prove the exact Europe schema-
v1 preset projection and one resulting schema-v3 create or refresh, reopen,
and reader-floor rollback without changing run bytes. The exact identities and
first-reader revision are recorded append-only in the capability-structure
catalog and its direct fixtures.

## 15. Required Regression Evidence

Implementation is not conformant until tests demonstrate:

- flattened project configs load without shared defaults;
- differently ordered/formatted source chains that resolve to the same typed
  map produce identical canonical `.cfg` bytes, and serialization is stable
  across a parse/serialize round trip;
- registered writeover follows contributor order and records the effective
  writer, while undeclared writes fail validation;
- legacy project-local configs retain defaults-plus-local layering;
- projects without local configs retain shared fallback;
- project-local `_defaults.cfg` wins over all legacy/shared names;
- project-local `_defaults.toml` wins over both shared defaults names;
- shared `_defaults.cfg` falls back to shared `_defaults.toml` when required by
  the compatibility window;
- the compatibility `_defaults.toml` is a relative symlink to `_defaults.cfg`,
  works for an older reader, and remains present through Forest and production
  validation;
- serialized NoDb payloads retain the config token without embedding a defaults
  filename;
- named-preset query overrides are materialized into the flattened file;
- unknown named-preset query overrides are rejected only on the flattened
  writer path and transport/authentication values never enter the manifest;
- every supported named preset passes schema and capability-completeness
  validation before release;
- later edits to shared defaults, presets, or locale profiles do not change a
  flattened project's effective values;
- malformed flattened configs fail explicitly without shared fallback;
- a valid flattened config with a missing, malformed, or inconsistent manifest
  continues loading with a warning, does not use shared fallback, and disables
  configuration updates;
- a valid flattened config with a newer unknown manifest schema loads and can
  be restored with updates disabled, while manifest schema version 1 remains
  readable;
- the async availability check performs no write and previews all applicable
  missing attributes from the complete recorded parent chain;
- only an authenticated, explicit apply request enqueues an update;
- a stale preview is rejected without mutation and requires a refreshed
  preview;
- applying a current preview adds all reviewed missing attributes in one batch;
- the amendment preserves every existing config value;
- an ordinary missing `config_get_*` lookup performs no configuration write;
- an unregistered/misspelled attribute and an ambiguous or inapplicable chain
  result do not mutate either file;
- amendment history records source, value, revisions, and prior/resulting
  digests without secrets;
- config digest mismatch emits a warning without, by itself, blocking project
  loading, mutation, model execution, or a registered additive amendment;
- concurrent apply requests for the same parent-chain delta cannot bypass the
  project lock or produce duplicate amendments;
- failure before, during, and after either file replacement recovers to a
  consistent config/manifest pair without re-resolving a changed value;
- registering a new mod does not enable it or inject a section into an older
  project;
- an older project with an already-active mod may receive its newly introduced
  missing section/options through the merge-only build-chain amendment;
- preset projects and their forks retain the recorded defaults/preset/override
  parent chain, and updates never infer a replacement profile;
- builder combinations validate locale/DEM/cell-size/backend/representation/
  WEPP-binary/mod constraints;
- all continental-US DEM/backend/representation/binary combinations pass the
  Forest gate before they are exposed; this includes direct unmocked role
  resolution and representative execution for every provider-exposed binary, a
  representative WBT Multiple OFE preparation and run with `wepp_260803`, and a
  Single OFE run with each exposed binary;
- nested/PUP controllers without a child-local config resolve the validated
  top-level project config before shared fallback, while preexisting legacy
  child-local configs retain precedence;
- the Interfaces path remains present and retains its original config tokens;
- builder controls expose only server-described stable IDs and dependent
  choices;
- Builder description exposes exactly one complete graph for each approved
  locale, dependent controls switch to the selected graph, and server
  validation rejects every cross-locale dataset choice without creating a run;
- every locale offers Vanilla CLIGEN; Continental US exposes exactly Legacy,
  2015, and GHCN station databases while Europe, Canada, Australia, and Earth
  expose only GHCN; generated configs contain the selected exact `cligen_db`;
- Europe, Canada, Australia, and Global Earth generated configs contain their
  exact runtime locale/data-provider writes and data defaults; Canada uses the
  `canada` token, global terrain/soil/land-cover sources, offers observed
  Daymet, and defaults to Vanilla CLIGEN;
- historical Continental-US schema-v2 bytes validate and reopen unchanged;
  every WP12C project stores a complete schema-v3 graph, and stored validation
  for every profile remains independent of the live registry;
- each DEM supplies an allowed default cell size from
  `1, 2, 5, 10, 25, 30, 90, 100`;
- ordinary users see the derived cell size but cannot submit an override;
- PowerUser/Admin/Root users can select only the fixed override values;
- unauthorized, stale-role, and out-of-set override requests fail without
  project creation;
- the review and manifest distinguish DEM default, effective cell size, and
  privileged override source;
- invalidated downstream selections are removed from submitted payloads and
  explained to the user;
- the review summary matches the server-resolved config and capabilities;
- stale builder registry revisions fail with `stale_builder_schema` and create
  no project;
- duplicate submission is prevented while creation is pending;
- idempotent success replay returns the original project, conflicting replay
  returns `idempotency_key_conflict`, and failed initialization releases the
  reservation without publishing a ready project;
- builder validation errors preserve selections and focus/announce correctly;
- the complete builder path passes keyboard, 200-percent zoom, and automated
  accessibility checks;
- the `/config/` run route renders the locale pill and Config Summary dialog,
  while other config stems and test-only exposure flags do not; nested/PUP
  `/config/` requests use their active resolved context and authorization denial
  occurs before rendering;
- the run summary retains the exact six-row order and field mappings from
  section 7.8 across populated, absent, empty, supported legacy, and malformed
  states, never substitutes live graph defaults for missing stored selections,
  and escapes hostile display values;
- the Config Summary dialog passes semantic-table, accessible-name,
  keyboard/focus, active-theme, and narrow-reflow checks;
- capability filtering and server enforcement use the same resolved IDs;
- update preview/apply reject public read authority and require the project
  owner or `Admin`/`Root`, including worker-time reauthorization;
- fork/archive recover any pending update and preserve a consistent config and
  manifest pair;
- initialization does not begin after config persistence failure; and
- reader-only deployment is compatible with flattened fixtures before writer
  feature flags are enabled; and
- the sanitization gate rejects secret-bearing generated config or manifest
  content before it can enter a project root or archive.
- the closed locale/dataset/method/provider inventory fails on every omitted or
  undispositioned source value and validates every stable-ID/runtime mapping;
- profile validation rejects duplicate/casefold-colliding tokens, multiple
  bases, incompatible overlays, precedence collisions, cycles, and profiles
  whose support state lacks its required axes/evidence;
- capability v2 rejects missing, empty mandatory, malformed, orphan, duplicate,
  non-exhaustive, out-of-axis, invalid-default, invalid-tuple, and invalid-mod
  relations, while valid adjacency/default closure is byte-stable;
- capability v3 passes complete graphs for every exposed locale and rejects a
  missing/empty station-database axis or default plus every v2 hostile shape;
- absent, v1 partial, v1 optional-empty, v1 hostile, v2 complete, v2 partial,
  v2 hostile, v3 complete, v3 partial, v3 hostile, and newer capability schemas
  follow the section-9 state matrix;
- historical schema-v2 update availability/preview/apply uses its frozen v2
  parent chain and never adds a station-database selection or changes v2 bytes;
- description-schema-v2 clients create with locale-keyed schema-v3 members,
  while old clients may parse the frozen US compatibility members but receive
  `unsupported_builder_schema` before validation or creation mutation;
- every inventoried Builder/rq-engine/run-page discovery surface and paired
  mutation/build endpoint derives availability from the same stored graph and
  an invalid request causes neither NoDb mutation nor enqueue;
- every provider/dataset advertised by a `builder_exposed` profile has
  presence/health evidence bound to registry, provider, and deployment
  revisions, and every Builder-exposed base and overlay has Forest creation
  evidence;
- every distinct exposed provider/method family has representative unmocked
  execution evidence and invalid graph edges are exercised directly;
- baseline differential fixtures pass before legacy locale conditionals are
  removed; and
- a v3-capable reader deployment runs with schema-v3 writing disabled before
  WP12C creation begins and proves all five v3 fixtures plus historical v2;
  rollback to a schema-v2-only reader is allowed only while no v3 project
  exists, and after v3 creation every supported rollback revision must enforce
  v2 and v3 without broadening either graph or changing project bytes; and
- a direct concurrent Legacy/2015/GHCN resolver test uses real station metadata
  and proves every returned `StationMeta.parpath` stays under the selected
  database's owned PAR root;
- all 128 shipped named configs resolve through defaults to the exact canonical
  locale inventory, including US, Canada, Portland, RHEM, Turkey, and Tenerife;
- both Config Builder navigation links, every established Interfaces link/form,
  card order, and config token remain plain and unchanged, while only Builder's
  typed locale payload writes the selected flattened runtime token;
- stale persisted `Ron._locales` cannot override effective config; project-
  local `_defaults.cfg`/`_defaults.toml` chains cover absent, explicit-empty,
  valid, invalid, and historical explicit locale without rewriting a file; and
  locale-bearing legacy query/config-token overrides return exact HTTP 400
  `project_config_validation_failed` before publication/initialization;
- flattened no-capability and schema-v1 non-preset/invalid-manifest fixtures
  cover absent, empty, unknown, overlay, and non-Builder locale values with zero
  Builder-registry calls while preserving compatibility/error behavior;
- a valid schema-v1 named preset for each recognized base uses the current
  climate and land-cover projections only, and a Europe fixture advertises,
  renders, accepts, and enforces exactly Vanilla CLIGEN, E-OBS Modified
  (Europe), and User-Defined Climate;
- digest-mismatched-but-loadable, missing/unknown/inactive source-preset,
  filename-incongruent, parent-chain-incongruent, and shape-valid forged-preset
  schema-v1 manifests retain compatibility with zero registry calls and
  preserve existing reader warnings;
- a self-consistent project-local forgery with recomputed hashes fails byte-
  exact canonical rematerialization; parent-source drift, forged/non-allowlisted
  overrides, and rematerialized/stored locale mismatch also remain
  compatibility-only; malformed/unavailable preset policy instead returns the
  diagnostic 503 with no write, reservation, mutation, or enqueue;
- the exact five-profile climate matrix, numeric modes, per-dataset method
  relations, Vanilla defaults, and User-Defined upload requirements are
  fixture-locked;
- synthesized registry component equality and deterministic digest fixtures
  exhaust every newly Builder-exposed climate and land-cover ID;
- rq-engine Builder description fixtures expose the exact five graph envelopes,
  and a non-default land-cover create fixture changes runtime/default selection
  while persisting the complete locale graph;
- each Builder Land-cover selection changes only runtime/default state while
  the graph and run control retain the complete locale envelope, including the
  full US catalog and Canada C3S rather than US datasets;
- graph-authoritative upload-cli accepts only an advertised
  `user_defined_cli`, while stored graphs without it fail before multipart
  read/save, timestamp removal, reservation, or enqueue and no-graph
  compatibility retains established behavior;
- exact-candidate Forest evidence executes real, unmocked DEP NEXRAD, Future
  CMIP5, and User-Defined `.cli` upload/validation/build paths; validates every
  advertised year in the expanded US land-cover provider; and executes one
  real annual NLCD, NLCD Ever Forest, and eMapR vote fetch/build. Prior evidence
  may be reused only when registry, provider, and deployment revisions exactly
  match the candidate;
- Turkey's exact `WP12D-1` supported-non-Builder profile serialization and
  closed empty axes are fixture-locked, and `yasin.cfg` reopens with its fixed
  map inputs and landuse change disabled without a synthesized Builder graph;
- legacy shared and project-local runs for all five recognized base tokens use
  the same live locale-to-graph resolver as Builder description/creation, while
  flattened schema-v2/schema-v3 stored authority remains registry-independent;
- flattened no-capability/schema-v1 states outside the exact preset exception,
  non-Builder, overlay, Turkey, RHEM, and explicit old Canada/Earth fixtures
  retain contracted compatibility behavior without run-file rewriting;
- run-page controls, Flask routes, rq-engine schema/default/error documents,
  operation documents, pipeline, readiness, and paired mutation/build routes
  advertise and enforce the same landuse, soil, and climate authority;
- invalid locale and unavailable-registry fixtures directly exercise HTML,
  Flask JSON, and rq-engine JSON 409/503 transports, diagnostic
  `details`/`error_id`, `Retry-After: 5`, auth precedence, and absence of a
  partially rendered interactive run page;
- direct unsupported selections fail before NoDb mutation, timestamp removal,
  file write, or enqueue, while an unchanged exact-current build succeeds;
- capability refresh is unavailable for schema-v2, preset-source schema-v3,
  locale/profile/selection mismatches, and removed/incompatible preserved
  selections, with diagnostic stable IDs and no substitution;
- additive-only, capability-only, and combined preview/apply cover exact
  update-kind, acknowledgment, JSON/null/sort/hash, stale, and payload-shape
  contracts for browser and direct clients;
- refresh preserves a non-Builder-default selection such as Daymet, every
  primary default, mods, and `climate.cligen_db`, and records one complete
  reversible amendment without changing creation provenance or personal data;
- direct real-filesystem tests parse the exact capability/combined manifest
  layout; reject oversized config, manifest, journal, and archive-member
  candidates before reservation without truncation; and exercise valid writes
  plus faults on both sides of the config-replacement commit point;
- current production structure identities validate, `280cf7e84` and current
  share the same identities, a test-only genuine two-identity transition proves
  append-only evolution, and unknown self-consistent identities fail closed;
- faults before/after config replacement prove prior-pair retention and result-
  pair roll-forward; availability/UI reconcile terminal state; historical
  amendment inference and latest-preview idempotent HTTP/RQ retry append no
  duplicate amendment; and
- exact-host Forest acceptance proves legacy/stored reopen, a real
  provider/binary refresh, and rollback to the recorded WP12D reader floor
  without image rebuild or production action.

At least one representative project MUST be exercised through create, reopen,
fork, archive, and restore before production rollout.

## 16. Approval and Evidence Gates

The review cycle identified no remaining version 1 behavior decisions. WP00R
approved this contract for implementation on the noncanonical initiative
branch. Runtime activation and promotion remain blocked until:

1. the sanitization work package inventories the existing lexical forms and
   ratifies the type-specific canonical value encodings required by section
   8.1;
2. each implementation package imports and closes its entries from the WP00R
   [normative requirement checklist](../work-packages/20260804_project_config_contract_ratification/artifacts/normative_requirement_checklist.md);
   and
3. implementation records the required local and Forest evidence before
   enabling writer feature flags or exposing a builder combination.

Implementation sequencing, requirement ownership, cross-package leakage, and
handoff evidence are defined in the companion
[`Project-Owned Configuration Implementation Roadmap`](project-owned-config-implementation-roadmap.md).

For non-provider components, an evidence failure removes or delays the affected
builder combination. Failure of any provider-supplied WEPP binary invalidates
Builder binary availability as a whole until the provider or deployment is
corrected. Neither case authorizes an inferred fallback or a change to
Interfaces presets.
