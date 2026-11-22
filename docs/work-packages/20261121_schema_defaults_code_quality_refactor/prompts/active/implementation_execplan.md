# Decompose the schema defaults discovery routes

## Purpose and orientation

From the repository root, inspect wepppy/microservices/rq_engine/schema_defaults_routes.py. These ten GET handlers generate the metadata used by clients to choose the next run operation. Preserve their HTTP signatures and the content and order of descriptors while separating request handling, runtime state reads, capability projections, controller schemas, operation definitions and outputs.

## Progress

- [x] 2026-11-21. Identified owners, consumers and baseline metrics.
- [x] 2026-11-21. Wired the extracted discovery builders into the router. Baseline focused tests passed (132 tests).
- [ ] Validate emitted responses, quality metrics, contracts and tests. Record independent review.

## Milestones and verification

First measure the baseline using analyze_python_text in tools/code_quality_observability.py with the system Python and Radon. Next move cohesive responsibility groups into sibling schema_defaults modules and subdivide large builders by domain. Keep execution order where state is read and preserve existing imports used by the session route. Update test patches at the actual lookup sites.

Finally run wctl run-pytest against the schema defaults, auth concurrency, geospatial upload metadata and errors/progress/outputs suites under tests/microservices. Inspect generated JSON for legacy and capability-aware runs. Run wctl run-pytest tests --maxfail=1, measure the final files with the same analyzer, and lint changed documents with wctl doc-lint. Record failures and reproduce baseline failures before attributing them. All commands can be rerun from the task worktree. Reverting the task commits restores the previous implementation.

## Surprises & Discoveries

The operation builder alone spans 2,249 lines. The session route reads the same runtime loader and archived probes import the digest helper. Preserve those integration points.

## Decision Log

On 2026-11-21, chose faithful extraction using existing authority and HTTP contracts. Registering another router or changing request handling at the framework level would expand the observable surface unnecessarily.

## Outcomes & Retrospective

The baseline at c82da0a94 has 5,359 source lines, maximum function length 2,249 and maximum cyclomatic complexity 90. Candidate evidence is pending.
