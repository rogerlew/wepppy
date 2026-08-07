# Tracker - Run Statistics Ledger

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-05 20:26 UTC  
**Current phase**: Canonical-Parquet incident bridge checkpoint
**Last updated**: 2026-08-07 UTC
**Next milestone**: Ratify and implement bounded current-inventory reads
**Security impact**: `high` for SURF-19A
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/2026-08-07_checkpoint_ops_security_review.md`
**Incident owner**: Roger Lew; implementation owner: Codex
**Checkpoint state**: Dual post-fix review passed; standalone ancestor pending
**Sunset review**: Roger Lew records keep/reduce/remove at activation + 14 calendar days

## Task Board

### Ready / Backlog

- [ ] Implement Postgres statistics ledger writer/reader module with idempotent insert semantics.
- [ ] Implement deterministic backfill from dot files and legacy artifacts.
- [ ] Add WEPP hillslope runtime event hook.
- [ ] Add WATAR ash runtime event hook.
- [ ] Add TTL deletion audit-event hook (must not decrement historical totals).
- [ ] Generate canonical rollups and compatibility `runs_counter.json`.
- [ ] Update `/stats`, `/stats/<key>`, `/access-by-year`, and `/access-by-month` to Postgres-backed rollups.

### In Progress

- [ ] Replace per-run `.slp` and ash globs with canonical Parquet footer reads.
- [ ] Close dual checkpoint review and commit standalone ancestor.

### Blocked

- [ ] None.

### Done

- [x] Diagnosed production job `7aa39c98-de7c-4298-8d5f-35e3784775e4` timing out after 36,000 seconds in the per-run `.slp` glob (2026-08-07 UTC).
- [x] Recorded operator approval to use canonical Parquet counts without legacy parity (2026-08-07 UTC).

- [x] Removed unreliable reported statistics from the `/interfaces/` template in the current worktree before this package was created (2026-05-05 20:10 UTC).
- [x] Investigated wepp1 counter semantics and confirmed the old numbers came from active run-directory file counts plus a hard-coded post-2024 cutoff (2026-05-05 20:20 UTC).
- [x] Created package scaffold, specification, tracker, and active ExecPlan (2026-05-05 20:26 UTC).
- [x] Audited package and project-tracker docs for storage, endpoint, migration-scope, and validation consistency (2026-05-05 23:05 UTC).
- [x] Re-ran scoped package and project-tracker doc lint after the consistency edits (2026-05-05 23:06 UTC).

## Timeline

- **2026-08-07 UTC** - Ten-hour production timeout attributed to per-run `.slp` enumeration; canonical-Parquet incident bridge authorized.

- **2026-05-05 20:10 UTC** - Interface statistics removed from local implementation because current counters were misleading.
- **2026-05-05 20:20 UTC** - Current counter semantics documented from `compile_dot_logs.py` and wepp1 observations.
- **2026-05-05 20:26 UTC** - Work package and draft contract created.
- **2026-05-05 20:42 UTC** - Storage decision revised: Postgres source-of-truth ledger, Redis optional cache only. Stats endpoint inventory added to spec.
- **2026-05-05 23:05 UTC** - Documentation consistency audit aligned endpoint migration scope and validation tracking across package docs and `PROJECT_TRACKER.md`.

## Decisions Log

### 2026-08-07 UTC: Use canonical Parquet footers for active inventory

**Context**: NAS directory enumeration caused `compile_dot_logs_rq` to exhaust a ten-hour timeout.

**Decision**: Count rows from `watershed/hillslopes.parquet` and `ash/post/hillslope_annuals.parquet`; do not retain legacy file-scan fallbacks.

**Impact**: Output shapes stay stable, values intentionally change to bounded current canonical-artifact inventory, and the future ledger remains responsible for historical execution totals.

### 2026-05-05 20:26 UTC: Split active project inventory from historical execution counts

**Context**: The current counter generator scans active projects and current output files, so TTL deletion and repeated runs distort reported totals.

**Options considered**:
1. Continue scanning current run directories and adjust the globs.
2. Use only application database rows.
3. Add an append-only execution ledger and derive active inventory separately.

**Decision**: Use an append-only execution ledger for historical WEPP/WATAR counts and continue deriving active project counts from active project inventory.

**Impact**: Historical execution totals survive TTL deletion and repeated runs are counted correctly. Active project counts can still decrease when projects expire.

### 2026-05-05 20:26 UTC: Dot-file backfill must not fabricate repeated-run counts

**Context**: Dot access logs can prove project access history but cannot prove how many times hillslopes or WATAR ash were executed.

**Options considered**:
1. Treat one dot file as one model run.
2. Treat current file counts as exact historical counts.
3. Use dot files for project metadata only and label legacy artifact counts as minimum inferred counts.

**Decision**: Dot files backfill project metadata only. Existing artifacts may seed minimum inferred counts with source-quality labels, but unknown repeated-run history remains unknown.

**Impact**: Historical summaries become honest about source quality and avoid false precision.

### 2026-05-05 20:26 UTC: Keep legacy stats outputs during migration

**Context**: `/stats` still reads `runs_counter.json`, and external consumers may depend on existing keys.

**Options considered**:
1. Remove `runs_counter.json` immediately.
2. Replace it with a breaking schema.
3. Generate richer canonical outputs while preserving compatibility keys.

**Decision**: Preserve compatibility keys until a separate consumer migration retires them.

**Impact**: Implementation stays backward-compatible while allowing better internal summaries.

### 2026-05-05 20:42 UTC: Use Postgres for the durable ledger, not flat-file or Redis

**Context**: Concurrent writers across workers and maintenance jobs increase collision risk for flat-file append ledgers. Redis durability characteristics are better suited to caching/streaming in this stack than long-horizon audit history.

**Options considered**:
1. JSONL flat-file append ledger under `/geodata/weppcloud_runs`.
2. Redis as source-of-truth ledger.
3. PostgreSQL event table as source-of-truth with optional Redis cache layer.

**Decision**: Use PostgreSQL as source-of-truth event ledger. Keep Redis optional for summary caching only.

**Impact**: Stronger write consistency and idempotence guarantees through transactions and uniqueness constraints. Route migration can read from database rollups while maintaining compatibility outputs.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Runtime event writes slow WEPP or WATAR execution | Medium | Low | Use one short transaction per high-level completion event, not per-hillslope writes | Open |
| Ledger accidentally stores PII from dot files or users | High | Low | Contract forbids email, IP, owner id, and raw public exposure of events | Open |
| Backfill consumers mistake artifact-inferred counts for exact history | Medium | Medium | Include source-quality fields in canonical outputs and compatibility docs | Open |
| Compatibility counters change semantics unexpectedly | Medium | Medium | Preserve keys, document semantics, and add route tests | Open |
| Database migration or index design causes write latency | Medium | Medium | Keep schema narrow, add focused indexes only, benchmark insertion in targeted tests | Open |
| Zero discovery or correlated Parquet failures replace good public outputs | High | Low | Stage all outputs; apply zero-discovery, readable-watershed, and 10/25% per-artifact guards before publication | Open |
| Temporary guard or legacy keys outlive evidence/consumers | Medium | Medium | Roger Lew owns activation+14-day guard review; legacy keys require consumer inventory and separate migration | Open |

## Verification Checklist

### Documentation

- [x] Package overview created.
- [x] Normative spec created.
- [x] Active ExecPlan created.
- [x] Stats endpoint inventory documented in spec.
- [x] Endpoint migration scope documented across package, spec, tracker, ExecPlan, and `PROJECT_TRACKER.md`.
- [x] Package docs lint clean (2026-05-05 20:43 UTC).
- [x] `PROJECT_TRACKER.md` docs lint clean (2026-05-05 20:43 UTC).
- [x] Package docs lint clean after consistency audit (2026-05-05 23:06 UTC).
- [x] `PROJECT_TRACKER.md` docs lint clean after consistency audit (2026-05-05 23:06 UTC).
- [ ] Final implementation notes and closeout added.

### Code and Tests

- [ ] SURF-19A footer-only and ignored-legacy-file tests pass.
- [ ] Missing, corrupt, racing, warning, zero-discovery, and watershed/ash systemic-containment tests pass.
- [ ] Location, project aggregation, TTL, and all-output last-good tests pass.

- [ ] Ledger module unit tests pass.
- [ ] Backfill idempotence tests pass.
- [ ] WEPP hillslope repeated-run regression passes.
- [ ] WATAR strict-count regression passes.
- [ ] TTL deletion rollup regression passes.
- [ ] Existing stats route compatibility tests pass.

### Deployment

- [ ] Baseline recorded: 36,000-second timeout, zero completed output, failing job `7aa39c98-de7c-4298-8d5f-35e3784775e4`.
- [ ] Fenced production canary duration, readable/missing/error counts, guard state, and output totals recorded.
- [ ] Post-change signal: representative compiler completes below 36,000 seconds with no partial publication.
- [ ] Activation + 14 days: Roger Lew records guard keep/reduce/remove against trips, warnings, stable totals, and canary evidence.
- [ ] Legacy-key removal remains blocked until consumer inventory and a separately approved migration are complete.

- [ ] Dry-run backfill report reviewed on production-like data.
- [ ] Runtime append behavior observed after rollout.
- [ ] 14-day observation window documented.

## Progress Notes

### 2026-05-05 20:26 UTC: Package Scoping

**Agent/Contributor**: Codex

**Work completed**:
- Documented why the prior interface count was unreliable.
- Created the work-package scaffold and draft statistics contract.
- Created an active ExecPlan for implementation.

**Blockers encountered**:
- None.

**Next steps**:
- Implement the ledger module first, because runtime hooks and backfill both depend on that contract.
- Add tests before wiring runtime paths so repeated-run and idempotence semantics are locked down.

**Test results**: Documentation-only package creation; doc lint pending.

### 2026-05-05 20:42 UTC: Storage and Endpoint Revision

**Agent/Contributor**: Codex

**Work completed**:
- Recorded a storage decision to use Postgres as the durable event ledger.
- Added explicit stats endpoint inventory and migration scope to the spec.
- Updated task board and risks to include route migration and database-write concerns.

**Blockers encountered**:
- None.

**Next steps**:
- Implement Postgres event schema and writer with unique-id idempotence.
- Add route tests for `/stats`, `/stats/<key>`, `/access-by-year`, `/access-by-month` before migrating data sources.

**Test results**: Documentation edits only; doc lint pending for revised files.

### 2026-05-05 20:43 UTC: Documentation Validation

**Agent/Contributor**: Codex

**Work completed**:
- Ran `wctl doc-lint --path docs/work-packages/20260505_run_statistics_ledger`.
- Ran `wctl doc-lint --path PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
- Begin implementation against the Postgres ledger contract.

**Test results**: Doc lint clean (`4 files validated` for package; `1 file validated` for project tracker).

### 2026-05-05 23:05 UTC: Documentation Consistency Audit

**Agent/Contributor**: Codex

**Work completed**:
- Aligned top-level tracker scope with the four endpoint response shapes that will migrate to ledger-backed rollups.
- Clarified that `/getloadavg` is inventoried but remains outside the ledger migration.
- Confirmed the storage decision remains PostgreSQL source-of-truth with Redis limited to optional summary caching/materialization.

**Blockers encountered**:
- None.

**Next steps**:
- Begin implementation against the PostgreSQL ledger contract.

**Test results**: Doc lint clean (`4 files validated` for package; `1 file validated` for project tracker).

## Watch List

- **Legacy `runs_counter.json` consumers**: `/stats` still serves this file, so compatibility must be maintained until route consumers are audited.
- **Production event volume**: The selected design appends once per completed invocation, which should keep event volume low. Validate this in production observation.
