# Checkpoint Review Disposition

**Status**: PASS; all initial and re-review findings closed

**Date**: 2026-07-30 UTC

## Disposition

| Finding | Disposition | Contract amendment |
| --- | --- | --- |
| GOV-01 | Accepted-fixed | The execution instruction is retained as approval of the complete documented delta in the decision artifact, package, ExecPlan, and ADR. |
| GOV-02 | Accepted-fixed | SURF-01, SURF-04, SURF-14, SHR-05, DOM-02, DOM-05, and DOM-05A are named and cross-linked; DOM-05 is corrected to closed. |
| GOV-03 | Accepted-fixed | `_wbt_boundary_touch_behavior` is the exact persisted field; missing legacy state hydrates to `warn` and is stable across archive/restore/fork/config change. |
| GOV-04 / OPS-05 | Accepted-fixed | The decision defines entrypoint-wide timestamp/raster/edge-ID invalidation, exact warn/error channels, dependent readiness, and retry restoration. |
| GOV-05 | Accepted-fixed | Forest is schema-first with exact discovery, backup/restore, restart, abort, cleanup, rollback, and post-action-audit gates. |
| GOV-06 / SEC-06 | Accepted-fixed | Complete-form last-committed-write-wins, row locking, one bounded unique-insert retry, and deterministic concurrency tests are required. |
| GOV-07 / SEC-02 | Accepted-fixed | The regular and HUC-fire paths are included; every other production/tool/test `Ron(...)` constructor is explicitly dispositioned, and the precedence table is finite. |
| GOV-08 | Accepted-fixed | Disposable PostgreSQL, exact migration topology, canonical preference failure, and warning channels are mandatory evidence. |
| SEC-01 | Accepted-fixed | Only user/cookie identities resolve preferences; subject binding, active user, atomic owner association, compensating cleanup, generic `error_id`, and negative tests are exact. |
| SEC-03 | Accepted-fixed | The real child/root dependency lifecycle and sanitized public status surface replace the incorrect enqueue-time response claim. |
| OPS-04 | Accepted-fixed | The preference migration merges heads `7b3c068e7a1d` and `b7d9c3e2f1a4`; fresh/two-head tests and schema-first Forest commands are exact. |

Implementation remains blocked until both original reviewers confirm that these
amendments close their findings, the ADR is Accepted, and the reviewed
documentation-only checkpoint is committed as a standalone ancestor.

## First Re-review Disposition

The governance re-review closed GOV-01/03/04/05/06 and retained GOV-02/07/08.
The operations/security re-review closed SEC-01/02, OPS-05, and SEC-06 and
retained SEC-03/OPS-04. Those remaining findings are accepted-fixed:

- DOM-05's canonical field matrix now records DOM-05A complete and cross-links
  the bounded SURF-14A policy; the package header names DOM-05A.
- Independent unit and boundary tables require the full successful Cartesian
  product and exact invalid-explicit/persisted failure rows.
- The warning literal, edge-ID serialization, StatusMessenger event, job tree
  states, jobinfo endpoint/payload/code/error ID, redaction, and diagnostic
  path are exact; `docs/schemas/rq-response-contract.md` is amended.
- Forest commands use exact target/repository/project/file/services. The four
  bind-mounted consumers stop before the checkout changes; migration runs in a
  one-off container and they remain stopped on failure.

A second re-review is required before ratification.

## Second Re-review Disposition

Governance passed with GOV-02/07/08 closed. Operations/security closed SEC-03
but retained OPS-04 because workers were not drained and a fresh backup command
was absent. OPS-04 is accepted-fixed:

- a secure one-off `pg_dump -Fc` command uses the mounted secret without
  exposing it, writes atomically, checks `PGDMP`, runs `pg_restore -l`, and
  records the exact path;
- WEPPcloud, rq-engine, and scheduler stop before queue drain;
- `wctl rq-info --raw` must prove both queues zero and all workers idle;
- workers receive a 30-minute graceful stop, followed by an independent
  post-stop registry check from a one-off container; and
- checkout/migration/start remain blocked until all drain, User-count, and
  exact named-constraint assertions pass.

The final operations/security confirmation passed OPS-04 with no residual
blocker. Governance and operations/security both approve this documentation
for the standalone pre-implementation ancestor.
