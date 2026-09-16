# Post-fire debris-flow report design and implementation planning

Status: Closed, documentation and review delivered (2026-09-15). Timezone: UTC.

## Overview and objectives

Document an intuitive, familiar report for existing M1/M3 outputs before writing
its UI. Deliver (1) the report contract, (2) module specification/roadmap links,
and (3) a staged implementation plan with field/state coverage and independent
correctness, security and dedicated end-user UX review.

## Scope and authority

Owner request: “carry out 1-3 as a work-package with agent review. add a dedicated
user-experience review agent that advocates for good UX that isn't overcomplicated
and is intuitive to human end-users.” This authorizes documentation and agent
review. It does not ratify every proposed control or authorize report code,
live model reruns, deployment, source acquisition, commits or pushes.

The [report contract](../../ui-docs/contracts/postfire-debris-flow-report-contract.md)
is the proposed durable design, not evidence of deployed behavior. The existing
scientific contracts remain unchanged. This package can close as a reviewed
documentation deliverable without claiming implementation or owner ratification.

## Complexity budget

Reuse Pure report shell, Unitizer, saved result readers, event IDs and existing
project artifact browsing. New runtime mechanisms permitted: none in this phase.
The future smallest implementation is saved scenarios/thresholds and paginated
events. No queues, services, storage, dependencies, privileges, scientific
heuristics, continuous curve, maps, or advanced controls are authorized here.
Escalation requires a documented failed acceptance condition and owner approval.

## Stakeholders and review gate

Owner: requesting WEPPcloud operator. Primary author: root agent. Independent
reviewers: correctness/contract, security/containment, and dedicated UX advocate.
The reusable role is [.codex/agents/ux_reviewer.toml](../../../.codex/agents/ux_reviewer.toml),
registered in [.codex/config.toml](../../../.codex/config.toml), with a retained
[package review brief](prompts/completed/ux_review.md), and
must advocate for human comprehension and fewer controls, not visual novelty.
Review agents read independently; the author records dispositions and obtains
confirmation after medium/high fixes. No reviewer can approve owner design intent.

Security impact: **low**, documentation and read-only review-role registration,
no changed application attack surface.
A dedicated security review is included voluntarily for the proposed read boundary;
runtime security approval must be repeated against actual implementation.
Future browser/query/download implementation is high-impact by default and must
be re-triaged explicitly, with a dedicated security review of code and evidence.
The only non-Markdown changes register that requested read-only review role;
they do not alter model choice, permissions, thread limits or production behavior.
Parameterization change: **no**; no ADR required. Proposed display formatting and
initial duration do not modify scientific formulas, coefficients or targets.

## Success criteria

- [x] Proposed contract distinguishes accepted science from pending report design.
- [x] Module specification and roadmap link the report and preserve data authority.
- [x] Field/state matrix and actionable future test/live acceptance plan exist.
- [x] Three independent reviews are retained and all findings resolved.
- [x] Documentation lint, spelling preview and diff checks pass; see validation artifact.

## Deliverables and references

- [Tracker](tracker.md) and [documentation ExecPlan](prompts/completed/report_design_execplan.md).
- [Implementation plan](artifacts/implementation_plan.md).
- [Field and state matrix](artifacts/field_matrix.md).
- [Contract decision record](artifacts/20260915_contract_decision.md).
- Review records and disposition under `artifacts/`.

Historical precedents are the closed
[Geneva interactive summary package](../20260418_geneva_interactive_summary_report/package.md)
and [Geneva contract verification](../20260728_pure_ui_geneva_summary_report_contract/package.md).
Do not reopen them or either closed Staley integration/remediation package.

## Follow-up boundary

Report implementation remains pending owner ratification of the proposed design,
complete adapter/route/feature-discovery contracts, and a separately committed
reviewed contract checkpoint. Neither document completion nor agent approval
substitutes for that implementation gate.

## Closure notes

Closed 2026-09-15 21:56 UTC. Delivered the reviewed proposal, module links,
implementation handoff, field/state matrix, decision/review records, and requested
reusable UX role. The [review disposition](artifacts/review_disposition.md) records
all corrections and independent confirmations. [Validation](artifacts/validation.md)
records the documentation/configuration checks and evidence limits.

No report implementation, live rerun, schema/science change, commit, push or
deployment occurred. The useful lesson was to make simplicity review independent:
fixed chart scale, visible window labels and inline event details improved the
design without adding controls. The technical review also exposed the exact
saved-table reader extension needed before implementation.
