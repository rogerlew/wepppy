# WP12D Contract Decision

**Amendment ID**: `PC-24/WP12D-20260827-3`
**Status**: ratified; canonical checkpoint `596ff5758`
**Scope audit amendment**: `PC-24/WP12D-20260828-4`, ratified 2026-08-28
**Starting revision**: `5e04e0da9a23dd676e171f1857e14fa38cc9dfbe`
**Starting upstream revision**: `origin/feature/project-owned-config` at the
same revision
**Canonical merge base**: `origin/master` at
`6af9ecdd63921189804c5e292114a97253914cbb`
Initiative branch: feature/project-owned-config
Canonical branch: master
Promotion policy: merge only at the roadmap promotion gate
**Promotion boundary**: exact host `forest` only; WP12 owns `master` and
production

## Operator Correction and Supersession

The operator corrected the authority design: selected locale belongs in the
effective `.cfg`, not in an Interfaces URL. Legacy runs without a flattened
project-owned config must reopen with the correct localized landuse, soils, and
climate controls.

This proposal replaces the unratified `PC-24/WP12D-20260827-2` draft in place;
amendments 1 and 2 remain chronology only. No implementation or checkpoint was
created from either draft. Locale query filtering and config-registry
`locale_profile` metadata remain withdrawn.

## Applicable Canonical Contracts and Owners

This bounded cross-owner enhancement composes, without advancing or closing,
the project-owned-config locale/authority owner, the shared Pure controller
presentation/submission owner, the RQ controller-state discovery owner, and
the feature-registry navigation owner. The applicable canonical set is:

- `docs/schemas/project-owned-config-contract.md`;
- `docs/schemas/project-owned-config-implementation-roadmap.md`;
- `docs/ui-docs/controller-contract.md`;
- `docs/schemas/rq-controller-state-contract.md`;
- `docs/schemas/rq-engine-agent-api-contract.md`;
- `docs/schemas/rq-response-contract.md`, whose generic envelope remains
  unchanged;
- `wepppy/weppcloud/feature_registry/specification.md`; and
- `docs/adrs/ADR-0047-project-config-locale-authority.md`.

## Exact Authority Model

The run has one of four authority modes. Stored project-config classification
always occurs before any new legacy locale validation:

1. A flattened schema-v2/v3 Builder project uses only its validated stored
   capability graph. Neither a shared `.cfg` nor the current Builder registry
   silently changes its options. This applies to every valid schema-v2/v3 graph
   regardless of manifest `source_kind`, not only Builder provenance. An
   authorized end user may explicitly replace current schema-v3 stored
   authority through the reviewed capability-refresh amendment defined below.
2. A flattened project-owned config with no capability section, or a schema-v1
   project-owned snapshot, preserves its canonical compatibility behavior.
   WP12D does not consult the live Builder registry or newly validate
   `general.locales` for this mode. An absent, empty, or unknown locale
   therefore does not create a new WP12D error; present valid schema-v1 axes
   continue to restrict behavior, while malformed present v1 axes retain their
   existing explicit configuration error.
3. A legacy run without a flattened project-owned config reads its effective
   `[general] locales` from shared defaults plus its named or project-local
   `.cfg`. When that composition is exactly one Builder-exposed base profile
   with no overlay, the current server-side Builder registry graph for that
   profile is the landuse, soil, and climate presentation/submission authority.
4. A legacy run whose effective `.cfg` selects a supported non-Builder base,
   an overlay composition, or the RHEM family preserves its current
   locale-aware catalog behavior. WP12D does not synthesize a partial Builder
   graph for those modes.

The stored-authority reader `capability_authority()` remains stored-only. A new
explicit run-authority resolver composes the stored reader with legacy `.cfg`
locale resolution. This preserves WP12C's accepted reader boundary and makes
live-registry use visible rather than hiding it in a fallback.

### Append-only structural authority

Schema-v3 stored graphs must remain valid after the current locale profile
adds a map or relationship. `CapabilityGraph.validate()` therefore separates
closed schema/referential validation from profile-structure authorization. It
computes a deterministic `structure_sha256` and requires it to appear in an
append-only allowlist for the graph's one Builder locale. The allowlist begins
with the one production structure per locale first shipped by `280cf7e84` and
retained by the current revision; `9fd8b556b` tightened its validation but did
not create a distinct structure. Entries are never redefined or removed.

The accepted-structure catalog retains each canonical structural payload as
well as its hash. Closed stable-ID vocabularies are the union of all accepted
payloads, so an ID removed from the current profile remains valid in a frozen
historical graph. Canonical dataset/runtime catalog entries referenced by an
accepted structure are likewise retirement-only, not deletable; removing their
runtime mapping requires a separately ratified compatibility plan. This keeps
append-only structural validation from being defeated by a current-only known-
ID table or missing exact-current resolver.

