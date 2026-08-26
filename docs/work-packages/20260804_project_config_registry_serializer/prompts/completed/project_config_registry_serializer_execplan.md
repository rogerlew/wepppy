# Deliver the project configuration registry and serializer

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

Initiative branch: `feature/project-owned-config`. Canonical branch: `master`.
Promotion policy: merge only at the roadmap promotion gate.

## Purpose / Big Picture

After WP03, later creation/update packages can ask one typed registry to
describe and resolve the supported continental-US builder family. The same
selections always yield the same complete typed map, canonical `.cfg` bytes,
ordered provenance, and effective writers. Invalid or unregistered choices
fail before any project exists. WP03 itself writes no run artifact.

## Progress

- [x] (2026-08-26 19:16 UTC) Verify branch, prerequisites, requirements, and current runtime values.
- [x] (2026-08-26 19:16 UTC) Scaffold package and record compatibility plan.
- [x] (2026-08-26 19:39 UTC) Implement schema, TOML loader, initial registry, and resolver.
- [x] (2026-08-26 19:43 UTC) Add descriptor/evolution/composition/matrix/canonical-byte fixtures.
- [x] (2026-08-26 19:51 UTC) Validate, review, document evidence, archive plan, close, and commit WP03.

## Surprises & Discoveries

- Observation: WP00B already supplies the complete canonical typed parser and
  serializer, so WP03 must compose typed maps rather than duplicate lexical
  logic.
  Evidence: `wepppy/project_config_serialization.py` exports
  `parse_config_text()` and `serialize_config()` with collision/sanitization
  gates.
- Observation: the contract's soil/land-use prose uses conceptual names while
  current runtime options are `[soils] ssurgo_db` and `[landuse] nlcd_db`.
  Evidence: `_defaults.cfg` and the controller accessors use those deployed
  keys; WP03 will retain them and expose semantic stable IDs separately.
- Observation: the ratified climate IDs contain underscores even though the
  initial stable-ID validator accepted only hyphen-separated tokens.
  Evidence: correctness review compared the first TOML corpus with contract
  section 7.2.1; the validator and corpus now preserve the exact tokens.

## Decision Log

- Decision: implement the suggested `wepppy/nodb/config_builder/` layout with
  real TOML profiles and no dynamic Python loading.
  Rationale: this is the contract's preferred ownership boundary and provides a
  static, reviewable registry.
  Date/Author: 2026-08-26, Codex.
- Decision: use a caller-supplied or canonical shared-defaults typed map as the
  first virtual contributor.
  Rationale: defaults are already canonical deployment sources, not a builder
  component; duplicating them in TOML would create drift.
  Date/Author: 2026-08-26, Codex.
- Decision: registry revision is a SHA-256 over sorted relative paths and exact
  TOML bytes.
  Rationale: descriptions and stale-schema checks need a deterministic identity
  that changes for any source-definition edit.
  Date/Author: 2026-08-26, Codex.
- Decision: soil, land-use, and climate selections are ordered registered
  capability contributors before the umbrella capability-list profile.
  Rationale: each selection needs stable provenance even when it has no static
  write, while the umbrella profile remains the final component contributor.
  Date/Author: 2026-08-26, Codex.

## Outcomes & Retrospective

WP03 delivered a dormant in-memory registry/resolver with 13 real-TOML source
documents, exact stable IDs, closed locale allowlists, deterministic canonical
bytes, ordered provenance, and effective-writer records. Correctness review
resolved stable-ID and schema-tightening findings. Focused tests passed 60/60,
NoDb passed 1,740 with 26 skipped, and the exact final repository suite passed
6,864 with 63 skipped. No writer, route, queue edge, feature flag, project
directory, or generated run artifact was added. WP11 retains deployed Forest
acceptance for each locally eligible matrix combination.
The implementation revision is `1bb9e49f4`.

## Context and Orientation

`wepppy/project_config_serialization.py` is WP00B's canonical typed INI
boundary. `wepppy/nodb/configs/_defaults.cfg` is the canonical shared base.
WP03 adds `wepppy/nodb/config_builder/`: `schema.py` defines immutable types;
`registry.py` parses/validates all TOML documents; `resolver.py` applies a
validated selection in contract order and calls the WP00B serializer; and
`profiles/` contains deployment-owned source documents. Stable IDs are durable
semantic identifiers, not preset filenames or route tokens.

