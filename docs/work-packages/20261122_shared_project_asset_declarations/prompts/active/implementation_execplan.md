# Shared project asset declarations ExecPlan

## Purpose and scope

Allow a producer to change a migrated asset location once while preserving both existing export and query outcomes. Start from the [contract](../../../../schemas/shared-project-asset-declarations-contract.md) and [decision](../../artifacts/20261122_contract_decision.md). This plan owns consolidation; the older catalog refresh package owns fleet capacity and the temporary Rocket cap.

## Progress

- [x] 2026-11-22 UTC. Scaffold the contract, source boundaries, scoped tests, actual-project protocol and independent planning reviews.
- [ ] M0. Confirm the final contract matrix, record any needed canonical cross-owner approvals, and establish its reviewed commit as an ancestor of implementation.
- [ ] M1. Implement shared naming behind both consumer adapters and exercise the scoped local matrix.
- [ ] M2. Execute the actual-project gate and the matched isolated export/writer replays.
- [ ] M3. Review evidence, publish disposition and decide whether to migrate additional families.

## Surprises & Discoveries

Export planners inspect raw locator values for geometry/carrier and SWAT table expansion. Export dependency identity can preserve an authorized parent-relative spelling that is invalid as an external query key. A shared physical-path normalizer could break both consumers.

## Decision Log

2026-11-22 UTC. Keep the layer catalog with Feature Export; extract only the shared asset declarations. Pin the existing producer and both consumers independently as comparison oracles. Require actual production NFS validation before accepting implementation.

## Context and orientation

Start at `wepppy/nodb/mods/features_export/{layer_catalog.yaml,catalog_loader.py,dependency_tracker.py,planner.py}`, `wepppy/query_engine/{activate.py,catalog_refresh.py,access_scope.py,core.py}`, `wepppy/topo/peridot/peridot_runner.py` and `wepppy/wepp/interchange/watershed_loss_interchange.py`. Trace the native output-name tables before changing a Python constant. The first-slice matrix includes baseline/Roads where already supported; Omni child-qualified hill loss uses the existing baseline path. [Audit](../../../20261023_query_catalog_async_refresh/artifacts/declared_asset_audit/findings.md)

## Milestones and validation

**M0 — contract first.** Reconcile the shared contract with the Feature Export, query refresh, query access and output-scope authorities. Map changed symbols and existing valid/invalid outcomes, record independent reviews and disposition their findings. Verify checkpoint ancestry with `git merge-base --is-ancestor <contract-commit> <implementation-commit>`. Resolve any proposed change in public behavior before implementing it.

**M1 — scoped local implementation.** Extend existing focused tests. Add the smallest pure declaration tests for uniqueness, exact paths, bounded templates, supplied selection versus enumeration, and unsupported scope/variable/ID rejection. Reject duplicate declaration IDs and conflicting physical bindings for a public key within one view; allow multiple export roles to reference one declaration. Assert listing multiplicity and lookup. Exercise real temporary Parquets with equal schemas and different values so a wrong source cannot pass unnoticed. Compare old and new locators on the exact same artifacts. Include parent inheritance, child override and contrast-local selection, missing optional input, stale/relocated root, denied sibling/external symlink, and explicit parent-qualified visibility. Retain stable export signature/fingerprint/cache key and public IDs. A simulated writer using the candidate declaration on both sides cannot serve as its own reference.

Run with `wctl run-pytest` against these existing targeted suites, adding test node IDs as they are written:

- `tests/nodb/mods/test_features_export_catalog_loader.py`, `test_features_export_dependency_tracker.py`, `test_features_export_planner.py` and `test_features_export_cache_key.py` in the same directory. Include geometry/source/dependency roles, required/optional missing markers, raw template introspection and equivalent fingerprints under legacy metadata-only and SHA-256 modes.
- `tests/query_engine/test_activate.py`, `tests/query_engine/test_context.py`, `tests/query_engine/test_catalog_refresh.py` and `tests/query_engine/test_http_access_boundary.py`. Cover synchronous and asynchronous paths, visibility versus direct child query, authorized relocation, lookup aliases and readonly behavior.
- `tests/nodb/test_catalog_producer_refresh.py` and `tests/wepp/interchange/test_watershed_loss_interchange.py::test_watershed_loss_interchange_outputs_expected_tables`. Check producer destination, durable notification, actual loss output names, and historical data without declaration metadata. Exercise the watershed producer via `tests/topo/test_peridot_runner_wait.py::test_post_abstract_watershed_prefers_parquet_sources` and `test_migrate_watershed_outputs_from_legacy_csv` in the same file. Run the relevant RQ refresh cases in `tests/rq/test_query_catalog_rq.py` if the async call path changes.

**M2 — environment validation.** Execute every row of the [actual-project protocol](../../artifacts/production_validation.md) against the exact tested candidate. Feed actual producer outputs through both consumers. Preserve failures and record bounded retries when source generations change. Confirm no writes to the original projects or production control plane.

**M3 — handoff.** Update package, tracker and review records with revision, evidence and highest justified claim. Run applicable repository gates for implementation. Remove duplicate location literals only where equivalent outputs and authorization have been demonstrated. A real production cutover requires a separate release decision.

## Idempotence and recovery

Rerun comparisons from an immutable source identity and use a fresh private output directory for each attempt. Stop the isolated candidate to roll back a shadow run. Preserve receipts, admitted jobs, production paths and user artifacts. Reopen the contract if recovery requires a public key, cache or access-policy change.

## Outcomes & Retrospective

The deliverable at scaffold time is the design and acceptance protocol. Code conformance, performance benefit and live candidate parity are unverified.

2026-11-22 UTC revision establishes the contract-first scaffold and production evidence requirements.