The structural payload contains the locale ID; every non-runtime capability
axis; all climate, landuse, soil, mod, and representation relationships; and
all per-dataset method defaults. It excludes `capability_defaults`,
`provider_revision`, `wepp_binaries`, `wepp_binary_revisions`, and the binary
member of model tuples. Model tuples are represented instead as the sorted
unique allowed `(delineation_backend, watershed_representation)` pairs, while
normal graph validation still requires every stored binary tuple and revision
to be internally valid. Canonical sorted-key compact JSON encoded as UTF-8 is
hashed with SHA-256.

Any future structural profile change must append the new identity, retain all
old identities, deploy that reader before its refresh writer, and prove it
opens every stored identity before capability refresh can be exposed. The
current live Builder resolver must itself produce an allowlisted current
identity. Unknown structural identities fail explicitly; the reader never
accepts arbitrary self-consistent capability injection.

WP12D does not claim that a production map-axis transition exists today.
Unit tests use a test-only two-identity same-locale catalog with a genuine
axis/relation/per-dataset-default difference to prove old/new validation and
refresh mechanics; those test identities are not accepted in production. The
first real map/capability structure change must add its actual old/new
production identities, direct fixtures, reader-floor evidence, and Forest
acceptance under a separately ratified amendment before its refresh writer is
exposed. Current Forest refresh evidence may exercise a real provider/binary
envelope delta but cannot stand in for that future structural-change gate.

## Interfaces and Config Builder Navigation

Both Config Builder links remain plain `/interfaces/` links. `/interfaces/`
does not gain a locale query, filtering mode, card remapping, or no-match state.
Every existing card, role filter, form action, config token, and order remains
unchanged. The selected Interface's effective `.cfg` establishes its locale
after creation; established-Interface links and forms never submit or store
locale separately.

The WEPPcloud config registry does not gain `locale_profile`. It continues to
own visibility, maturity, role, and backend metadata only. Labels, filenames,
and established-Interface links cannot supply or override locale authority.
The Config Builder's existing create payload still carries its selected
Builder locale ID so the server can validate the request and write the runtime
token to `[general] locales`; that creation-time selector is not legacy run
authority.

## Effective `.cfg` Locale Contract

`[general] locales` is a closed ordered list of canonical runtime locale
tokens. Shared `_defaults.cfg` supplies `["us"]` for historical US configs that
omit the option. Specialized configs override it. Builder creation already
writes the selected profile's runtime token into its flattened `config.cfg` and
continues to do so.

The following checked-in normalization is exact:

- add `locales = ["us"]` to `_defaults.cfg`;
- add explicit `locales = ["us"]` to the current established presets
  `0.cfg`, `13.cfg`, `baer.cfg`, `reveg.cfg`, `reveg-mofe.cfg`, and
  `reveg-10m-mofe.cfg`, and to `general.cfg`; the latter's `name = "seattle"`
  is stale display metadata, while its data/map contract is Continental US;
- change `canada.cfg`, `canada-wbt.cfg`, and `canada-wbt-mofe.cfg` from
  `["earth"]` to `["canada"]` without changing their global DEM, ISRIC,
  C3S, GHCN, or other provider values;
- add `["us", "portland"]` to `portland-10-mofe.cfg`,
  `portland-disturbed.cfg`, `portland-disturbed9003.cfg`,
  `portland-disturbed-simfire-eagle.cfg`, and
  `portland-disturbed-simfire-norse.cfg`;
- add `["rhem"]` to `rhem_rap.cfg`; and
- add `["turkey"]` to `yasin.cfg` and add this exact canonical profile record:
  stable ID `turkey`, label `Turkey`, runtime token `turkey`, classification
  `base`, support state `supported_non_builder`, source revision `WP12D-1`, no
  base/overlay metadata, and empty closed DEM, soil, landuse, climate, and
  climate-station-database axes. Yasin's fixed Turkey DEM, land-cover, and soil
  map paths remain config-owned inputs outside Builder dataset authorization;
  `enable_landuse_change = false` remains unchanged. No new dataset stable ID
  or catalog entry is added, and no Builder graph is synthesized; and
- normalize `tenerife-disturbed.cfg` and `tenerife-5m-disturbed.cfg` to
  canonical base-first order `["eu", "tenerife"]`.

Every other checked-in explicit locale declaration remains unchanged. Every
shipped config must resolve after defaults to a nonempty canonical composition;
the row-level regression inventory in `20260827_config_locale_inventory.md`
covers all 128 named `.cfg` files, not only the Interfaces registry.

For legacy project-local resolution, an absent `general.locales` after the
project-local defaults/config chain receives the non-persisting compatibility
value `["us"]`. An explicitly empty or invalid value fails. An explicit local
value remains authoritative: an old project-local Canada copy that says
`["earth"]` remains Global Earth and is not reinterpreted from its filename.
Neither case rewrites a file.

