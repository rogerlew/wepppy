# Preserve project configuration through lifecycle operations

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, users can fork, archive, download, and restore a flattened
project without receiving a torn config/manifest pair. If an update stopped
between replacements, lifecycle operations first recover it under the same
project amendment lock. Legacy archives still reopen through shared fallback,
and invalid or newer manifests retain the reader's nonblocking degraded mode.

## Progress

- [x] (2026-08-26) Read the contract, roadmap, WP08 recovery code, and lifecycle paths.
- [x] (2026-08-26) Scaffold WP10 with compatibility and security scope.
- [x] (2026-08-26) Implement reusable lifecycle guard and wire fork/archive/restore.
- [x] (2026-08-26) Add lifecycle and authorization-adjacent regression evidence.
- [x] (2026-08-26) Run gates, review, archive, close, and commit.

## Surprises & Discoveries

- Observation: archive logic already excludes only `archives/`; without WP10 it
  can copy `.config-amendment.pending.json` and does not coordinate with the
  amendment lock.
  Evidence: `wepppy/rq/project_rq_archive.py` walks the run root directly.
- Observation: the RQ dependency graph records enqueue source lines, so the
  lifecycle guard's source shift required regenerating graph artifacts even
  though no dependency edge changed.
  Evidence: `wctl check-rq-graph` reported drift and passed after the canonical
  `--write` regeneration.

## Decision Log

- Decision: expose a context-managed lifecycle guard from WP08's update module.
  Rationale: fork/archive/restore must share the exact lock and recovery logic,
  while callers must retain the lock across their entire copy or replacement
  window.
  Date/Author: 2026-08-26, Codex.

## Outcomes & Retrospective

Delivered one shared amendment/recovery boundary across fork, archive, and
restore. Transaction-only files are excluded, restore preserves the active lock
inode, and composite identities coordinate with top-level authority. Exact-byte,
recovery, concurrency, legacy, degraded-manifest, secret-scan, authorization-
adjacent, stub, isolation, documentation, RQ graph, and full-suite gates pass.

## Context and Orientation

`wepppy/nodb/project_config_update.py` owns the amendment lock, pending journal,
and deterministic recovery. `wepppy/rq/project_rq.py` orchestrates forks and
adapts archive helpers. `wepppy/rq/project_rq_archive.py` creates and restores
ZIP archives. A flattened config is a project-root `.cfg` paired with
`config-manifest.json`; an Omni child inherits that pair from its top-level run.

## Plan of Work

Expose a context manager that acquires the existing amendment lock, recovers a
pending transaction when present, and holds the lock until lifecycle copying
finishes. Wire it around fork source copying and archive creation. Wire restore
under the same lock so an update cannot race destructive replacement. Exclude
the pending journal from ZIP members and ignore it when restoring older
archives, because a journal is transaction machinery rather than project data.

Add focused fixtures that synthesize prior/result pairs and pause lifecycle
copying to prove mutual exclusion. Inspect fork and ZIP outputs byte-for-byte.
Restore owned, legacy, malformed-manifest, and newer-manifest archives and load
them through the canonical reader. Retain existing route authorization as the
read-only/public mutation boundary and add focused regressions if coverage is
not already direct.

## Concrete Steps

Work from `/home/workdir/wepppy`. Run focused tests with `wctl run-pytest` after
each lifecycle integration, then run stub, isolation, archive/fork suites,
documentation lint, broad-exception enforcement, and `wctl run-pytest tests
--maxfail=1` before closure.

## Validation and Acceptance

Tests must observe identical config and manifest bytes after fork and
archive/restore, deterministic recovery before copying, no pending journal in
new or restored project state, top-level authority for composite run IDs,
legacy fallback after restore, and degraded loading with updates disabled for
invalid/newer manifests. Existing fork/archive tests must remain green.

## Idempotence and Recovery

The lifecycle guard is safe to enter repeatedly. Recovery removes a journal
only after the pair matches a recorded prior/result state or after completing
the deterministic replacement. Failed archive temporary files retain existing
cleanup. Restore validation still occurs before removing current project data.

## Artifacts and Notes

Store security review and validation transcripts under `artifacts/`.

## Interfaces and Dependencies

No dependency is added. The public NoDb interface is a context manager yielding
after recovery while holding the existing `fcntl` amendment lock. Archive
helpers receive it through `ArchiveRuntime` so the helper remains testable.

Plan revision note (2026-08-26): initial executable plan.

Plan revision note (2026-08-26): recorded completed lifecycle integration,
validation evidence, generated-graph discovery, and closure outcome.
