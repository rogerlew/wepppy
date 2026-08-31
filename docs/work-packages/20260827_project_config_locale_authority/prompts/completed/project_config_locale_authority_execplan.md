# Make locale dependencies authoritative for Builder and run views

**Outcome**: Completed 2026-08-27. Revision `3e8d0d09b` implements the typed
locale dependency authority and passed independent review, full local
validation, and exact-host Forest acceptance. The accepted implementation is
handed to WP12; production was not changed.

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
remain current throughout WP12B.

## Purpose / Big Picture

After WP12B, a user selecting a locale in Config Builder sees only compatible
terrain, climate, soil, landuse, watershed, binary, and mod choices. After the
project is created, that project's flattened configuration controls which
climate radios, landuse datasets and modes, soil choices, and watershed options
are rendered and accepted. Adding or revising a locale occurs in one typed
profile graph rather than through unrelated template and catalog conditionals.

## Progress

- [x] (2026-08-27 06:12 UTC) Inventory current registry, catalogs, templates,
  capability helpers, and paired mutation routes.
- [x] (2026-08-27 06:12 UTC) Scaffold WP12B package, tracker, ADR, contract, and
  roadmap checkpoint.
- [x] (2026-08-27 06:25 UTC) Resolve first-review blockers with a closed
  inventory, stored dependency graph/tuples/defaults, versioned compatibility
  matrix, exact boundary, and security checkpoint.
- [x] (2026-08-27 07:14 UTC) Complete independent correctness, governance, and
  high-impact security review of the checkpoint; all returned Ready.
- [x] (2026-08-27 09:02 UTC) Implement 16 canonical locale profiles, complete
  climate/landcover providers, stable runtime mappings, and dependency graph.
- [x] (2026-08-27 09:02 UTC) Emit and fail-closed validate complete schema-v2
  authority; normalize stable profile `continental-us` to runtime token `us`.
- [x] (2026-08-27 09:02 UTC) Wire Builder, run views, Flask/RQ mutations,
  discovery schemas/defaults, pipeline, and readiness to stored authority.
- [x] (2026-08-27 09:02 UTC) Add generated-config round-trip, hostile graph,
  compatibility, discovery, no-mutation, and frontend dependency evidence.
- [x] (2026-08-27 12:59 UTC) Pass the 533-test touched Python matrix, 220-test
  authority subset, 71-test Builder matrix, frontend lint and 107-suite/792-test
  suite, stubtest/stub completeness, broad-exception, and RQ contract guards.
- [x] (2026-08-27 12:59 UTC) Receive Ready dispositions from independent implementation correctness,
  contract correctness, security, and governance re-reviews.
- [x] (2026-08-27 12:59 UTC) Pass the full Python suite: 7,034 passed and 63
  skipped; all five seeded isolation iterations also passed.
- [x] (2026-08-27 13:13 UTC) Pass Forest acceptance on exact host `forest` for
  revision `3e8d0d09bcf5`; record deployed providers, real execution, Builder
  creation/reopen, stored discovery, and invalid no-mutation evidence.
- [x] (2026-08-27 13:13 UTC) Disposition the unrelated file-isolation auditor
  failure without claiming an overall pass, close WP12B, and hand the accepted
  revision to WP12.

## Surprises & Discoveries

- Observation: locale dependencies currently exist in both
  `wepppy/nodb/locales/climate_catalog.py` and
  `wepppy/nodb/locales/landuse_catalog.py`, while Builder TOML duplicates only
  four continental-US climate IDs and one landcover ID.
  Evidence: the runtime climate catalog contains 13 dataset descriptors and
  locale allow/block rules; the Builder capability component contains four.
- Observation: climate dataset descriptors already carry station and spatial
  method dependencies, but the template renders all six station radios and all
  three spatial radios.
  Evidence: `ClimateDataset.station_modes` and `spatial_modes` are serialized
  but `controls/climate_pure.htm` builds fixed option arrays.
