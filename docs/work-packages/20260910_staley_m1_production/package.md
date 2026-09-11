# Production M1 upload and execution

Status: completed 2026-09-10; ExecPlan archived.
Baseline `304572530`. User requests NoDb state, prerequisites/freshness, dNBR
upload/publication and RQ execution with a simple control. Reports are deferred.

## User outcome

On an eligible prepared WBT project, including the owner's planned 10 m test
project, upload dNBR, see that it is ready, run Staley M1 and inspect completed
model files. A reload preserves status and accepted inputs. Failed replacement
or run never destroys prior successful output. The control uses familiar
watershed, soil burn severity, soil erodibility and rainfall terminology.

## Contracts and execution gate

Review the [UI contract](../../../docs/ui-docs/contracts/postfire-debris-flow-control-contract.md),
[workflow contract](../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m1.md),
[decision register](artifacts/decision_register.md), [tracker](tracker.md) and
[ExecPlan](prompts/completed/production_m1_execplan.md). UI copy/layout and state
behavior are accepted through owner execution authorization and the contract checkpoint.

Contract-first ancestors `5c0a172ee` and `595816476` contain the accepted
contract/state matrix, owner authorization and independent reviews before runtime
edits. Runtime changes remain uncommitted; no production deployment occurred.
See [validation](artifacts/validation.md), [correctness review](artifacts/correctness_review.md)
and [security review](artifacts/security_review.md).

## Scope and acceptance

New additive NoDb facade, owner-artifact readiness, immutable upload/run artifacts,
authorized CSRF-protected rq-engine boundaries, workers and minimal Pure UI
control. Reuse local scientific libraries and existing feature/job infrastructure.
No report/template charts or probability tables, interactive dashboard, M3,
upstream builds, new catchment selection or public result-query endpoint.

Security impact: high. Independent correctness, security and UI behavior reviews;
resolve all medium/high findings and verify valid-state noninterference. Require
actual end-to-end web/worker tests with real files/permissions/status reload,
RQ graph/catalog checks and target WBT capability preflight. Test developer/local
readiness separately from approved target installation and operator smoke test.
Unrelated quality-report changes must be preserved.
