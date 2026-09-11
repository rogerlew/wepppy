# Staley M1/M3 UI and RQ wiring

Status: closed 2026-09-11 UTC. Starting revision 29a18e00f.
Owner: repository user. Implementer: Codex.

Deliver the existing postfire control with header comparison, M1/M3 radios,
conditional prerequisites/dNBR fields, model-aware durable state and real
rq-engine dispatch to dedicated M1/M3 tasks. M3 scientific composition follows;
the wired M3 task explicitly fails integration_pending until then. It must not
be disabled solely because integration is pending and never reports fake success.
This is scaffold/task-boundary scope, not completed scientific integration.

The current [selection contract](../../../wepppy/nodb/mods/postfire_debris_flow/docs/model_selection.md)
is the durable authority linked by the domain specification. The archived
[ExecPlan](prompts/completed/execplan.md) records execution. ADR-0066 records the
owner's valid-support numerical direction for the following scientific milestone.

Compatibility: preserve run-m1 endpoint, legacy M1 attempts/results, published
file locations, masks and all historical records. Add model selection/identity;
no result relabeling, automatic reruns or data migration. Old M1 source snapshots
may become stale after the dependency contract changes; preserve their files.
No scientific coefficient or raster reduction changes in this package.

Security impact: high (authenticated model dispatch/state/freshness boundaries).
Two independent read-only contract reviews and a standalone accepted checkpoint
commit precede implementation. Dedicated final correctness/security evidence and
real development browser/worker validation are required. No production deployment.
Complexity budget: existing services, queue, NoDb facade and UI macros only;
no dependencies, workers, infrastructure or feature-registry redesign.

Exit: browser selection reaches the correct tracked task, M1 still calculates
through its current engine, M3 explicitly reports pending integration with
persistent job/error records, invalid model requests fail before admission,
model-specific freshness works and existing result files remain inspectable.
Full M3 scientific delivery remains open in roadmap stage 6; this package cannot
claim it complete. Reports remain deferred.


Preflight scope: amend module preflight.py and Go checklist projection with the
canonical production_m1.md “Preflight completion task” policy. 🌋 reflects the
latest accepted result's own model/frequency; selection alone never invalidates
it. Validate both relevant and unrelated model dependency changes with Python
and `wctl run-preflight-tests` Go tests, plus actual development stream readback.

Delivered and validated on the development stack after checkpoint aa30e637e.
[Validation](artifacts/validation.md): full Python 8,468 passed, 103 skipped,
frontend 872 passed, live M1/M3 task dispatch and reload, real Redis contention,
recorder-enabled selection recovery, downloads and preflight.
[Correctness review](artifacts/implementation_reviews.md) and
[security review](artifacts/security_review.md) passed. M3 scientific integration
and valid-support calculations are the explicit successor scope.