- Observation: existing locale tokens include geographic bases and specialized
  overlays such as `portland`, `seattle`, and `laketahoe`, plus specialized
  bases such as `oyster-creek`.
  A comprehensive model must classify them rather than treating every token as
  an interchangeable base locale.
- Observation: independent axis lists cannot preserve dataset-specific or
  backend/representation/binary dependencies.
  Evidence: reviewers demonstrated that the union authorizes invalid
  cross-products once run pages are prohibited from reading the live registry.
- Observation: the live landcover provider contains 163 values, not the 164
  recorded at checkpoint. Its eMapR range ends at 1984; 1983 was an inventory
  transcription error and was removed rather than invented as runtime support.
- Observation: Tenerife uses lowercase runtime spelling
  `eu/corine_landcover/2018`, while the catalog provider uses
  `eu/CORINE_LandCover/2018`.
  Resolution: both map explicitly to `corine-2018`; provider serialization
  keeps the canonical catalog spelling.
- Observation: canonical serialization preserves empty sections, but the
  capability component's write list could not create the two empty mod
  relation sections.
  Resolution: the resolver materializes every graph section before canonical
  serialization, and the v2 reader requires both empty sections.
- Observation: first implementation review exposed that validating graph shape
  alone did not prevent raw numeric climate modes from bypassing stable dataset
  authority, and that discovery built some relationship metadata without
  returning it from the public schema routes.
  Resolution: schema-v2 climate changes now require a stable catalog identity,
  validate mode/method agreement before mutation, restore parser state on
  validation failure, and publish stable climate/model relationships through
  controller and endpoint discovery.
- Observation: stored schema-v2 validation initially consulted the current
  locale and climate catalogs, which could invalidate an older stored graph
  after a compatible catalog addition.
  Resolution: validation now uses immutable schema-v2 grammar and profile
  constants; only new graph construction consults live providers.
- Observation: the isolation checker passed all five seeded suites, then its
  parallel file audit aborted while collecting an unrelated profile-recorder
  test because a Flask stub lacked `Request`; the worker then attempted to
  JSON-serialize a function object and failed to emit a result payload.
  Resolution: record the seeded pass and the incomplete file audit separately.
  Every WP12B project-config/locale-authority file reported `Isolated OK`
  before the tool aborted; the overall isolation gate is not represented as a
  pass.
- Observation: `continental-us` is the only `builder_exposed` profile, so one
  successful Forest creation covers the complete WP12B profile population.
  Evidence: live registry description returned one locale component and run
  `matted-smooth` materialized stable profile `continental-us` as runtime `us`.
- Observation: all 72 WEPP provider values resolved both execution roles on
  Forest, yielding 144 valid role paths and 99 distinct executable files.
  Evidence: no role target was missing or non-executable; direct default
  watershed and hillslope smoke runs both completed 100 simulation years.
- Observation: the directly invoked TerrainProcessor BLC integration helper
  requests no fill without fail-on-unresolved and therefore conflicts with the
  diagnostics safety contract; after that failure, WBT working-directory state
  also contaminated the next relative-path test.
  Evidence: the production BLC path failed closed with 377 unresolved
  depressions on the fixture, while direct WBT fill delineation, installed
  WBT TopazCondition, standalone GDAL conversion, and direct TOPAZ channel
  generation all completed. WP12 retains real-project BLC/MOFE acceptance.

## Decision Log

- Decision: keep `continental-us` as the durable component ID and map it to the
  runtime locale token `us` in the canonical profile.
  Rationale: normalization must not invalidate provenance by renaming an ID.
  Date/Author: 2026-08-27, project operator and Codex.
- Decision: the live registry is creation authority; flattened per-project
  capabilities are run-view and mutation authority.
  Rationale: this prevents registry edits from changing an existing run.
  Date/Author: 2026-08-27, project operator and Codex.
- Decision: model datasets and interaction methods on separate stable axes.
  Rationale: a climate dataset's station and spatial methods are dependencies,
  not additional datasets; the same distinction applies to soil and landuse.
  Date/Author: 2026-08-27, project operator and Codex.
