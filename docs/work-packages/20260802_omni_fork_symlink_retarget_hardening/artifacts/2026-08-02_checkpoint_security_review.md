# Checkpoint Security Review

**Reviewer**: independent checkpoint security reviewer
**Date**: 2026-08-02 UTC
**Initial verdict**: not safe to ancestor-commit

## Findings

- **High**: lexical containment did not close symlinked/swapped-parent races;
  require descriptor-relative no-follow operations and adversarial tests.
- **High**: root role target existence/type/resolved containment was undefined.
- **Medium**: require preflight, exclusive temp creation, cleanup, rollback, and
  fresh-destination recovery.
- **Medium**: immediate child name/type rules were undefined.
- **Medium**: pending behavior was written as current behavior.
- **Medium**: add old-target non-access, parent-race, temp-residue, root-role,
  rsync, and materialized-entry tests.
- **Medium**: add exact incident signature, hypothesis, latency guardrails,
  timeline, risks/owners, and callus statement.

No files were edited by the reviewer.

## Post-Fix Confirmation

Approved for standalone ancestor commit with no unresolved high or medium
finding. Final implementation review must prove descriptor-relative parent-race
defense, rollback, cleanup, and preservation of foreign sentinels.
