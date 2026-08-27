# Make locale dependencies authoritative for Builder and run views

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
- [ ] Implement canonical locale profiles and dependency resolution.
- [ ] Expand the flattened capability contract and normalize `continental-us`.
- [ ] Wire climate, landuse, soil, and watershed presentation/submission parity.
- [ ] Add generated matrix and compatibility evidence.
- [ ] Pass correctness, security, quality, and Forest acceptance gates.
- [ ] Close WP12B and hand the accepted revision to WP12.

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

## Outcomes & Retrospective

Pending implementation. WP12 remains blocked until the generated matrix and
representative Forest provider flows pass.

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

Plan revision note (2026-08-27): initial WP12B scaffold and contract checkpoint.