- Decision: no unsupported combination becomes selectable merely because it is
  present in a shipped preset or catalog.
  Rationale: the inventory records deployed behavior, while an explicit support
  state controls Builder exposure and Forest acceptance.
  Date/Author: 2026-08-27, Codex.
- Decision: capability schema v2 stores adjacency, allowed tuples, and defaults;
  v1 continues to enforce only its present coarse axes.
  Rationale: per-project authority must preserve relationships and remain
  backward compatible without live-registry fallback.
  Date/Author: 2026-08-27, Codex.
- Decision: standalone contract checkpoint `4a975657f` is the implementation
  ancestor.
  Rationale: contract-first review completed before production-path edits.
  Date/Author: 2026-08-27, Codex and independent reviewers.
- Decision: historical v2 graph validation is bound to immutable schema-v2
  rules, not exact live-catalog contents.
  Rationale: creation may use the current provider registry, but rollback and
  stored-run reads must remain independent of later compatible catalog edits.
  Date/Author: 2026-08-27, Codex and independent security reviewer.
- Decision: close WP12B after representative provider-family execution and
  complete deployed-provider presence, while retaining the contract's wider
  per-binary/full-project operational matrix for WP12 production acceptance.
  Rationale: WP12B proves locale authority and all currently Builder-exposed
  profiles; the operator explicitly reserved production deployment for WP12.
  Date/Author: 2026-08-27, project operator and Codex.

## Outcomes & Retrospective

Implementation and Forest acceptance are complete. The typed locale
catalog now classifies all 16 shipped profiles, `continental-us` maps to runtime
token `us`, the complete provider definition identities and WEPP role revisions
are bound into schema-v2 authority, and views/discovery/mutations consume that
stored authority. First implementation review materially strengthened the
climate preflight, graph hostile-input validation, v1 compatibility, tuple-aware
WEPP enforcement, diagnostic errors, snapshot-independent rendering, and
snapshot-independent validation.

All independent reviews are Ready. The full Python suite passed with 7,034
tests and 63 skips, and all five isolation seeds passed. On Forest, revision
`3e8d0d09bcf5` created and reopened `matted-smooth`, proved the stable/runtime
locale normalization, returned stored-authority discovery, rejected an invalid
landuse selection without mutation, verified every advertised provider, and
passed representative real GDAL, WBT, and WEPP executions.

The representative terrain matrix used successful WBT fill and TOPAZ channel
execution. A BLC attempt on the fixture failed closed with 377 unresolved
depressions, as designed. The directly invoked TerrainProcessor BLC test has
an argument/diagnostics mismatch and leaked WBT working-directory state after
failure; both are recorded as follow-up rather than hidden as passing evidence.

The repository-wide file-isolation audit remains incomplete because of the
unrelated profile-recorder/tooling failure and is not represented as a pass;
all WP12B modules reported isolated success before the abort. WP12B is closed
and handed to WP12. Production was not changed and remains gated by WP12.

## Context and Orientation

`wepppy/nodb/config_builder/profiles/` contains declarative TOML components.
`registry.py` validates them, `resolver.py` composes them with shared defaults,
and `snapshot.py` creates immutable project artifacts. A capability is a stable
semantic ID written into the generated `[capabilities]` section. The Builder UI
uses the current registry description, but runtime controllers reopen the
flattened project config through `project_config_capabilities.py`.

Today `climate_catalog.py` and `landuse_catalog.py` independently filter options
from runtime locale tokens and mods. `ClimateStationCatalogService`,
`Landuse.landcover_datasets`, and the soil template then apply only part of the
flattened capability lists. WP12B makes the canonical profile graph produce the
lists and makes both rendering and mutation validate them.

A base locale is a geographic/data family such as continental United States,
Europe, Australia, or Oyster Creek. An overlay is a narrower project profile
such as Seattle, Portland, Lake Tahoe, or Tenerife that adds or restricts a
base. Every shipped runtime locale token must be classified as a base, overlay,
or explicitly non-Builder model family such as RHEM.

## Plan of Work

