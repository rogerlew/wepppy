# Production M1 upload and execution

Status: scaffolded 2026-09-10 07:23 UTC; runtime implementation not started.
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
[ExecPlan](prompts/active/production_m1_execplan.md). UI copy/layout and state
behavior are concrete proposals for owner review, not approved by scaffolding.

Required contract-first ancestor before runtime edits: exact contract/state
matrix and operator approval, two independent reviews, affected canonical docs
and disposition committed separately. The current request authorizes scaffolding;
no runtime checkpoint, commit, installation or deployment is implied.

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
