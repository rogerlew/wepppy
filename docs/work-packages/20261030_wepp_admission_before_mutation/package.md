# WEPP admission before mutation

Status: implemented and locally validated; review-ready, 2026-10-30 UTC.
Full gate: 12,210 passed, 334 skipped. No deployment.
Remediation ID: WAM-01. Owner: operator / Codex.

## Outcome and scope

A rejected WEPP execution submission must not persist proposed input changes
that already-admitted preparation can consume. Preserve configuration-only
batch/base saves. Starting branch `master`, revision
`29716c1bd9a24dacf1cb45e05a11b2aa44a5378e`; initial dirty paths are retained in
[initial status](artifacts/initial-status.txt). Preserve unrelated Roads work and
ignore the dirty generated usersum index.

The three `wepp_routes.py` endpoints and two `bootstrap_routes.py` WEPP no-prep
endpoints apply payload before active-work admission. This is static evidence,
not runtime confirmation of mixed scientific results. Scope includes those five
consumers, their regression tests, and proportionate docs. No worker rewrite,
queue wiring, parameterization, schema change, dependency, deployment, production
submission or branch change. No singleton rollback, malformed-body or RedisPrep
snapshot redesign. Complexity budget: move existing input application into the
existing admission critical section, with a small shared helper only if necessary
to preserve errors. No new infrastructure.

## Governance

The current response contract forbids duplicate enqueue but does not explicitly
forbid pre-admission input persistence. WAM-01 adds normative intent, so the
[contract-first checkpoint](../../standards/contract-first-change-standard.md#required-pre-implementation-checkpoint)
applies. The [operator prompt](artifacts/operator-prompt.md) approves the bounded
outcome and confirmed-consumer assessment, but explicitly does not grant commit
authority initially. The operator subsequently granted that authority; two
independent reviews and disposition preceded checkpoint `525e78c9f`, and all
implementation/test edits followed it.

Security impact: low. Existing auth/access, callback destination policy,
ownership and isolation remain unchanged; the patch reduces mutation by rejected
authorized requests. Dedicated high-impact security artifact is not required.
Independent reviews must assess containment and valid-state noninterference.

## Acceptance and risks

All cases in the retained prompt are required: active root/child, busy lease,
controlled competing requests, successful identity/persistence, batch/base,
webhook replay/new submission, admitted failures, deferred recovery and lifecycle
exclusion. Tests must exercise real NoDb reload and real lease coordination.
Accept A, reject B, prepare a real disposable fixture and parse A's value in the
exact `wepp/runs/` input; no claim about native outputs without a model run.
No-prep tests additionally prove prepared files remain byte-identical. Record
existing browse/download/archive/restore evidence for retained artifact paths.
No new format or visibility exception is authorized.

Compatibility plan: no keys, columns, defaults or formulas change. Move mutation
ordering only; retain parser semantics and error translation. Admission conflicts
can take precedence over invalid payload errors. Failures after application begins
do not gain rollback guarantees. Longer lease duration and NoDb lock order must
be assessed and tested; existing renewal remains in use.

## Precedent and observation

Reuse `20260821_deferred_job_retry_recovery` as historical evidence for conditional
deferred cancellation; current authority remains the response contract. Reuse
`20261027_rq_webhooks` replay/publication boundaries without changing callback
semantics. Unlike those efforts, this correction changes payload placement only.

Health signal: rejected submissions preserve durable fields and active receipts.
Danger signals: altered preparation inputs after rejection, failed valid batch
saves, duplicate enqueue, deadlock or lease loss. No temporary mitigation is
introduced. Production observation is outside this no-deploy task; future rollout
must retain a pre/post snapshot and recurrence must open a new assessment.

See [decision](artifacts/20261030_contract_decision.md),
[assessment](artifacts/assessment.md), [tracker](tracker.md) and
[ExecPlan](prompts/active/implementation_execplan.md).