First create a typed canonical locale catalog under `wepppy/nodb/locales/` and
make Builder locale TOML conform to it. Profiles declare runtime tokens,
classification, support state, available component IDs, and capability IDs.
Registry loading must reject unknown references, duplicate runtime authority,
cycles, contradictory requirements, and empty mandatory capability axes.

Next split capabilities into datasets and methods and persist their relations.
At minimum the flattened
schema will distinguish `climate_datasets`, `climate_station_methods`,
`climate_spatial_methods`, `landuse_datasets`, `landuse_methods`,
`soil_datasets`, `soil_builders`, `delineation_backends`,
`watershed_representations`, `wepp_binaries`, and `mods`. Stable-to-runtime maps
belong beside the domain catalog, never in templates.

Then update resolver output and named-preset snapshots to compute deterministic
dependency closure. Existing flattened projects retain their stored values;
legacy projects without capabilities retain current catalog behavior. A
preexisting persisted selection remains renderable under the section-9 carveout
but cannot authorize a different newly submitted value.

Finally wire the run-page climate, landuse, soil, and watershed controls to
resolved capability adapters and enforce identical IDs in Flask/rq-engine
mutation boundaries. Remove duplicated locale conditions only after equivalent
generated and legacy evidence exists.

## Concrete Steps

Work from `/home/workdir/wepppy` on `feature/project-owned-config`. Use
`apply_patch` for file changes. Commit the reviewed contract checkpoint before
implementation. Run focused tests with `wctl run-pytest`, frontend tests with
`wctl run-npm test`, lint with `wctl run-npm lint`, and rebuild generated
controller assets only when controller sources change.

Use a generated matrix test to load every canonical locale profile, resolve
every advertised component combination, serialize a real `config.cfg`, reopen
it through the project capability reader, and compare the resulting view and
server allowlists. On Forest, prove presence/health for every advertised
provider, run representative unmocked execution for every distinct
provider/method family, and create every Builder-exposed base and overlay;
catalog-only tests do not prove deployed datasets.

## Validation and Acceptance

Acceptance requires that changing locale in Builder visibly updates every
dependent choice and clears invalid downstream selections with an announced
reason. A created continental-US run must render only its resolved climate
dataset, station-method, spatial-method, soil, landuse, and watershed choices.
Direct requests for hidden choices must return a field-addressable 4xx error
without mutating NoDb state or enqueueing work.

The generated matrix must cover all supported profiles and reject all unknown
references and invalid cross-profile tuples. Existing project-owned fixtures
must reopen with byte-stable capabilities. Legacy fixtures without a capability
section must retain their prior choices. Forest must create and exercise a
representative project for every profile marked Builder-exposed before WP12B
can close.

## Idempotence and Recovery

Registry and capability generation is deterministic and read-only until the
normal project creation boundary. Re-running tests or Forest description calls
does not mutate projects. Creation uses existing idempotency. Before the first
schema-v2 project exists, WP12B may be fully reverted. After the first v2
project exists, rollback may disable v2 writers and new views but must retain or
redeploy a v2-aware, fail-closed reader and server enforcement path; returning
to a pre-v2 reader is unsupported. No migration, project rewrite, or
read-triggered write is introduced.

## Artifacts and Notes

Store the locale inventory, endpoint matrix, generated capability matrix,
review dispositions, and Forest evidence under this package's `artifacts/`
directory. Never treat generated docs indexes or chat history as authority.

## Interfaces and Dependencies

The canonical locale profile API must expose immutable stable-ID descriptions,
runtime-token resolution, dependency closure, and support state. The Builder
registry consumes that API or schema; domain catalogs own dataset descriptors
and stable-to-runtime method maps. `project_config_capabilities.py` remains the
single run-scoped adapter used by templates and server routes. No new external
dependency is permitted.

Plan revision note (2026-08-27 13:13 UTC): Forest acceptance is recorded at
exact host/revision, the unrelated isolation-tool defect is explicitly
dispositioned without a false pass claim, and WP12B is complete for WP12
handoff.
