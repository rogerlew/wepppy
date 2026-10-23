# Implementation contract clarification checkpoint

Date: 2026-10-23 UTC. Scope: preserve established source selection and concurrent
Roads reads while retaining catalog publication and lifecycle fencing.

## Decisions and rationale

- An explicit permitted catalog `fs_path` remains authoritative without a matching
  producer receipt. Captured producer intent and recurring full reconciliation
  advance canonical child selection. Existing report redirection tests require
  this distinction; finding a child file alone does not prove newer authority.
- Ordinary Roads shared readers must remain concurrent. Holding the exclusive
  catalog guard throughout each read introduced false unavailable responses.
  Readers may take a short catalog barrier under Roads shared admission; writers
  retain catalog-before-Roads order and nonblocking exclusive admission. Archives
  use compatible shared admission. Blocking exclusive acquisition and lock
  upgrades remain forbidden, so this exception cannot create a blocking cycle.

The independent correctness and security reviewers approved these bounded
clarifications. Correctness verified the source-selection disposition; both
reviewers approved the Roads exception, and security independently reran four
concurrency/barrier cases. The lifecycle implementer reported 21 passing Roads
tests, including a concurrent-reader regression demonstrated failing before the
fix. Final implementation review artifacts retain the detailed dispositions.

## Checkpoint boundary

The two canonical contracts are committed separately from runtime changes.
The Roads working-tree patch was already prepared after reviewer agreement when
the checkpoint pause arrived; it remained uncommitted and undeployed. This
checkpoint precedes runtime integration commits and further evidence generation.
It does not authorize production deployment or project repair.

Canonical sections: query-engine refresh contract, **Publication and synchronous
coexistence** and **Reader freshness and caches**; Roads preparation lifecycle
contract, the guard-order paragraph following shared-reader admission.