For a non-flattened legacy run, an empty, unknown, duplicate, multiple-base,
incompatible-overlay, or mixed non-Builder/geographic composition fails explicitly as
`locale_authority_invalid` with diagnostic `details`. It cannot silently become
Continental US. The checked-in US default is an intentional compatibility
value, not a runtime error fallback. This new validation does not run for the
flattened no-capability/schema-v1 compatibility mode described above.

## Legacy Live-Registry Authority

For legacy mode only, these exact single-token compositions select the matching
live Builder graph:

| Effective `.cfg` locale token | Builder profile |
| --- | --- |
| `us` | `continental-us` |
| `eu` | `europe` |
| `canada` | `canada` |
| `au` | `australia` |
| `earth` | `global-earth` |

The resolver must use the same server-owned graph builder as Builder
description and creation. It cannot reconstruct axes from frontend lists,
config labels, filenames, feature-registry metadata, or broad domain catalogs.
A recognized Builder profile whose registry cannot load fails explicitly as
`builder_registry_error` with diagnostic `details`; it does not fall back to a
broader catalog.

Legacy config-token query overrides may not set `general.locales`. Flattened
creation continues to reject that unknown durable override with HTTP 400
`project_config_validation_failed`; legacy creation/config loading must reject
it before directory publication or controller initialization. Locale never
enters an established-Interface link or legacy config-token override.

Live registry changes may intentionally change the options of a legacy run
because that run has no frozen graph. A Builder-created schema-v2/v3 run never
changes implicitly. Schema-v2 remains permanently frozen and refresh-
unavailable; only an eligible complete schema-v3 project may adopt the current
same-locale graph through an acknowledged capability refresh. This distinction
must be named in the UI/developer contract and tested.

## Explicit Capability-Authority Refresh

The existing project-config update flow gains a second update class. A pure
attribute update retains version 1 merge-only behavior. A capability refresh
atomically replaces the stored capability envelope with the current canonical
axes, relationships, provider revision, and structural identity for the
same `[general] locales` composition. It does not replace project selections
with current Builder defaults. Builder creation, legacy live resolution,
update preview, and refresh application must all call the same public server-
side locale-to-graph resolver; no update path may reconstruct capability axes
independently.

Refresh eligibility is limited to a complete valid schema-v3 graph whose
locale composition is exactly one of the five Builder-exposed bases and whose
manifest `source_kind` is `builder`. Schema-v2, schema-v1, no-capability,
preset-source, overlay, specialized, and RHEM projects retain their current
update availability and cannot capability-refresh. This is not a migration
accommodation: there are zero existing Config Builder projects to migrate, and
all newly created Builder projects use the current schema-v3 contract.

Eligibility requires exact locale and selection congruence before registry
comparison. `[general] locales` must equal the one canonical runtime-token list
for the stored `capabilities.locale_profiles` ID;
`capability_defaults.locale_profile`, manifest `selections.locale`, and the
stored graph profile must be that same Builder locale; manifest
`selections.capability_profile` must be that locale's capability component; and
the manifest's selected DEM, climate, station database, landuse, soil, model
tuple, and mods must equal the selection-bearing config values. A preset
manifest has no Builder selection record and is refresh-unavailable. Every
mismatch returns HTTP 409 `config_update_unavailable` with diagnostics before
reservation, mutation, or enqueue.

Refresh rebases the current canonical envelope around the project's existing
selection-bearing config. Every `capability_defaults` value, `nodb.mods`, and
the linked `climate.cligen_db` selector remains canonically identical; the
refresh never substitutes the locale's current Builder defaults. Before a
preview is available, the preserved defaults and mods must remain members of
the new axes, satisfy every adjacency, model-tuple, requires/conflicts, and
station-database/runtime-selector invariant, and retain the same locale. If
any preserved selection was removed or became incompatible, preview returns
HTTP 409 `config_update_unavailable` with diagnostic `details` naming the
conflicting stable IDs. It does not auto-select a replacement, reserve a job,
write, or enqueue. Persisted controller choices that are outside the refreshed
envelope remain governed by the exact-current carveout below.

A capability refresh is never automatic. Availability is read-only. Preview
must show the complete prior-to-current delta for axes, relationships,
defaults, provider revision, selected-chain revisions, and added features'
canonical support state when one exists. Locale cannot change through this
operation.
Cross-locale composition, unresolved registry state, a partial graph, or a
stale preview fails without mutation or enqueue.

Historical provenance is bounded by what Builder creation actually stored.
The prior identity never invents per-component revisions for unselected graph
members. It records the aggregate stored provider revision, the complete
stored WEPP-binary revision mapping, the selected `parent_chain` revisions,
and the deterministic graph and structural identities. The resulting identity
records the corresponding current values. For an added ID, `support_state` is
the canonical registry/provider-catalog value when defined and JSON `null`
otherwise; no synthetic `maturity` value is introduced.

