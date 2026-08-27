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
- Dynamically recomposing locale or component fragments whenever an existing
  project is opened.
- Removing shared named configs or their legacy fallback path.
- Standardizing how preexisting persisted capability selections affect UI
  visibility, rebuild eligibility, or model routing.

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
the run-page header MUST show a notice linking to an accessible modal panel.
The panel MUST list every section, option, value, owning parent-chain source,
and source revision that the merge would add. It MUST provide an explicit
button to request the update and MUST explain that version 1 only adds missing
attributes.

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

Overwrite and removal updates are reserved for a future contract. The version
1 endpoint, preview, and job MUST reject them.

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

### 6.3 Shared fallback mode

When no project-local config exists, the loader MUST retain current behavior:

1. load shared `_defaults.cfg`, falling back to shared `_defaults.toml` during
   the compatibility period;
2. load the named shared preset; and
3. apply supported config-token query overrides.

Missing or malformed shared files retain their existing explicit failure
behavior. The new resolver MUST NOT mask those failures.

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
| WEPP binary | `wepp_dcc52a6`: legacy-parity binary for Single OFE; `wepp_260803`: default Builder binary, available for Single or Multiple OFE |
| Soils | `ssurgo-gnatsgso-2025`: `soils_db = "ssurgo/gNATSGSO/2025"`, existing gridded mode |
| Land use | `nlcd-2019`: `landuse_db = "nlcd/2019"`, existing gridded mode and general mapping |
| Climate | `vanilla_cligen`; `prism_stochastic`; `observed_daymet`; `observed_gridmet` |
| Mods | none |

The ten supported tuples are the cross-product of two DEMs with: TOPAZ, Single
OFE, and either binary (four tuples); WBT, Single OFE, and either binary (four
tuples); and WBT, Multiple OFE, and `wepp_260803` (two tuples). They are eligible
only after all ten pass the Forest create/reopen/delineate/build gate and the
execution evidence in section 15. Dataset and binary identifiers MUST be
verified against deployed services, mounts, and executable pairs at that gate.
Failure removes the affected tuple from the initial registry rather than
causing an inferred substitution.

Builder V1 defaults to `wbt`, `single-ofe`, and `wepp_260803`. The WBT-only
Multiple OFE rule is a conservative Builder eligibility policy, not a statement
that legacy TOPAZ MOFE presets are technically invalid. Those existing presets
remain unchanged. The Builder MUST NOT infer defaults from lexical component
ordering.

TauDEM, alternate soil/land-use modes, event/upload/future climate modes,
and optional NoDb mods are deferred from the initial matrix. They require
separate registered definitions and representative validation before becoming
builder-visible. This does not remove or change any Interfaces preset that
already uses them. Later mod IDs SHOULD retain the exact stable tokens accepted
by `[nodb] mods`; filesystem discovery alone MUST NOT register a mod.

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
  project; registered missing attributes may be added through the explicit
  update flow described in section 5.1.
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
   selected representation; and
7. optional mods when at least one is registered for the resolved combination.

Labels MUST be human-readable while submitted values use stable registered
component IDs. Technical details such as dataset keys MAY be shown as secondary
help but MUST NOT replace understandable labels.

#### Dependency behavior

- The server-provided builder schema and validation response are authoritative
  for available values, defaults, requirements, and conflicts.
- Selecting a locale MUST limit DEM, cell-size, capability, and mod choices to
  those supported by that locale.
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
- soil-building methods that will be available;
- land-cover choices when more than one is relevant; and
- initialized mods and material limitations introduced by the combination.

Derived capabilities are explanatory in version 1 unless the component schema
explicitly declares them user-selectable. The client MUST NOT independently
invent or broaden capability lists.

#### Validation and review

- Validation MUST run against the complete proposed combination, not only each
  field in isolation.
- Field errors MUST be associated with their controls and a page-level summary
  MUST link or move focus to each invalid field.
- The Create action MUST remain unavailable while required selections are
  missing, validation is pending, or the server reports an invalid
  combination.
