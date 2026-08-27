# WP12C Contract Decision

**Amendment ID**: `PC-23/WP12C-20260827-1`
**Starting revision**: `e1ef3b8df`
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master` at verified origin revision `6af9ecdd6`
**Promotion policy**: WP12C pushes only the initiative branch and may deploy
only to host `forest`; WP12 owns canonical merge and production
**Operator approval**: ratified on 2026-08-27. The operator stated: "I
explicitly ratify amendment PC-23/WP12C-20260827-1 exactly as currently
documented, and authorize the standalone checkpoint commit and subsequent
implementation." The preceding 2026-08-27 sequence explicitly instructed Codex to
integrate the other locales, bounded the set to Continental US, Europe, Canada,
Australia, and Earth, made applicable locale land-use maps authoritative, and
finally specified Canada-wide global datasets plus observed Daymet. Existing
canonical EU/AU/Earth providers and defaults resolve the other profile details.
The operator then required Vanilla CLIGEN in every locale and a separate Climate
Station Database control: Legacy, 2015, and GHCN for Continental US and only
GHCN for the other profiles. The operator then explicitly selected Vanilla
CLIGEN as the default for every profile. This sequence plus the explicit
ratification approves the combined matrix, compatibility, source-boundary, and
rollback amendment.
**Implementation conformance**: candidate `b31eeb625` is independently
correctness/security Ready; Forest acceptance remains pending

## Applicable Canonical Contracts

- `docs/schemas/project-owned-config-contract.md`, sections 7.2, 7.2.2, 7.4,
  8.2, 9, 13, and 15.
- `docs/schemas/project-owned-config-implementation-roadmap.md`, WP12C/PC-23.
- `docs/schemas/rq-engine-agent-api-contract.md` Builder description response.
- `docs/adrs/ADR-0047-project-config-locale-authority.md`.

## Exact Source and Owner Boundary

The finite trusted authority source boundary is
`wepppy/nodb/locales/locale_profiles.py` for profile IDs/runtime tokens/data
lists and locale-owned writes; `climate_catalog.py` for climate IDs, numeric
mode/method defaults, station-database IDs, and their runtime values;
`landuse_catalog.py` for land-cover IDs/runtime
values; the DEM and soil runtime maps in `locale_profiles.py`; and the canonical
WEPP provider functions in `wepp_runner/wepp_runner.py`. The CLIGEN resolver in
`wepppy/climates/cligen/cligen.py` owns instance-local selector-to-database and
PAR-root resolution. Changed implementation consumers are exactly
`wepppy/nodb/locales/capability_graph.py`;
`wepppy/nodb/config_builder/schema.py`, `registry.py`, `resolver.py`, and
`snapshot.py`; `wepppy/nodb/project_config_update.py`;
`wepppy/nodb/project_config_capabilities.py` as the side-effect-free stored
schema-v2/v3 authority reader;
`wepppy/microservices/rq_engine/builder_routes.py`,
`climate_routes.py`, and `schema_defaults_routes.py`;
`wepppy/nodb/locales/__init__.py` as export-only package wiring; and
`wepppy/weppcloud/controllers_js/config_builder.js` plus
`wepppy/weppcloud/templates/config_builder.htm`. Their `.pyi` files and focused
tests are in validation scope. The config-builder registry owns deterministic
typed-component synthesis and composition. Routes and frontend consume only
that registry/stored-run authority and cannot broaden it.

The two consumers above were absent from the ratified checkpoint's supposedly
exact enumeration. The chronology-preserving correction, operator acceptance,
independent control confirmation, and WP12 prevention step are recorded in
`20260827_checkpoint_scope_deviation.md`. They add no authority source or
normative behavior and do not rewrite checkpoint `bb1745fd8`.

Shared preset files remain compatibility evidence, not Builder authority.
Archived work packages, fixtures, labels, filesystem discovery, and frontend
lists cannot authorize a component. Locale profile identity and every
synthesized source revision participate in the registry digest.

## Normative Delta

The Builder-exposed locale set becomes exactly `continental-us`, `europe`,
`canada`, `australia`, and `global-earth`. The exact current authority is
section 7.2.2 of `docs/schemas/project-owned-config-contract.md` and the WP12C
amendment to ADR-0047. `20260827_locale_dataset_matrix.md` is checkpoint and
acceptance evidence only. `canada` is a new base profile and runtime token; it
is not an alias of `earth` or `bc-ca`.

`LocaleProfile` owns DEM, soil, land-cover, climate source, and climate-station
database IDs. Those lists
alone authorize options for Builder presentation and submission. Catalog
support state describes implemented provider maturity but cannot expose a value
outside the selected profile. The profile landuse list is specifically the sole
authority for the Land-cover dataset control.

Description schema version 2 responses add `capability_graphs_by_locale`, keyed
by the five stable profile IDs. Each value is a complete schema-v3 graph. They
also add `components_by_locale`, containing the exact component population for
each profile. The existing `capability_graph` and `components` members retain
the frozen historical Continental-US schema-v2 response shape for read-only
parsing compatibility. New validation and creation clients submit
`builder_description_schema_version = 2` and the station-database selection;
old create clients receive `409 unsupported_builder_schema` before mutation.
Validation and resolution select the graph by submitted locale; they never
validate against a union. Unknown locale keys, missing graphs, and cross-profile
data IDs fail with a field-addressable 4xx and no run mutation.

Run-scoped climate discovery and `build-climate` remain the execution boundary
for the newly exposed climate IDs. New clients submit stable station/spatial
method IDs atomically; numeric compatibility fields may accompany them and must
agree. Numeric climate mode alone cannot authorize a new schema-v3 selection.

Schema version 3 adds mandatory climate-station database authority and immutable
contracts for all five profile IDs. Stored graph validation is independent of
the live registry. Existing Continental-US v2 bytes remain valid and keep their
configured `cligen_db`; no legacy/v1/v2 run is migrated or recomposed.

## Defaults and Runtime Writes

All generated configs remain Preview. WBT and `wepp_260803` remain global
Builder defaults. Per-profile data defaults are those in the matrix. The only
Multiple OFE tuple is `wbt|multiple-ofe|wepp_260803`. The complete canonical
WEPP binary provider list is available for every exposed profile under Single
OFE.

Europe uses its existing ESDAC soil and CORINE land-cover execution paths;
Australia uses ASRIS and the deployed 2010-2011 Australian land-cover provider.
Canada and Earth write explicit global provider values. Canada advertises
observed Daymet for explicit selection while its generated default is Vanilla
CLIGEN. Locale-owned map/unit settings remain explicit and deterministic.

Vanilla CLIGEN is available for all five locales. Continental US exposes
`cligen-stations-legacy`, `cligen-stations-2015`, and
`cligen-stations-ghcn`, defaulting to 2015. The other profiles expose only
`cligen-stations-ghcn`. The selected component writes the exact contracted
`climate.cligen_db` runtime token. Every profile defaults its climate mode to
Vanilla CLIGEN.

The CLIGEN manager MUST resolve its database and PAR root per instance. It MUST
NOT mutate process-global selector/root state. Registry and manifest identity
bind the station stable ID, exact manager selector, and resolver adapter
revision. A direct concurrent Legacy/2015/GHCN test must prove every returned
station path remains under the selected owned root.

## Compatibility, Security, and Rollback

Interfaces preset tokens and existing specialized profiles are unchanged.
Builder components are stable allowlisted IDs; labels, paths, and arbitrary
config values are never accepted as component IDs. Auth, CSRF, ownership,
idempotency, fixed `config.cfg`, diagnostics, and no-partial-run contracts remain
unchanged. Rejections occur before directory creation or NoDb mutation.

Before the first expanded-profile v3 project exists, full revert is allowed.
Afterwards every supported rollback revision must read and enforce all five
immutable v3 profile contracts. Writers may be disabled, but projects are not
rewritten and a schema-v2-only reader is not supported.

Historical schema-v2 update availability, preview, and apply use the frozen v2
resolver and original parent chain. They never synthesize a station-database
component or selection into the v2 manifest. If that chain cannot be resolved,
updates report unavailable and preserve the existing bytes.

## Required Evidence

The checkpoint requires two independent contract reviews. Implementation
requires generated inventory/closure tests, every valid per-profile data tuple,
invalid cross-profile and hostile-graph tests, historical Continental-US v2
round trips and update behavior, description-version negotiation tests, paired
UI/API tests, no-mutation creation failures, direct concurrent real CLIGEN
Legacy/2015/GHCN isolation evidence, and direct
Forest presence/health plus representative real execution for every advertised
provider family. Each of the four newly exposed profiles requires a Forest
create/reopen proof before closure. Canada evidence must explicitly prove the
`canada` token, global data providers, Vanilla CLIGEN as the default, GHCN as
the selected station database, and Daymet as an advertised explicit non-default
option.

Before the first expanded-profile project is created, WP12C MUST deploy a
candidate reader with Builder creation disabled and prove it can parse and
enforce synthetic stored schema-v3 fixtures for all five profiles plus the
historical schema-v2 fixture. That exact
revision becomes the minimum post-create rollback target. Creation may be
enabled only after this reader-first proof is recorded.