The preview response retains `preview_id`, `current_digest`, `digest_warning`,
and `additions`; adds deterministic `resulting_digest`; and adds `update_kind`
with exactly `additive`, `capability_refresh`, or `combined`.
`capability_refresh` is null for `additive`; otherwise it contains:

- `locale_profile` and the unchanged runtime locale tokens;
- `preserved_project_selections`, containing canonical values for every
  preserved `capability_defaults` option, `nodb.mods`, and
  `climate.cligen_db`;
- `acknowledgment` with `required = true`, revision
  `PC-24-capability-refresh-v1`, and the exact warning text below;
- `prior` and `resulting`, each with string `graph_sha256`, string
  `structure_sha256`, string `provider_revision`,
  `wepp_binary_revisions` as a stable-ID-to-revision object, and
  `selected_parent_chain` as an ordered list of `{kind, id, revision}` string
  objects; and
- a deterministically sorted `changes` list. Each row has string `section` and
  `option`; `kind` equal to `added`, `removed`, or `changed`; canonical JSON
  `before` and `after` values with JSON `null` representing absence; sorted
  string lists `added_ids` and `removed_ids`; and `added_support` sorted by ID,
  whose rows are exactly `{id: string, support_state: string|null}`.

`changes` sorts by `(section, option, kind)`. IDs sort lexicographically by
their canonical stable ID. `graph_sha256` is SHA-256 over the canonical project-
config serialization of exactly the complete capability sections, including
the selection-preserving `capability_defaults`. `structure_sha256` is SHA-256
over canonical sorted-key compact JSON for the structural contract defined
below. These serialization rules are shared by preview, apply, and manifest;
there is no implementation-dependent object hashing.

The preview ID hashes the config bytes, manifest bytes, complete additions,
complete capability-refresh object, and warning revision. The same reversible
`changes`, prior/resulting identities, and acknowledgment revision are written
to the successful manifest amendment, together with
`preserved_project_selections`.

Availability retains its existing fields and adds `current_digest`,
`update_kind`, `acknowledgment_required`, and `last_update`. It does not return
the graph delta. `last_update` is null or the latest amendment's exact
`{sequence, kind, preview_id, prior_sha256, resulting_sha256}` values:
`sequence` is an integer; `kind` is one of the three update kinds;
`preview_id` is a string or JSON `null`; and both digests are lowercase SHA-256
strings. A historical entry without `kind` is reported as `additive`; one
without `preview_id` reports JSON `null`. It contains no actor identity or
warning text. When updates are disabled or unavailable, `update_kind` and
`acknowledgment_required` are null and false; digest and last-update
reconciliation fields remain read-only.

The modal must display this exact acknowledgment text next to an initially
unchecked checkbox:

> I understand that refreshing capability authority changes this project's
> modeling envelope, diminishes strict provenance continuity with its original
> configuration, and may expose Preview or otherwise unstable features.

The apply button remains disabled until the user checks it. The rq-engine apply
request must contain exactly this additional object when the preview includes
a capability refresh:

```json
{
  "capability_acknowledgment": {
    "accepted": true,
    "revision": "PC-24-capability-refresh-v1"
  }
}
```

The acknowledgment is required equally for browser and direct API callers.
The browser never persists acknowledgment state: it resets the checkbox on
every preview load, stale/error response, modal close, and successful apply.
The existing `preview_id` remains required. `trigger` is required exactly when
the preview has missing-attribute additions, including a combined update, and
is absent for a capability-only refresh. `capability_acknowledgment` is
required exactly when the preview has a capability delta and is absent for an
additive-only update. Payload shape must match the current preview.
Missing, false, unknown, or mismatched acknowledgment returns HTTP 400
`capability_refresh_acknowledgment_required` without reserving a job.
Revalidation binds the acknowledgment revision and exact capability delta to
the opaque preview ID; drift returns the existing HTTP 409
`stale_config_preview` contract.

Apply runs under the existing owner/Admin/Root authorization, project lock,
reservation, and crash-recovery transaction. One atomic replacement writes the
selection-preserving current envelope and any compatible missing registered
attributes, then appends one manifest amendment. That record must contain the
acknowledgment
revision, application revision/time, prior and resulting config digests, prior
and resulting capability/provider revisions, and a reversible old/new delta
for every changed axis, relationship, and default. It also stores the opaque
`preview_id` so retry and read-only status can reconcile commit outcome. It
must not store personal identity. This preserves an auditable discontinuity;
it does not claim strict creation-time reproducibility after refresh.

