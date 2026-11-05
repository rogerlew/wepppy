# Notification design security review

Reviewer: independent `notification_security_review` agent (security_reviewer role).
Date: 2026-11-05 UTC. Starting revision: `5fb446744d1e5d0e193c3d3aa2cf2dc040e22823`.
Scope: proposed notification contract/package/ExecPlan against auth, CSRF, worker
and deployment contracts. Read-only; no runtime tests or edits by reviewer.
Primary agent retained the report from the independent response.

## Security triage and threat model

Impact high; dedicated final security review required. Threats include cross-user
content disclosure, forged/oversize bulk updates, revoked project access, unsafe
rendering, duplicate/replayed tasks and preflight affecting real users. Controls
must preserve empty/legacy states and legitimate read/unread operations. See
[correctness review](20261105_correctness_review.md) for valid-state scope.

## Findings

| ID | Severity | Surface | Finding and required action | Disposition |
| --- | --- | --- | --- | --- |
| SEC-01 | Medium | CSRF/API | Preserve existing global JSON 400 `csrf_failed` before route auth; do not add exemptions or change global handler to satisfy draft 403/401 | Closed by independent recheck |
| SEC-02 | Medium | Deployment/worker | Migrate before real preflight; explicit default-off schedule and trusted fixture scope across both creation and reconciliation; prove no non-fixture state changed | Closed by independent recheck |

## Surface checks and evidence

Positive design controls: recipient scoping/current membership, no admin expansion,
atomic mixed-ID rejection, private/no-store responses, plain-text rendering and
trusted links, read-only TTL, unchanged GC, unique rows and overlap lock, preserved
read state, explicit forest identity/mount parity, no Redis flush or production
rollout. These are contract obligations, not proven implementation properties.

No new secrets, external egress, dependencies or privilege expansion is planned.
Account inbox data is visible only through its authorized listing; new project
archive artifacts are N/A. Actual security boundary checks, job tree, database
transactions and browser evidence must be recorded in final implementation review.

## Verdict and residual obligations

Initial verdict: changes requested; two medium, zero high findings. Final design
verdict: pass; independent reviewer confirmed both findings closed on 2026-11-05
UTC, with no unresolved medium/high findings. Added reviewer regression obligation:
an explicitly empty fixture scope must be a no-op, never an unrestricted sweep.
No implementation/deployment
approval. Implementation must prove membership changes cannot leak content,
mixed-ownership requests are atomic, content cannot inject markup, fixture scope
cannot affect other subjects, and schedule rollback handles already queued jobs.
No residual risk is accepted on behalf of the operator.
