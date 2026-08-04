# Project-Owned Configuration Contract (Draft)

> **Status:** Draft for operator review; non-canonical and not approved for
> implementation.
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
  `_defaults.toml` alias contains the same INI-style content. Despite its old
  suffix, `_defaults.toml` is parsed by `RawConfigParser`; it is not TOML.
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

The project-owned config MUST contain every effective runtime option from all
applicable sections. It MUST NOT require shared defaults, locale fragments, or
builder component files to supply an omitted runtime value.

The project-owned config MUST retain the resolved `[general] locales` value for
provenance and existing locale-aware runtime behavior. Runtime capability
availability, however, MUST come from the resolved project config rather than
from recomposing the current shared locale profile.

The project-owned config is application-managed infrastructure after project
initialization. Ordinary controls MUST persist user/project state in their
existing NoDb stores rather than editing the config. The only version 1
post-creation edit is the registered additive amendment process below.

### 5.1 Additive configuration evolution

Flattened configs use lazy, additive amendments when software requests a
registered configuration attribute that did not exist when the project was
created. This is not a bulk migration framework and does not re-flatten the
project against all current shared configuration.

When a `config_get_*` lookup cannot find `(section, option)` in a flattened
project config, that first registered miss triggers one merge-only
reconciliation of the complete recorded build chain. The resolver MUST:

1. determine whether the exact attribute is registered as amendable;
2. reconstruct the project's config build chain from the immutable selections
   and source identity in `config-manifest.json`;
3. resolve the complete current attribute set for that recorded chain using its
   declared precedence;
4. verify that every contributing component/mod is active for the project;
5. acquire the project config amendment lock and re-read both files;
6. calculate the set difference and add every applicable registered attribute
   that remains absent, including newly introduced sections;
7. validate the complete merged result;
8. atomically replace the project-owned config; and
9. append one batch amendment record and the new digest to the manifest as one
   crash-recoverable logical transaction.

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

The build-chain resolution may use component definitions introduced after
project creation, but the amendment makes that fall-forward explicit and
durable. Once written, later component/default changes MUST NOT alter the
amended value. An additive amendment does not increment the config schema
version.

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
5. write the flattened project-owned config and manifest atomically; and
6. initialize Ron and all other NoDb controllers only after both files are
   durable.

The new project MUST NOT depend on later reads of the shared preset or shared
defaults.

### 7.2 Builder creation

The builder MUST accept typed, allowlisted selections rather than arbitrary
configuration keys. Its initial component model SHOULD cover:

- locale/profile, such as `continental-us`;
- locale-supported DEM source and resolution, with an associated default cell
  size;
- an authorized cell-size override from the closed set defined in section 7.5;
- delineation backend, initially TOPAZ or WBT;
- watershed representation, initially conventional/single-OFE or MOFE;
- additional mods to initialize; and
- resolved climate, soil, land-cover, and related capability profiles.

The builder MUST validate the complete combination before creating the project.
It MUST reject incompatible selections with a field-addressable explanation and
MUST NOT silently substitute a different locale, DEM, cell size, backend,
representation, capability, or mod.

Component sources are creation-time inputs. They MUST NOT become runtime
dependencies of the generated project.

### 7.3 Builder config naming

Builder-created projects MUST use the reserved config token `config` and the
fixed project-owned filename `config.cfg`.

The builder MUST NOT derive the filename or route token from selected locale,
DEM, cell size, backend, representation, mods, a user-supplied project name, or
the config digest. Those values may change in vocabulary or presentation while
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
  existing Interfaces path.
- The builder MUST explain that it creates a project-owned `config.cfg` that
  users do not edit. Changing builder selections later requires creating a new
  project; registered missing attributes may be amended internally as described
  in section 5.1.
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
5. watershed representation, initially conventional/single-OFE or MOFE; and
6. optional mods available for the resolved combination.

Labels MUST be human-readable while submitted values use stable registered
component IDs. Technical details such as dataset keys MAY be shown as secondary
help but MUST NOT replace understandable labels.

#### Dependency behavior

- The server-provided builder schema and validation response are authoritative
  for available values, defaults, requirements, and conflicts.
- Selecting a locale MUST limit DEM, cell-size, capability, and mod choices to
  those supported by that locale.
- Selecting a DEM MUST set and display that DEM's associated default cell size.
- Backend, representation, and mod choices MUST update dependent availability
  when their registered constraints require it.
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
  DEM, cell size, backend, representation, mods, and derived capabilities.
- The review MUST state that the generated runtime filename is `config.cfg` and
  that the complete selections and provenance will be recorded in
  `config-manifest.json`.
- Advanced raw `.cfg` editing or arbitrary key/value injection is prohibited.

#### Submission and completion

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
- Retry behavior MUST not silently create multiple projects from one successful
  request. The exact idempotency mechanism remains an implementation decision.

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

## 8. Composition and Precedence

Composition MUST be deterministic and schema-driven. The conceptual order is:

1. shared defaults;
2. locale/profile attributes;
3. terrain and DEM component;
4. delineation backend component;
5. watershed representation component;
6. selected mod components;
7. capability profile; and
8. explicit builder selections or supported named-preset overrides.

This order does not grant arbitrary last-write-wins behavior. Each option MUST
have an owning component or an explicitly declared override relationship.
Conflicting assignments without such a relationship MUST fail validation.

The resolver MUST produce the same canonical `.cfg` bytes for the same schema,
component versions, and selections, excluding fields explicitly documented as
non-deterministic. Timestamps belong in the manifest, not the `.cfg`.

### 8.1 Component registry format and ownership

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
    capabilities/
    mods/
```

Each TOML document MUST declare a stable component ID, schema version, source
revision identity, owned configuration attributes, constraints, and any
references to other registered component or capability IDs. The typed Python
registry MUST validate every document before exposing it to the builder or
resolver. Invalid IDs, unknown references, duplicate ownership, malformed
values, or contradictory constraints MUST fail explicitly; they MUST NOT be
ignored or repaired through implicit defaults.

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
- climate, soils, and land-cover maintainers own their capability catalogs; and
- each NoDb mod owner owns that mod's component definition and constraints.

Locale profiles compose allowed component and capability IDs and locale-level
constraints. They MUST NOT duplicate the runtime settings owned by the
referenced DEM, backend, representation, capability, or mod components. Shared
named `.cfg` presets remain owned by the existing Interfaces creation path and
are not converted into registry profiles merely to support the builder.

Component IDs are durable provenance identifiers and MUST NOT be renamed or
reused with incompatible semantics. A materially incompatible meaning requires
a new ID, such as `continental-us-v2`. Compatible additions may retain the ID
with an incremented source/schema revision and are eligible for the merge-only
amendment rules in section 5.1. The manifest MUST record the exact IDs and
revisions used to resolve the project so the build chain can be reconstructed
without treating current registry contents as the project's original values.

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

`config-manifest.json` MUST be UTF-8 JSON and SHOULD contain:

```json
{
  "schema_version": 1,
  "resolver_version": 1,
  "source_kind": "builder",
  "source_preset": null,
  "source_revision": "<git revision>",
  "resolved_at": "<RFC 3339 UTC timestamp>",
  "selections": {
    "locale": "continental-us",
    "dem": "usgs-3dep-10m",
    "dem_default_cellsize": 10,
    "cellsize": 10,
    "cellsize_source": "dem_default",
    "delineation_backend": "wbt",
    "watershed_representation": "mofe",
    "mods": ["disturbed"]
  },
  "config": {
    "filename": "<config>.cfg",
    "sha256": "<lowercase SHA-256>"
  },
  "amendments": []
}
```

Named-preset creation MUST set `source_kind` to `preset` and record the preset
name. The manifest MUST NOT contain secrets, bearer tokens, query credentials,
or environment dumps.

In schema version 1, the digest is provenance evidence. A digest mismatch MUST
produce an explicit operator-visible warning, but the mismatch alone MUST NOT
block project loading, ordinary mutation, model execution, or a registered
additive amendment. It MUST NOT automatically delete, rewrite, or repair
project data. Normal parsing, validation, authorization, and downstream model
errors remain enforceable. This warning-only policy avoids bricking an
otherwise usable project; the operation may succeed, or an actionable failure
may surface at the subsystem that cannot use the changed configuration.

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
controller initialization. Creation MUST use temporary files in the target
working directory followed by atomic replacement.

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

A fork MUST retain the source project's resolved config and manifest by default.
Changing configuration during fork is a separate future contract and MUST NOT
be inferred from the existence of the builder.

Restore MUST use the restored project-owned config when present. Restoring a
legacy archive without one MUST retain shared fallback behavior.

Read-only/public state MUST not change configuration resolution or permit user
config mutation. A registered internal additive amendment may still occur so a
project can be opened by newer software; it remains subject to the same lock,
journal, and provenance requirements.

## 13. Security Boundary

The builder MUST resolve only registered component IDs and allowlisted values.
It MUST NOT accept arbitrary filesystem paths, configuration section names,
option names, Python literals, environment-variable references, or executable
content from browser input.

The resolver MUST validate configured paths against the existing owned data
roots and config path conventions. Generated files MUST not contain secrets.
Project authorization for creation, read, fork, archive, and restore remains
unchanged.

Cell-size override authorization is an additional builder-specific privilege.
Possession of ordinary project-creation authority does not grant it. The server
MUST enforce `PowerUser`/`Admin`/`Root` authorization at submission and audit a
successful non-default override.

## 14. Compatibility and Rollout

### 14.1 Phase 1: Dual-name compatibility

Add `_defaults.cfg` as the canonical shared defaults file while retaining a
byte-equivalent `_defaults.toml`. Update the central resolver and direct
consumers to use the project-local and shared precedence in section 6.2.

All deployed versions MUST continue to operate during this phase. A bare rename
without the compatibility reader is prohibited.

### 14.2 Phase 2: Local automated validation

Complete the defaults-name regression matrix and project-owned config tests in
section 15. Confirm that serialized `.nodb` files retain their config token but
do not embed either defaults filename. Validate new project creation, legacy
project reopen, fork, archive, and restore locally.

### 14.3 Phase 3: Forest test-production integration gate

The compatibility release MUST be deployed to the Forest test-production
server before production rollout. This is an integration gate, not an
observation-only deployment.

Forest acceptance MUST demonstrate:

1. the stack starts with canonical shared `_defaults.cfg` present;
2. a representative legacy project without project-local defaults reopens and
   resolves the same effective values as before deployment;
3. a fixture/project containing only project-local `_defaults.toml` continues
   to prefer that file over shared `_defaults.cfg`;
4. a fixture/project containing project-local `_defaults.cfg` prefers it over
   both `.toml` locations;
5. a new named-preset project initializes with the same effective values as
   before the defaults-name change;
6. the representative project reopens after a stack restart; and
7. normal climate, soils, delineation, and WEPP preparation paths complete for
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
`_defaults.cfg` to production. The shared `_defaults.toml` MUST remain through
the mixed-version deployment window. Project-local `_defaults.toml` support is
permanent for legacy archives and projects.

Maintaining two shared defaults files is an error trap and is not a permanent
compatibility strategy. The shared `_defaults.toml` alias MUST be removed after
Forest and production validation demonstrates that every deployed application
revision and supported rollback target reads canonical shared `_defaults.cfg`.
The removal MUST occur in the next planned release after that gate; it MUST NOT
be deferred as optional cleanup.

This removal applies only to the shared alias. The reader MUST permanently
retain support for project-local `_defaults.toml` in legacy projects and
archives, with the precedence defined in section 6.2.

### 14.5 Project-owned configuration rollout

After the defaults-name integration gate, continue in this order:

1. Add flattened-config detection while preserving all legacy modes.
2. Add deterministic resolution and snapshotting for newly created named-preset
   projects.
3. Add manifest generation and diagnostics.
4. Add resolved capability reading without restricting legacy projects.
5. Introduce one builder-supported configuration family.
6. Exercise flattened create, reopen, fork, archive, and restore on Forest
   test production before enabling project-owned configs in production.
7. Expand registered components and profiles incrementally.

There is no bulk backfill or general re-flattening. A shared config edit
continues to affect legacy projects. Flattened projects stay pinned except when
an accessed, registered missing attribute is resolved and durably recorded by
the additive amendment process in section 5.1.

## 15. Required Regression Evidence

Implementation is not conformant until tests demonstrate:

- flattened project configs load without shared defaults;
- legacy project-local configs retain defaults-plus-local layering;
- projects without local configs retain shared fallback;
- project-local `_defaults.cfg` wins over all legacy/shared names;
- project-local `_defaults.toml` wins over both shared defaults names;
- shared `_defaults.cfg` falls back to shared `_defaults.toml` when required by
  the compatibility window;
- serialized NoDb payloads retain the config token without embedding a defaults
  filename;
- named-preset query overrides are materialized into the flattened file;
- later edits to shared defaults, presets, or locale profiles do not change a
  flattened project's effective values;
- malformed flattened configs fail explicitly without shared fallback;
- the first registered missing attribute resolves the complete recorded build
  chain and adds all applicable missing attributes in one batch;
- the amendment preserves every existing config value;
- a second lookup for any attribute included in that batch performs no write;
- an unregistered/misspelled attribute and an ambiguous or inapplicable chain
  result do not mutate either file;
- amendment history records source, value, revisions, and prior/resulting
  digests without secrets;
- config digest mismatch emits a warning without, by itself, blocking project
  loading, mutation, model execution, or a registered additive amendment;
- concurrent lookups for missing attributes in the same build-chain delta
  produce one batch amendment;
- failure before, during, and after either file replacement recovers to a
  consistent config/manifest pair without re-resolving a changed value;
- registering a new mod does not enable it or inject a section into an older
  project;
- an older project with an already-active mod may receive its newly introduced
  missing section/options through the merge-only build-chain amendment;
- builder combinations validate locale/DEM/cell-size/backend/representation/mod
  constraints;
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
- duplicate submission is prevented while creation is pending;
- builder validation errors preserve selections and focus/announce correctly;
- the complete builder path passes keyboard, 200-percent zoom, and automated
  accessibility checks;
- capability filtering and server enforcement use the same resolved IDs;
- fork/archive/restore preserve config and manifest bytes;
- initialization does not begin after config persistence failure; and
- generated config and manifest contain no secrets.

At least one representative project MUST be exercised through create, reopen,
fork, archive, and restore before production rollout.

## 16. Open Decisions Requiring Ratification

The following remain intentionally unresolved in this draft:

1. The exact stable IDs and initial matrices for soil, land-use, DEM, watershed
   representation, and mods.
2. The behavior of nested project/PUP working directories that need a distinct
   configuration authority.
3. The exact creation-request idempotency mechanism and retry window.

No implementation should begin until these decisions are resolved through the
applicable contract-first work-package checkpoint.
