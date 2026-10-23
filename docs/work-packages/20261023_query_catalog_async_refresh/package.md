# Query catalog asynchronous refresh

Status: contract committed and execution scaffold ready; runtime work not started. Deployment and production repair require separate authority.

## Purpose and scope

Make asynchronous query-engine catalog refresh the preferred artifact-writer path while preserving freshness-sensitive consumers. Diagnose and prevent the observed wepp1 submission 502: a missing catalog invokes a native full scan that holds the GIL long enough to starve the web-worker heartbeat.

Deliverables: canonical contract, comprehensive caller/reader disposition, independent contract reviews and disposition, and a prepared pre-implementation checkpoint. The contract-only phase made no runtime changes. The operator subsequently authorized checkpoint commit and execution scaffolding: contract ancestor `dc2b2ddbe8cfedbd4bae024310f03447ca813c32`. Canonical design and caller matrix are reviewed; runtime conformance remains pending.

## Authority and complexity budget

The operator requested: “we need a comprehensive analysis to figure out where the async can be safely deployed. that should be the preferred route. let's do this contract first. author the contract and dispatch agents to review and disposition changes”. This authorizes analysis, contract authorship and independent reviews; it does not assert implementation conformance or authorize deployment. The subsequent instruction “commit and scaffold work-package for execution” authorizes the checkpoint and execution documentation now retained here.

Use existing Redis, RQ queues, workers and scheduler. Permit per-project coordination records and visible refresh diagnostics. No new service, queue topology, datastore, dependency, auth policy, model parameterization, or model-output schema. Existing synchronous APIs remain compatible; caller migration is explicit.

## Security impact

High: future queued work crosses web/worker filesystem boundaries, including nested project scopes and lifecycle races. Dedicated security contract review required. Preserve existing identities, permissions, authorized project roots, readonly behavior, archive/restore and public job disclosure restrictions. Contract review is not execution evidence.

## Evidence and precedent

- wepp1 October 19–23: 15 related submission 502s match rq-engine child deaths across five Jackson-owned projects.
- Read-only scan probe on October 23: 8.56 s full scan, 5.70 s Python heartbeat gap against 5 s supervisor timeout; 4,561 project files on NFS. Temporary local Parquet write: 0.011 s; export excluding catalog: 1.48 s. No production NFS write benchmark.
- `wepppy/rq/wmesque_rq.py` October 14 coalesces queue admission with Redis WATCH; `run_catalog_rq.py` supplies the precedent; run-catalog repository dirty/indexed revisions preserve concurrent invalidations.
- Relevant historical packages: `20261014_wmesque_catalog_sync`, `20260930_run_catalog_projection`. Durable authority remains current contracts, not those packages.

## Acceptance and follow-through

This phase passes when all discovered call sites/readers have an explicit disposition, the canonical design covers concurrency and recovery, independent reviews close medium/high findings, and documentation lint passes. Future runtime acceptance must prove authenticated submission remains responsive, refresh convergence and catalog semantic readback under production-equivalent NFS/identities; queue success alone is insufficient.

Healthy signals: bounded web admission, one admitted refresh per scope, dirty revision convergence, readable atomic catalog and accurate freshness. Danger signals: growing dirty age, missing eligible workers, repeated failures, old-generation publication, duplicate writers or hidden synchronous scans. Future rollout must define its observation window and rollback evidence before deployment; no temporary mitigation is installed here.

## Execution entry points

Use [the active implementation ExecPlan](prompts/active/implementation_execplan.md)
and [launch prompt](prompts/active/execute.md). Record milestone evidence in
[the execution ledger](artifacts/execution_evidence.md) and update [tracker.md](tracker.md).
The completed contract plan remains under `prompts/completed/`. Execution begins
with source/environment admission, shared publication/lifecycle coordination,
recovery and reader barriers before producer migrations. No production action
is implied by the scaffold.
