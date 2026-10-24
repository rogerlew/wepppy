# Review and disposition the Roads dashboard contract

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Produce a reviewable, internally consistent specification for road-centerline
detachment and an in-dashboard Baseline/Roads switch. The user approved the proposed
choices and requested independent review and disposition, not runtime execution.

## Progress

- [x] 2026-10-24 05:32 UTC: Accepted choices and starting revision recorded.
- [x] 2026-10-24 05:32 UTC: Independent correctness, security and UX reviews dispatched.
- [x] 2026-10-24 UTC: Canonical contracts and ADR amended for nine findings.
- [x] 2026-10-24 UTC: Independent correctness/security/UX post-fix confirmations retained.
- [x] 2026-10-24 UTC: Documentation checks passed; prepared checkpoint handed off uncommitted.

## Surprises & Discoveries

The initial scope-switch wording contradicted the upstream continuous-mode
mandatory summary requirement. Scope and overlay availability can differ only
within a result set that satisfies the existing lifecycle contract.

## Decision Log

2026-10-24 05:32 UTC: retain model outputs and existing lifecycle as authoritative
inputs; this feature adds display and navigation only. Reviewers inspect but do
not edit canonical documents, so authors cannot approve their own corrections.

## Outcomes & Retrospective

Review complete: four correctness, three security and two UX findings closed.
The important corrections preserve mandatory resource admission, coherent reads,
effective CRS, literal labels, independent errors and scope/graph transitions.
One extra payload correction preserves per-profile length semantics. No runtime
implementation, commit, deployment or repair. Commit the standalone checkpoint
only when authorized, then execute a separately prepared implementation plan.

## Context and Orientation

Canonical behavior lives in `docs/schemas/roads-gl-dashboard-contract.md`, with
scope navigation in `docs/schemas/output-scope-contract.md`. Upstream segment
summary and preparation lifecycle contracts govern units and current eligibility.
ADR-0105 records the display aggregation and scaling policy. Runtime source
anchors are `wepppy/weppcloud/routes/gl_dashboard.py`, `templates/gl_dashboard.htm`
under the same package, and `static/js/gl-dashboard/` modules. Existing summary
artifacts at `/wc1/runs/cl/clogging-starch` may be inspected, never rewritten here.

## Plan of Work

First record operator intent, scope, authority and a valid-state/input matrix in
the decision artifact. Reviewers compare these against canonical contracts and
actual consumer/producer boundaries. The parent reconciles findings in the
canonical documents and ADR, maintaining a per-finding disposition. Reviewers
then independently confirm the revised text before the prepared checkpoint is
called reviewed. No code or project-data edits are required for this outcome.

## Concrete Steps and Validation

From `/home/workdir/wepppy`, inspect the applicable contracts and source anchors,
then run `wctl doc-lint --path` for each changed canonical document, ADR, UI guide
and this package. Preview spelling with `uk2us`; run `git diff --check`. Retain
reviewed file hashes. No model or runtime tests are claimed for a documentation
review. Future implementation requires direct producer-to-browser validation.

## Idempotence and Recovery

Preserve unrelated dirty files and generated Usersum index. No branch switches,
project mutations, hidden data copies or operational actions. Historical review
findings remain visible when resolved. Checkpoint commit remains a separate
authorized action; approval of specification alone is not runtime conformance.

## Artifacts and Acceptance

Retain `correctness_review.md`, `security_review.md`, `ux_review.md` and
`review_disposition.md` under artifacts. Complete this review when all findings
are dispositioned and independent reviewers confirm closure; keep implementation
acceptance explicitly pending. Update this plan and tracker before handoff.

2026-10-24 revision note: marked review complete after independent closure;
runtime acceptance and the uncommitted ancestor checkpoint remain separate gates.