- Before creation, the UI MUST present a review summary containing the locale,
  DEM, cell size, backend, representation, WEPP binary version, mods, and
  derived capabilities.
- The review MUST state that the generated runtime filename is `config.cfg` and
  that the complete selections and provenance will be recorded in
  `config-manifest.json`.
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
- Focus MUST move to the error summary after failed validation and to a clear
  creation-status target after submission.
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
equivalent). They are source definitions for the builder and resolver; they are
not runtime NoDb configuration files. The generated, flattened project-owned
configuration remains INI-style `.cfg` as defined in section 5.

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

## 9. Capability Contract

The resolved config MUST record stable semantic identifiers rather than UI
labels or raw enum values. An illustrative section is:

```ini
[capabilities]
climate_datasets = ["vanilla_cligen", "prism_stochastic", "observed_gridmet"]
soil_builders = ["gridded", "single_mukey", "single_database"]
landuse_datasets = ["nlcd-2021"]
```

Climate capabilities MUST use climate catalog IDs, not numeric
`ClimateMode` values. Soil capabilities MUST introduce stable IDs rather than
using `SoilsMode` integers because existing enum values include aliases.

For flattened projects:

- UI option lists MUST be derived from the resolved capability section.
- Server mutation/build endpoints MUST validate new selections against the same
  resolved capability section.
- A hidden UI option MUST NOT remain invokable as an unsupported backend
  selection.

Version 1 intentionally makes no contract for how a capability selection that
was persisted before this contract influences current-state visibility,
rebuild eligibility, or model routing. Those paths use several established
mechanisms, and normalizing them in this package would create disproportionate
regression risk. Implementations MUST preserve their existing behavior unless
a separately scoped and ratified contract changes it. The requirements above
govern newly presented and newly submitted selections only; they MUST NOT be
used as authority to refactor or reject a preexisting persisted selection.

Legacy projects without resolved capabilities MUST retain their current locale,
mod, catalog, and route behavior.

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

Amendment history is append-only. It MUST NOT contain credentials or bearer
tokens.

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

An additive amendment MUST use one project-scoped config amendment lock. Both
candidate files MUST be written and fsynced before replacement. Because two
filesystem paths cannot be replaced by one POSIX rename, the implementation
MUST use a small pending-amendment journal containing the expected prior and
resulting hashes. It then replaces the config, replaces the manifest, and
removes the journal. A later reader MUST complete or roll back an interrupted
transaction deterministically before serving configuration.

Failure before commit leaves the prior config and manifest authoritative.
Failure or process death between replacements MUST be recoverable from the
journal without importing a newly changed build-chain value. Concurrent misses
covered by the same resolved build-chain delta MUST produce at most one batch
amendment entry.

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
read-only/public project restrictions. Service/session/MCP principals may
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
canonical `202` with `job_id`.

The UI contract depends on these stable error codes:

- `validation_error` (`400`) with field-addressable details;
- `forbidden` (`403`);
- `not_found` (`404`);
- `idempotency_key_conflict` (`409`);
- `creation_in_progress` (`409`);
- `stale_builder_schema` (`409`);
- `stale_config_preview` (`409`);
- `config_update_unavailable` (`409`);
- `config_update_in_progress` (`409`); and
- `unsupported_config_schema` (`409`).

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
an authorized user previews and applies a merge-only update through the process
in section 5.1.

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
- all initial continental-US DEM/backend/representation/binary combinations
  pass the Forest gate before they are exposed; this includes direct unmocked
  presence and execution checks for both watershed/hillslope binary pairs, a
  representative WBT Multiple OFE preparation and run with `wepp_260803`, and a
  Single OFE run with each exposed binary;
- nested/PUP controllers without a child-local config resolve the validated
  top-level project config before shared fallback, while preexisting legacy
  child-local configs retain precedence;
- the Interfaces path remains present and retains its original config tokens;
- builder controls expose only server-described stable IDs and dependent
  choices;
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

An evidence failure removes or delays the affected builder combination; it does
not authorize an inferred fallback or a change to Interfaces presets.
