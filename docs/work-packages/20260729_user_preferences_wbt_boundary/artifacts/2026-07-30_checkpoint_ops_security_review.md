# Checkpoint Operations and Security Review

**Reviewer**: independent operations/security agent

**Reviewed revision**: `c820efd9137680b09321f5a5ef88e2cd8a78806e`

**Date**: 2026-07-30 UTC

**Verdict**: FAIL; implementation remains blocked pending amendment and
re-review.

## Findings

| ID | Severity | Finding | Required disposition |
| --- | --- | --- | --- |
| SEC-01 | High | Account identity and run ownership can currently fail open. | Restrict eligible identities, remove email fallback, snapshot in one DB context, require atomic ownership, compensate partial state, return generic errors, and add negative tests. |
| SEC-02 | High | “Every creation path” omitted HUC-fire and did not disposition other `Ron(...)` constructors. | Inventory every constructor, include regular/HUC-fire or narrow scope, and explicitly exclude batch/playback/tooling/internal paths. |
| SEC-03 | High | The documented enqueue-time typed response is not the asynchronous worker failure path; job tracebacks and dependent-job behavior were unresolved. | Define child/root/dependency/public-status behavior, sanitize the public surface, and test terminal failure, no abstraction, redaction, and retry. |
| OPS-04 | High | Alembic has two repository heads, contrary to the plan's single-head assumption. | Define a merge topology, test fresh/two-head paths, stop on Forest mismatch, use schema-first coordinated restart, set `FLASK_APP`, and prohibit destructive row-bearing downgrade without separate approval. |
| OPS-05 | Medium | Worker/direct/batch stale-state invalidation and retry were incomplete. | Define raster, timestamps, abstraction products, entrypoints, preflight, and error-to-success transitions. |
| SEC-06 | Medium | Concurrent preference insert/update semantics were ambiguous. | Define unique-key transaction recovery and last-write-wins or optimistic concurrency with tests. |

## Baseline Evidence

The reviewer reported both documentation lint targets and `git diff --check`
passing, plus 151 focused baseline tests. The baseline does not cover the
findings above.

No files were edited by the reviewer.
