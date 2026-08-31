# Make project capabilities authoritative for new choices

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

Initiative branch: `feature/project-owned-config`. Canonical branch: `master`.
Promotion policy: merge only at the roadmap promotion gate.

## Purpose / Big Picture

After WP05, a newly flattened project's stable climate, soil, and land-use
capability IDs determine both what controls offer and what mutation/build
routes accept. A hidden choice cannot be submitted directly. Legacy projects
and a flattened project's already persisted controller state retain their
existing behavior.

## Progress

- [x] (2026-08-26 21:20 UTC) Verify branch, prerequisites, contract, and checklist ownership.
- [x] (2026-08-26 21:20 UTC) Scaffold package and record the data/schema compatibility plan.
- [x] (2026-08-26 21:27 UTC) Inventory paired presentation/submission endpoints and stable runtime mappings.
- [x] (2026-08-26 21:38 UTC) Implement capability population, reading, filtering, and validation.
- [x] (2026-08-26 21:42 UTC) Add generated-output/parity/legacy/persisted/security fixtures.
- [x] (2026-08-26 21:48 UTC) Validate and review; archive and commit follow this final update.

## Surprises & Discoveries

- Observation: climate already has semantic catalog IDs, while soil controls
  submit numeric `SoilsMode` values and land-use combines modes with database
  tokens.
  Evidence: `wepppy/nodb/locales/climate_catalog.py`,
  `controls/soil_pure.htm`, and `controls/landuse_pure.htm`.
- Observation: WP03's `continental-us-capabilities` profile is constrained to
  the builder's continental-US family and cannot be assigned wholesale to all
  128 geographically diverse named presets.
  Evidence: its TOML `requires = ["continental-us"]` and the WP04 preset corpus.

## Decision Log

- Decision: activate runtime authority only for a recognized flattened config
  containing validated capabilities; absence preserves legacy behavior.
  Rationale: section 9 explicitly protects legacy projects without resolved
  capabilities.
  Date/Author: 2026-08-26, Codex.
- Decision: separate offered new choices from current persisted state.
  Rationale: the contract forbids using WP05 to normalize or reject a
  pre-contract persisted selection.
  Date/Author: 2026-08-26, Codex.

## Outcomes & Retrospective

WP05 populated every new named-preset snapshot with semantic capability lists
and made those lists the shared authority for climate catalogs, soil modes, and
land-use datasets. Legacy absence and persisted controller state remain
compatible. Focused and exact repository suites, typing, documentation,
correctness, and security reviews passed. WP06 can now reuse the same IDs.

## Context and Orientation

WP04 resolves shared defaults plus a named preset in
`wepppy/nodb/project_config_snapshot.py` and writes a flattened `.cfg`. WP02's
reader in `wepppy/nodb/project_config_reader.py` recognizes top-level and nested
authority. Climate choices come from the semantic catalog in
`wepppy/nodb/locales/climate_catalog.py`; soil and land-use controls currently
submit numeric modes through Flask/rq-engine routes. WP05 introduces one shared
read/validation service so presentation and mutation decisions cannot drift.

Implemented means generated flattened configs contain validated semantic IDs,
and pure helper tests prove decisions. Wired means the actual run page and each
inventoried mutation/build endpoint call those helpers. Generated-output
evidence is required from a real WP04 snapshot; deployed Forest evidence is
WP11 scope.

## Plan of Work

First write an inventory artifact mapping every choice to its template or
catalog producer, payload field, route, runtime value, and stable ID. Record
which choices are creation-family capabilities versus legacy-only modes.

Add a capability module under `wepppy/nodb/` with an exact schema, immutable
semantic-ID sets, stable-ID/runtime mappings, and helpers that load capability
authority through the same top-level project config used by WP02. It must
distinguish legacy absence, valid populated authority, and malformed flattened
authority. Extend WP04 resolution to write the appropriate explicit stable IDs
without assigning the continental-US builder profile to incompatible presets.

Wire the run-page catalog/context producers and mutation/build boundaries to
the shared helper. On flattened projects, filter newly offered values and
reject a newly submitted stable/runtime value not in the config before any
NoDb mutation or enqueue. Do not reject merely because the current persisted
selection is outside the offered set. Leave every legacy path unchanged.

Add direct tests for real generated pairs, every mapping, UI/server parity,
hidden direct submissions, nested authority, malformed capability sections,
legacy projects, and current persisted state. Then run focused, frontend,
NoDb/microservice, stub, docs, broad-exception, exact full-suite, correctness,
and dedicated security gates.

## Concrete Steps

From `/home/workdir/wepppy` run focused tests with:

    wctl run-pytest tests/nodb/test_project_config_capabilities.py --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests/nodb tests/microservices tests/weppcloud --maxfail=1
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260804_project_config_capability_enforcement
    git diff --check

## Validation and Acceptance

A real generated snapshot must contain semantic string lists and reopen with a
valid manifest. Given the same flattened config, each inventoried UI producer
and server validator must expose/accept exactly the same stable IDs. Directly
submitting an omitted ID must return an explicit 400 before controller state or
queue metadata changes. A legacy project without capabilities must produce the
same catalog/options and accept the same requests as before. A persisted value
outside a flattened project's offered set remains visible as current state and
continues existing routing until the user selects a new supported value.

## Idempotence and Recovery

Capability resolution and reads are pure. Snapshot creation remains atomic and
refuses overwrite through WP04. Validation happens before mutation/enqueue, so
rejected submissions leave no recovery state. Disabling the existing reader or
writer flags restores legacy behavior; WP05 introduces no migration/backfill.

## Artifacts and Notes

Retain the endpoint inventory, generated evidence, correctness review,
dedicated security review, exact test counts, feature-flag state, and WP06/WP11
handoffs. Do not record project tokens, user identity, secrets, or production
run identifiers.

## Interfaces and Dependencies

Use only standard-library config/typing utilities and the existing WP02/WP03/
WP04 modules and domain catalogs. Add no dependency. New public Python helpers
must have matching stubs. Preserve the canonical RQ response/error contract,
existing auth decorators/scopes, NoDb locking, route payload field names, and
numeric runtime enums; stable IDs are config provenance and selection authority,
not a forced rewrite of persisted controller serialization.

Plan revision note (2026-08-26): initial plan created from the ratified
contract, roadmap, PC-11 checklist, prerequisite artifacts, and current
climate/soil/land-use presentation and submission paths.