The original manifest `selections`, `parent_chain`, creation provenance,
source identity, and all prior amendment entries remain semantically
unchanged; refresh only appends the new amendment and updates the manifest's
resulting config digest. The appended entry distinguishes preserved project
selections from changed envelope defaults/relationships so the audit record
never implies that a current Builder default was selected by the user.

The existing transaction's recovery semantics remain authoritative for every
update kind. Rejection before Redis reservation has no queue or file side
effect. Once apply is accepted, the RQ job and reservation are observable
history even if the worker later fails. Before config replacement, recovery
retains the prior config/manifest pair; after config replacement, recovery
rolls the manifest forward to the result pair. After manifest replacement it
retains the result pair. The terminal job/UI response must reopen and report
which complete pair recovery established; it must never report a generic
failure while leaving the user unable to tell whether the acknowledged refresh
committed. A retry with the same stored `preview_id` returns the already-
committed result idempotently. After any terminal job failure, the browser
rechecks availability and compares its preview's prior/resulting digests with
`current_digest` and `last_update`, reporting `not applied`,
`committed/recovered`, or an explicit indeterminate diagnostic. Direct clients
can perform the same check. Pure additive updates retain these exact semantics
and use the same reconciliation fields for new amendments.

The idempotent rule matches only the latest amendment. Under the project lock,
the current config digest must equal that entry's `resulting_sha256` and its
non-null `preview_id` must equal the request. The rq-engine apply endpoint then
does not reserve or enqueue and returns HTTP 200 with exactly
`{applied: true, recovered: true, sequence: integer, prior_digest: string,
resulting_digest: string}`. An RQ retry returns the same fields in its job
result. A null/different/non-latest preview ID follows normal stale-preview
handling; a matching latest ID with a mismatched current digest returns HTTP
409 `config_update_unavailable` with diagnostic details. A newly committed
normal job result uses the same object with `recovered: false`. No retry appends
a second amendment.

Preview must validate the resulting config, manifest, journal, and archive
member sizes against existing canonical safety bounds. If the reversible record
cannot fit, refresh is unavailable with diagnostic details; it may not truncate
the delta or weaken archive validation.

Manifest schema version remains 1. Each new amendment entry has `kind` equal to
`additive`, `capability_refresh`, or `combined`; historical additive entries
without `kind` retain their current interpretation. Pure additive entries do
not acquire capability-refresh acknowledgment fields.

The refreshed stored graph becomes presentation and submission authority only
after the atomic commit and page reload. A persisted current choice removed by
the refreshed graph retains the exact-current visibility/rebuild carveout; it
cannot authorize a different removed value. No rollback, locale change, silent
refresh, selection substitution, or background migration is introduced.

## Run-Control Contract

Land-cover datasets and methods, soil builders, climate datasets, climate
station methods, and climate spatial methods use the resolved run authority at
both presentation and submission/build boundaries.

For a recognized legacy Builder profile, all authorized graph options render.
If a persisted current dataset is outside that live graph, it appears as
exactly one disabled current option in addition to every authorized option so
the user can recover. Its dependent method control shows the exact current
state until an authorized dataset is selected. An ordinary exact-current
rebuild remains allowed. A different unsupported stable or runtime value fails
before NoDb mutation, timestamp removal, file write, or enqueue. No current
value is silently substituted.

Persisted `Ron._locales` is not authority at the scoped landuse, soil, and
climate consumers for a non-flattened legacy run whose effective `.cfg` can be
read. That legacy reopening resolves locale from the effective `.cfg` without
changing the global `NoDbBase.locales` property and without rewriting
`ron.nodb`, another controller file, or the run tree. Flattened no-capability
and schema-v1 projects retain their existing locale/catalog path. Project-local
legacy configs retain precedence over shared presets exactly as section 6.2
currently requires.

## Error Transport Contract

An invalid effective locale in non-flattened legacy mode returns
`locale_authority_invalid`: HTTP 409 for Flask JSON and rq-engine JSON, using
their canonical error envelope with diagnostic `details` and `error_id`; the
HTML run page returns a diagnostic 409 error page with the same code and an
error ID. An unavailable live Builder registry when that legacy mode requires
one returns `builder_registry_error`: HTTP 503 at all three boundaries, with
the same envelope/page requirements and a `Retry-After: 5` header. Auth and
run-access failures still occur first. The generic RQ response envelope remains
unchanged. Capability-refresh apply without the exact preview-bound
acknowledgment returns HTTP 400
`capability_refresh_acknowledgment_required`; a changed graph, warning
revision, config, or manifest returns the existing HTTP 409
`stale_config_preview`. Both fail before reservation or enqueue.

## Exact Source and Consumer Boundary

Allowed configuration changes are exactly the `.cfg` files named above.
Allowed implementation consumers are:

