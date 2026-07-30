# Checkpoint Governance Review

**Reviewer**: independent governance/correctness agent

**Reviewed revision**: `c820efd9137680b09321f5a5ef88e2cd8a78806e`

**Date**: 2026-07-30 UTC

**Verdict**: FAIL; implementation remains blocked pending amendment and
re-review.

## Findings

| ID | Severity | Finding | Required disposition |
| --- | --- | --- | --- |
| GOV-01 | Blocking | Durable operator approval covered the label, scaffold, and Forest migration but did not attribute the complete normative delta consistently. | Record approval or pending authority for storage, enums, precedence, compatibility, defaults, failures, and canary; reconcile all provenance. |
| GOV-02 | Blocking | SURF-01, SURF-04, DOM-02, and affected canonical owner records were omitted or not amended; DOM-05 status was stale. | Add owners/dependencies, cross-link bounded amendments, distinguish SHR-05/DOM-05A, and correct DOM-05. |
| GOV-03 | High | Legacy Watershed state did not define hydration of the new field. | Name the field and define missing-state, archive/restore, fork, and later-config behavior. |
| GOV-04 | High | WBT error cleanup and rerun semantics were not exact. | Define canonical raster, timestamps, edge IDs, warning channel, preflight, and retry transitions. |
| GOV-05 | High | Forest staging lacked a compatibility matrix and contained target/backup/restart/abort/post-audit controls. | Select a safe rollout order and define all operational evidence and stop points. |
| GOV-06 | Medium | Concurrent first-save and stale complete-form semantics were undefined. | Select concurrency semantics, collision recovery, and deterministic tests. |
| GOV-07 | Medium | Creation paths and precedence cases were not finite. | Enumerate entry points, identity/operation cases, and a complete truth table. |
| GOV-08 | Medium | Migration evidence did not require PostgreSQL or exact error/warning contracts. | Require disposable PostgreSQL, generated revision identity, canonical failures, and exact warning publication. |

## Positive Controls

The reviewed revision is documentation-only and directly follows the recorded
starting revision. The feature is correctly classified as intended behavior,
ADR-0033 precedes implementation, production authority is excluded, and the
rollback intent preserves additive preference rows.

No files were edited by the reviewer.