This is faithful, wired core implementation: implemented means all shipped
documents validate and resolve; wired means the public resolver actually uses
the loaded registry and WP00B serializer. It intentionally does not wire a run
creation path. Generated-output evidence is not applicable until WP04/WP06;
WP03 closeout requires exact in-memory canonical bytes and explicit proof that
no run directory changes.

## Plan of Work

Define immutable component, constraint, selection, description, provenance,
and result records. Parse TOML with standard-library `tomllib`; accept only
schema version 1, lower-case durable IDs, known kinds, declared owned keys,
canonical scalar/list write values, and structurally valid constraints. Load
all documents recursively, calculate a content revision, reject duplicate IDs,
and resolve every locale reference after the complete registry is known.

Create the conservative initial profile corpus for the two ratified DEMs, two
delineation backends, single-OFE representation, one soil, one land-use, four
climate selections, no optional mods, and the resolved capability-list profile.
Definitions use real current runtime keys. The WBT component includes its
current required `[watershed.wbt]` settings; TOPAZ uses the defaults already in
the base contributor.

Resolve by deep-copying the typed defaults map, validating the full selection
against locale allowlists, ordering contributors, applying only owned writes,
and rejecting undeclared collisions unless the later component declares the
override. Apply the derived/default or allowlisted cell size as the explicit
final selection layer. Record ordered component provenance and effective
writer per key, produce a deterministic builder description, and serialize
with WP00B.

Tests use shipped and temporary TOML registries to cover malformed syntax,
schema evolution, stable IDs, duplicate/case collisions, references,
constraints, declared writes/writeover, source order, snapshot independence,
new-mod nonenablement, active-component compatible additions, DEM defaults,
the complete local four-combination matrix, excluded IDs, builder constraint
errors, deterministic descriptions, and canonical byte round trips.

## Concrete Steps

From `/home/workdir/wepppy` run:

    wctl run-pytest tests/nodb/test_project_config_registry_serializer.py --maxfail=1
    wctl run-pytest tests/nodb/test_project_config_serialization.py --maxfail=1
    wctl run-pytest tests/nodb --maxfail=1
    wctl run-stubtest wepppy.nodb.config_builder
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260804_project_config_registry_serializer
    git diff --check

## Validation and Acceptance

Each of `2 DEMs x 2 backends` must resolve with both the DEM-associated default
and every fixed allowlisted override; unsupported locale/DEM/backend/
representation/capability/mod IDs must fail without substitution. Repeated and
reordered loads of identical documents must produce one registry revision,
description, typed result, provenance order, and byte string. The bytes must
round-trip through `validate_canonical_config_text()` and retain the flattened
marker supplied by the resolver.

Temporary hostile registries must prove that malformed TOML, unknown schema,
duplicate IDs, unknown references, invalid stable IDs, malformed values,
undeclared writes, and unauthorized collisions fail explicitly. The full suite
and correctness review must leave no unresolved medium/high finding. No route,
queue edge, feature flag, manifest, project directory, or config file writer may
be added.

## Idempotence and Recovery

Registry loading and resolution are read-only. Tests use temporary directories.
No migration or rollback is needed because no persisted state changes; reverting
the new package removes the dormant registry. Invalid sources fail before a
registry is returned, so partial registration is never externally visible.

## Artifacts and Notes

Closeout retains a registry/serializer evidence artifact and required
correctness review. WP11 handoff must distinguish local eligibility from Forest
acceptance for all four combinations.

## Interfaces and Dependencies

Use only standard-library `tomllib`, `dataclasses`, `enum`, `hashlib`, `pathlib`,
and collection utilities plus WP00B's existing parser/serializer. Add no
dependency. Export immutable public records, `load_registry()`,
`describe_builder()`, and `resolve_builder_config()` with matching stubs. Later
packages must consume these interfaces rather than reparse TOML.

Plan revision note (2026-08-26): initial plan created from the ratified
contract, roadmap, checklist, WP00B handoff, and current normalized sources.