- `wepppy/nodb/config_builder/resolver.py` and `resolver.pyi`, plus
  `wepppy/nodb/config_builder/__init__.py` and `__init__.pyi`, for one public
  server-side locale-to-graph reader shared with Builder description;
- `wepppy/nodb/config_builder/registry.py` to expose existing canonical
  landuse/climate support states on synthesized components for refresh preview;
- `wepppy/nodb/locales/capability_graph.py` for the append-only schema-v3
  structural-identity allowlist, deterministic structure hash, and separated
  internal/structural validation;
- `wepppy/nodb/locales/__init__.py` only to reexport the ratified capability
  structure helpers, without owning a runtime decision, plus
  `wepppy/nodb/locales/capability_structures/README.md` and
  `capability_structures/catalog.json` for the append-only reader-floor
  structure authority and its maintenance contract;
- `wepppy/nodb/project_config_capabilities.py` and its stub for the explicit
  stored-or-legacy run-authority resolver and matching domain helpers;
- `wepppy/nodb/project_config_reader.py` and its stub, plus
  `wepppy/microservices/rq_engine/project_routes.py`, to prohibit locale query
  overrides before run publication or legacy load;
- `wepppy/nodb/project_config_update.py` and its stub,
  `wepppy/microservices/rq_engine/project_config_update_routes.py`, and
  `wepppy/rq/project_config_update_rq.py` for preview-bound acknowledged graph
  replacement, atomic apply, and manifest provenance;
- `wepppy/nodb/locales/locale_profiles.py` for the canonical supported-non-
  Builder Turkey identity;
- `wepppy/nodb/core/landuse.py` and `landuse.pyi`, `soils.py` and `soils.pyi`,
  and
  `climate_station_catalog_service.py` for non-flattened legacy
  effective-config locale at the exact locale-sensitive landuse list/Australia
  build, Chile/Europe/Australia soil dispatch, and climate catalog/heuristic
  consumers; flattened compatibility paths and the global `NoDbBase.locales`
  property are non-change assertions;
