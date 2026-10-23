# Specify asynchronous query catalog refresh

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Prepare a reviewed contract that moves catalog maintenance out of latency-sensitive requests without losing updates or breaking consumers that need immediate discovery. This plan executes the contract phase only.

## Progress

- [x] 2026-10-23 UTC: Read contract-first and documentation guidance; preserve unrelated dirty files.
- [x] 2026-10-23 UTC: Dispatch writer, reader/lifecycle and queue-design analysis agents.
- [x] 2026-10-23 UTC: Consolidate 79-call/41-file matrix and author canonical contract/checkpoint.
- [x] 2026-10-23 UTC: Obtain independent correctness and security/operations initial reviews; disposition all eight findings.
- [x] 2026-10-23 20:20 UTC: Both independent reviewers confirmed all findings closed.
- [x] 2026-10-23 UTC: Scoped Markdown lint/spelling previews passed; tracker records reviewed scope and remaining ancestor/runtime gates.

## Surprises & Discoveries

The apparent soil export stall follows an already-written 68 KB Parquet: missing catalog triggers native full-project traversal. Native scan blocks Python heartbeat while holding the GIL. Existing WMesque admission suppresses duplicates, but does not alone preserve invalidations arriving during execution.

## Decision Log

- 2026-10-23 / Codex: async preferred for eligible artifact writers; retain explicit synchronous barriers for immediate consumers. Reason: user direction and demonstrated web-process failure.
- 2026-10-23 / Codex: separate query-engine asset catalog from Runs/PostgreSQL catalog; reuse coordination concepts without merging distinct data contracts.

## Outcomes & Retrospective

Initial reviews found four correctness and four security/operations gaps; post-fix review added standalone compatibility and jobstatus wording. All ten findings/clarifications are incorporated and independently confirmed closed. No implementation or production changes.

## Context and Orientation

`wepppy/query_engine/activate.py` scans and writes `_query_engine/catalog.json`; `update_catalog_entry` may escalate a single asset update into a full scan. NoDb export hooks invoke it inside submission paths. `wepppy/rq/wmesque_rq.py` provides transactional admission and the Runs catalog provides dirty revisions. Reader and lifecycle inventory is required before choosing migration boundaries.

## Plan of Work and Milestones

1. Inventory: agents inspect all writers, aliases, reader caches, lifecycle boundaries and existing queue recovery. Record file/function evidence and async/sync/blocked dispositions in `artifacts/caller_matrix.md`.
2. Specification: author `docs/schemas/query-engine-catalog-refresh-contract.md`, relevant cross-contract pointers, and `artifacts/2026-10-23_contract_decision.md`. Specify concurrency, failure/recovery, visible artifacts, state/input matrix and acceptance evidence.
3. Review: independent read-only reviewers assess correctness and security/operations. Primary author dispositions all findings; medium/high fixes require confirmation. Preserve review artifacts.
4. Handoff: lint changed docs, keep this plan and tracker current. Prepare checkpoint; do not commit or implement without authority. Required standalone ancestor remains pending.

## Concrete Steps

Use `rg`/AST inspection for direct and aliased calls, `git log` for precedent, and `wctl doc-lint --path <file>` for each changed document. Preview spelling with `diff -u <file> <(uk2us <file>)`. Reviews name the canonical draft and matrix explicitly. Read-only analysis is repeatable; do not enqueue maintenance on production.

## Validation and Acceptance

Every discovered producer and reader has a migration classification, a reason and required evidence. The contract covers absent, empty, populated, legacy, malformed, queued/running/failed and archive/restore states. No unresolved medium/high contract findings. Tests and production-equivalent execution are obligations for the later implementation, not claimed by this documentation phase.

## Idempotence and Recovery

Only scoped Markdown edits. Preserve user changes and generated docs index. Re-read final draft after review; no rollback of unrelated work. An uncommitted checkpoint cannot authorize implementation under the contract-first standard.

## Artifacts and Notes

Package tracker records reviewers, dispositions, validation, base revision and remaining ancestor gate. Normative rules live outside work packages.

## Interfaces and Dependencies

Existing Redis/RQ/scheduler only. Introduce an explicit asynchronous request interface; preserve synchronous `update_catalog_entry` return/error compatibility until callers are deliberately migrated. Concrete concurrency and reader guarantees belong in the canonical contract.

Revision note (2026-10-23 UTC): independent review strengthened reader freshness, receipt-free crash recovery, stable lifecycle coordination, worker eligibility and deterministic disclosure. These are implementation prerequisites, not new completion claims.

Completion note (2026-10-23 UTC): operator authorized checkpoint commit and execution scaffolding. Contract committed as `dc2b2ddbe8cfedbd4bae024310f03447ca813c32`; this completed plan is historical. Continue with `../active/implementation_execplan.md`; runtime work has not started.
