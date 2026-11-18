# M0 contract checkpoint draft

Date: 2026-11-18 UTC. Status: **scaffold; not an implementation checkpoint**.
Starting source: `392ee2299d8573e038b2e932fe3bdb7e044d1d35`.

## Operator decision

Scaffold implementation on `codex/parquet-csv-cli-package`. Intended delivery:
immediate cutover, no environment-variable-facing configuration, no Python
fallback. Zero-trust input handling and strict JSON response IPC carry forward.
Broad tests follow integration wiring. This approves the direction, not undeclared
compatibility reductions, arbitrary resource defaults or deployment execution.

## Contracts and discrepancy classification

- New [integration contract](../../../schemas/parquet-csv-integration-contract.md):
  records approved policy and draft implementation obligations; conformance pending.
- Existing [CLI contract](../../../schemas/parquet-csv-cli-contract.md): accepted
  standalone wire/resource/input subset; amend before needed native extensions.
- Existing [filesystem contract](../../../schemas/browse-filesystem-contract.md):
  preserve raw access, security/PII precedence, honest failures and retirement policy.
- Existing [filter contract](../../../schemas/weppcloud-browse-parquet-filter-contract.md):
  preserve selection/validation/empty-result semantics, explicitly reconcile CSV
  environment-backed settings without changing other consumers implicitly.

Classification: intended execution-boundary change with compatibility obligations,
not a claim that existing Python code violates an already-implemented native contract.
Security impact high. No project data mutation is planned; CSV artifact semantics
require a compatibility/regression plan before implementation.

## Required checkpoint completion

Record a route/state/type/codec/filter matrix from actual fixtures and projects,
including absent, empty, populated, supported legacy, hostile and retired states.
Specify fixed executable/provenance/scratch paths, code-owned settings, exact
HTTP mappings/headers, serving ownership and crash recovery. Resolve valid cases
excluded by CLI v1 and any versioned filter/input protocol extension. Freeze the
resource ADR and whole-service concurrency/disk/memory accounting under real worker
and mount topology. Inventory and reconcile CSV environment reads explicitly.

Record binary packaging/source-provenance policy and exact-image preflight, an
artifact visibility/retention policy, and regression commands with actual paths.
Amend all affected canonical contracts, then obtain two independent read-only
contract reviews and disposition findings. Commit those documents and dispositions
as a standalone ancestor before implementation. Record that SHA in the tracker.
Do not treat the scaffold commit as the completed M0 checkpoint.

## Regression and review evidence to retain

Real-child CSV/HTTP parity for every covered branch, filter validation/empty/cap
outcomes, auth/containment/PII denials before native invocation, malformed metadata,
external references and allocation limits, missing/tampered binary, bad JSON IPC,
shared-worker busy admission, slow-client disconnect, cancellation, worker death
and restart recovery. Prove no old Python exporter is callable from covered routes.
Run broad pytest after wiring. Exact-image production-equivalent readback is a
release gate; historical standalone results alone cannot close it.

Independent contract reviews: pending. Checkpoint ancestor: pending.