- `wepppy/weppcloud/routes/run_0/run_0_bp.py` and
  `templates/controls/{landuse,soil,climate}_pure.htm` for presentation;
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm`,
  `wepppy/weppcloud/controllers_js/project_config_update.js`, and the generated
  `wepppy/weppcloud/static/js/controllers-gl.js` for the exact warning,
  accessible acknowledgment, delta preview, and apply payload;
- `wepppy/weppcloud/routes/usersum/weppcloud/rq-engine.md` for the user-facing
  preview, acknowledgment, refresh, error, and provenance-discontinuity
  workflow;
- `wepppy/weppcloud/routes/nodb_api/climate_bp.py`, `climate_bp.pyi`, and
  `soils_bp.py` for the listed discovery/setter boundaries; and
- `wepppy/microservices/rq_engine/climate_routes.py`, `landuse_routes.py`, and
  `soils_routes.py` for the paired build/set boundaries; and
- `wepppy/microservices/rq_engine/schema_defaults_routes.py` and
  `orchestration_read_routes.py` for run endpoint schemas/defaults/errors,
  aggregated operation documents, pipeline, and readiness parity; and
- `wepppy/microservices/rq_engine/auth.py`, with regression coverage in
  `tests/microservices/test_rq_engine_auth.py`, only for the Forest-required
  identity handoff that prefers the existing signed numeric `user_id` claim
  and retains numeric `sub` fallback without broadening authentication or
  authorization.

The enqueue signature change also requires synchronized
`wepppy/rq/job-dependencies-catalog.md` and
`wepppy/rq/job-dependency-graph.static.json` evidence, without changing queue
topology or dependency edges.

The Config Builder links, `interfaces.htm`, `weppcloud_site.py`,
`config_registry.yaml`, and feature-registry schema/runtime modules are explicit
non-change assertions. Discovering a required unlisted implementation file
stops WP12D and requires amendment plus operator re-ratification.

Unlisted route behavior, model execution, data providers, defaults other than
`general.locales`, queue topology/dependency edges, authentication or
authorization changes beyond the exact identity handoff above, uploads, and
migrations are excluded.
The exact unrelated dirty-path exclusions remain recorded in the tracker and
active ExecPlan and must never be staged.

### Ratified scope-audit correction

The post-implementation comparison from documentation checkpoint `596ff5758`
through technical Forest candidate `588608f1a` found only the three support
entries added above: the export-only locale package initializer, the checked-in
append-only capability-structure authority and maintenance contract, and the
bounded RQ identity handoff with its regression test. The project operator
ratified audit-only amendment `PC-24/WP12D-20260828-4` exactly as documented on
2026-08-28, preserving every existing commit and requiring parent WP12 to
carry and repeat the comparison before canonical merge or production
promotion. The authoritative audit record is
`artifacts/20260828_scope_audit_correction.md`.

## Compatibility and Parameterization

There are zero existing Config Builder projects requiring migration or support;
historical Builder compatibility must not drive the design. This package does
not silently migrate or rewrite any run. It changes an absent
effective locale to historical Continental US and corrects
Canada/Tenerife/Portland/RHEM locale identities, so the parameterization ADR
gate is `yes`. The standalone checkpoint must amend ADR-0047 before config or
implementation edits.

WP12D must create and record a standalone implementation reader-floor revision
before refresh writing is exposed. That commit contains append-only structural
validation and can read every graph identity the writer candidate may produce;
the capability-refresh writer is absent while existing additive behavior is
unchanged. Forest deploys and validates this reader floor first, then deploys
the writer candidate. After one acknowledged
schema-v3 refresh and reopen, rollback returns to the recorded WP12D reader
floor, reopens the same project, and proves the refreshed config and manifest
remain readable and byte-for-byte unchanged.

Existing reader floor `187a856d47e522cfd7ed489a53d06007ed8e1bf7`
remains a rollback target only before any WP12D capability refresh is exposed.
It is not claimed to understand future allowlisted structural identities and
must not be deployed after a refresh has committed. Each future map/capability
structure change repeats the same reader-first gate before its writer is
enabled. Rollback never rewrites or deletes a run.

## Canonical Checkpoint Promotion Map

After exact ratification, the standalone checkpoint must:

1. amend project-config sections 5.1, 6.2, 6.3, 7.1, 7.4, 8, 9, 10, 11,
   13.1, 14, and 15 with the effective `.cfg`, no-link-locale, dual-authority,
   acknowledged capability-refresh, manifest, atomicity, error, rollback, and
   evidence rules. Section 8 must distinguish immutable envelope and per-
   dataset method-default structure from selection-bearing
   `capability_defaults`, define the append-only structural identities, and
   cross-link the reader-first writer gate;
2. add WP12D and PC-24 to the roadmap DAG/table/ownership ledger and make WP12
   depend on WP12D;
3. amend ADR-0047 with the shared US default, exact normalization set, live
   legacy graph policy, stored Builder graph precedence, and explicit
   provenance-diminishing capability refresh;
4. normatively amend `docs/ui-docs/controller-contract.md` for presentation and
   paired-submission parity plus the accessible acknowledgment interaction;
   and
5. amend `docs/schemas/rq-controller-state-contract.md` and
   `docs/schemas/rq-engine-agent-api-contract.md` so five recognized
   legacy profiles advertise live Builder authority through run schemas,
   defaults/errors, operation documents, pipeline, and readiness, with the
   exact 409/503 error semantics above and unchanged generic envelopes, and so
   update availability/preview/apply expose the exact update-kind, delta,
   acknowledgment, and 400/409 contracts; and
6. record `docs/schemas/rq-response-contract.md` as an unchanged applicable
   contract and prove the route-specific 409/503 semantics are additive to its
   generic envelope and error-ID rules; and
7. add a feature-registry specification non-change assertion that registry
   metadata does not own locale; and
8. update `wepppy/weppcloud/routes/usersum/weppcloud/rq-engine.md` with the
   user-facing warning, preserved-selection behavior, explicit refresh flow,
   reconciliation states, and provenance tradeoff.

Advisory reviews of a proposal do not count as the independent correctness,
governance, and dedicated security reviews required against the ratified
canonical diff. All three must be Ready, with findings dispositioned in their
artifacts, before the standalone checkpoint commit. The implementation
candidate then requires fresh correctness and security review.

## Required Regression Evidence

- Parse every shipped named `.cfg` with shared defaults and assert one valid
  canonical locale composition; assert the exact established, Canada,
  Portland, RHEM, and Tenerife normalizations.
- Prove both Config Builder links and the Interfaces page remain unchanged and
  no locale appears in an established-Interface href, query, form field,
  config token, or override. Preserve the Config Builder's existing validated
  locale selection payload, stored `[general] locales`, and provenance
  manifest/snapshot fields.
- For each of the five live legacy Builder profiles, directly render the exact
  landuse, soil, climate, station-method, and spatial-method graph axes and
  reject cross-profile selections at every paired boundary.
- Reopen real legacy-style runs with no flattened config, including a persisted
  stale `Ron._locales`, and prove effective `.cfg` authority without file
  mutation.
- Exercise project-local `_defaults.cfg` and `_defaults.toml` with absent,
  explicit-empty, explicit-valid, and old Canada/Earth state; prove locale query
  overrides fail before publication/load.
- Prove schema-v2/v3 options do not change when the live registry changes;
  prove stored-read validity is independent of manifest source kind while
  capability refresh is unavailable for schema-v2 and preset-source schema-v3.
  Exercise flattened no-capability and schema-v1 snapshots with absent, empty,
  unknown, and valid locale values; prove no live-registry consultation,
  preserve every present valid v1 axis, and preserve existing malformed-
  present-axis failures. Prove non-Builder, overlay, Turkey, RHEM, and project-
  local legacy behavior remains in its contracted mode.
- Validate each current production schema-v3 structural identity, prove
  `280cf7e84` and current resolve to the same identity, and reject an unknown
  internally consistent identity. With a test-only two-identity same-locale
  catalog, prove a genuine axis/relation/per-dataset-default transition. Prove
  the structure hash excludes dynamic binary/provider and project-selection
  values but includes every structural axis, relation, and per-dataset method
  default.
- Reject every runtime-token/graph/default/manifest locale, capability-profile,
  source-kind, and selection mismatch before reservation or mutation.
- Prove Builder creation, legacy resolution, refresh preview, and refresh apply
  use the same locale-to-graph resolver. Registry drift must affect legacy
  options and project update availability, but not stored project authority
  before acknowledged apply.
- Exercise additive-only, capability-only, and combined previews. Render every
  axis/relation/default/provider/selected-source/support-state delta; assert the
  exact JSON keys/types/null encoding/sort order and both hash serializations;
  keep acknowledgment unchecked and apply disabled; reject missing, false,
  wrong, and stale acknowledgments before reservation, write, or enqueue.
- Preserve a non-Builder-default selection such as Daymet, all other primary
  defaults, mods, and `climate.cligen_db` across refresh. Make a removed or
  incompatible preserved selection unavailable with diagnostic stable IDs and
  no substitution, reservation, mutation, or enqueue.
- Apply one acknowledged refresh and prove one atomic config/manifest change,
  reversible old/new manifest delta, exact acknowledgment revision, no stored
  personal identity, and refreshed UI/API/RQ parity after reload. Inject faults
  before and after config replacement and prove recovery retains the prior pair
  before that commit point, rolls forward the result pair afterward, and makes
  the terminal job/UI state identify the recovered result. Preserve the same
  behavior for pure additive updates. Prove historical last-update inference,
  exact latest-preview idempotent HTTP/RQ results, non-latest stale handling,
  digest-mismatch refusal, and that no retry appends a second amendment.
- Assert Turkey's exact serialized profile record and deterministic catalog
  revision, then reopen `yasin` and prove its fixed config-owned maps and
  localized legacy climate behavior are unchanged.
- Direct per-domain positives must prove ordinary exact-current builds remain
  allowed. Negatives for different unsupported values must prove no NoDb,
  timestamp, file, or queue mutation.
- Missing registry, empty/unknown/duplicate/multiple-base/incompatible/mixed
  locale state must return explicit diagnostic failures without partial UI.
- RQ endpoint schema/default/error, operation-document, pipeline, and readiness
  payloads must advertise the same choices the paired mutations enforce.
- Exact-host `forest` evidence must reopen one legacy run per Builder profile
  plus stored schema-v2/v3 fixtures without rebuilding an image. It must apply
  and reopen one acknowledged eligible schema-v3 real provider/binary refresh,
  then restore the recorded WP12D reader floor and prove the refreshed config
  and manifest reopen and remain byte-for-byte unchanged. It must also prove
  that `187a856d4` is used only before writer exposure. This is not evidence of
  a production structural-map transition; the first such change carries its
  own reader-first Forest gate. Production is excluded.

## Exact Ratification Requested

Ratification authorizes the `.cfg`-owned locale model, exact normalization set,
live Builder graph authority for recognized legacy base profiles, stored
authority for schema-v2/v3 projects, explicit acknowledged same-locale refresh
for congruent Builder-source schema-v3 projects only, selection-preserving
envelope rebasing, append-only structural identities, a WP12D reader floor with
the refresh writer absent, unchanged Interfaces navigation, no silent
migration, the bounded source/consumer list, standalone checkpoint, and
subsequent implementation.

It confirms that WP12D may compose the named project-config, Pure controller,
RQ controller-state, and feature-registry owners only for this exact behavior,
without advancing or closing those owners or their unrelated requirements.

It authorizes overlap with still-open WP12C only above candidate `b31eeb625`,
audit correction `f6784420a`, and deployed reader floor `187a856d4`. It does not
claim or replace WP12C writer/provider/create/reopen acceptance and does not
authorize production or any unlisted change.

## Approval

Ratified exactly as documented by the project operator on 2026-08-27. The
operator authorized the standalone canonical checkpoint and subsequent
implementation. No config or implementation file may be edited before the
canonical amendments, independent binding reviews, disposition, and standalone
ancestor checkpoint commit.

Audit-only amendment `PC-24/WP12D-20260828-4` was ratified exactly as
documented by the project operator on 2026-08-28. It corrects the bounded
support-file inventory, preserves all existing commits and evidence, and adds
no new behavior or production authority.
