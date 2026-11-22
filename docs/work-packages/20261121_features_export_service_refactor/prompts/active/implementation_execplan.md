# Extract Features Export carrier identity and cache artifact checks

This ExecPlan follows [the repository plan template](../../../../prompt_templates/codex_exec_plans.md).

## Purpose

Maintainers should be able to locate carrier identity alignment and cache
format checks without reading the entire export service. The same requests must
produce the same ZIP member layout, spatial feature content, and cache
reuse or regeneration outcomes.

## Progress

- [x] Identify the identity-alignment block and cached artifact checks in the service.
- [ ] Extract both blocks and connect them to their current call sites.
- [ ] Run focused validation, record evidence, and integrate the approved work.

## Surprises & Discoveries

The service and join planner use identical normalization for join tokens and key
values. Their column lookup functions differ in handling the label `None`.

## Decision Log

- **2026-11-22 05:53 UTC** — Move format checks for resolved artifacts while
  keeping path confinement and cache policy in the service. Retain the existing
  column lookup semantics when sharing join normalization with the new module.

## Outcomes & Retrospective

Validation and integration are pending.

## Context and Implementation

In `wepppy/nodb/mods/features_export/`, move the carrier key alignment and
watershed identity lookup from `service.py` into `carrier_identity.py`. Carrier
keys link hillslope or channel attributes to geometry. Preserve lookup order,
ambiguous-pair rejection, and dataframe behavior. Use the existing
`join_planner.py` for matching token and scalar key normalization. Point the
identity unit tests at the new owner of the watershed lookup seam.

Move cached GeoPackage, Geodatabase, and CSV checks into
`cached_artifact_validation.py`. The service resolves the cache entry to a path
inside the run before calling it. A rejected artifact continues through the same
regeneration or error path as before.

## Validation and Acceptance

From the candidate worktree, run the following focused command.

    wctl run-pytest --profile python -- tests/nodb/mods/test_features_export*.py tests/rq/test_features_export_rq.py tests/microservices/test_rq_engine_features_export_routes.py -q

Read the test assertions for the generated ZIP, GeoPackage metadata and spatial
feature records. Run scoped Markdown lint and the changed-code exception check.
Commit and open a PR to master, wait for required checks, then merge preserving
the commit and verify its ancestry against freshly fetched master. Retain the
integration receipt outside the commit it identifies.

## Recovery

Each extraction operates on the current service entry points and has no
migration step. Reverting the PR merge restores the previous ownership of the
helpers.
