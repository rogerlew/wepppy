# Malformed request side-effect repair (MRS-01)

Status: accepted contract checkpoint awaiting commit authority; implementation not started.
Started: 2026-10-30. Owner: operator; implementer: Codex.

## Objective and scope

Reject malformed requests before side effects, preserving intentional empty/default
requests. Repair both Flask and rq-engine parsing, confirmed direct/indirect
consumers, boolean truthiness, enclosing exception handlers and validation order.
The starting revision is `e35d7a3e69497ddfd9709736af50107f56963584`.
Operator authorization is the request to execute the retained repair prompt;
it explicitly authorizes equivalent confirmed consumers and tests, but withholds
independent commit authority. No implementation edits until the reviewed contract
checkpoint is committed as an ancestor.

## Execution and evidence

Execute [the active ExecPlan](prompts/active/repair_execplan.md).
[Tracker](tracker.md), [consumer matrix](artifacts/consumer-matrix.md),
[decision](artifacts/20261030_contract_decision.md), and
[canonical contract](../../schemas/request-payload-contract.md) define the work.
The copied [operator prompt](prompts/active/repair_request.md) preserves scope.
`artifacts/initial-status.txt` records unrelated Roads/research changes; preserve
those, including preexisting PROJECT_TRACKER changes. Ignore generated usersum
index changes. No branch changes, dependency installation, deployment or production
job submission. Historical WAM-01 package remains immutable.

## Complexity budget and security

Use shared classification/validation with framework adapters and bounded existing
upload parsers. No new services, dependencies, queues, privileges or artifact/data
schemas. No scientific default/formula changes; parameterization ADR not required
for this scope. Escalations require evidence and separate authority.
Security impact: **high**, because public mutation routes and uploads can change
or delete state on invalid input. Dedicated [security review](artifacts/20261030_security_review.md)
and independent correctness/QA review are required. Preserve auth/CSRF and valid
absent/empty/populated/legacy/busy/replay states; do not turn optional absence into
an error or change access policy.

## Acceptance and hardening

The read-only actual-HTTP parser probe reproduces `{`, `[]`, `null` and whitespace
becoming `{}` in both frameworks, and invalid clean text/arbitrary numbers
remaining truthy. Static consumers connect that fallback to RHEM default cleanup,
Flask mutation and submission, source promotion and completion timestamp clearing.
No destructive production reproduction is authorized or needed.

Closure requires every confirmed consumer repaired and traced to real route tests,
representative real NoDb reload/cache follow-up and filesystem sentinels, actual
multipart cleanup/promotion tests, WAM-01 preparation evidence, focused and broad
canonical gates, and all medium/high independent review findings closed. Persisted
state alone does not prove artifact correctness; read prepared inputs where that
boundary changes. Local conformance, deployment and incident resolution are separate.

Hypothesis: narrow validation before the first business mutation eliminates this
invalid-to-default class while retaining valid submissions. Health signals: safe
400s/no mutation, valid default/form/false requests succeed. Danger signals:
500/HTML responses, default work on invalid input, upload leaks, false rejection.
Use a recurrence-triggered observation model: retain local pre/post snapshots;
production snapshot is a separate rollout obligation and blocks production claims.
No temporary mitigation/callus is proposed. A recurrence opens a new package.

## Related work

[WAM-01](../20261030_wepp_admission_before_mutation/package.md) is historical
precedent for protecting proposed inputs under admission. Reuse its five-endpoint
regressions; do not weaken leases, replay or no-prep semantics. Current authority
is [WEPP input](../../schemas/wepp-run-input-contract.md),
[RQ response](../../schemas/rq-response-contract.md),
[webhooks](../../schemas/rq-webhook-contract.md),
[CSRF](../../schemas/weppcloud-csrf-contract.md), and the shared MRS-01 amendment.
