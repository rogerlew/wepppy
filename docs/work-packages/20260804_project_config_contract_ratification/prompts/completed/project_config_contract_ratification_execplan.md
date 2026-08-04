# Ratify and inventory the project-owned configuration contract

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be maintained
as execution proceeds. Maintain this plan according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package turns a reviewed design into an implementation-authorizing
checkpoint without claiming that runtime behavior exists. When complete, a
stateless implementation agent can open the contract, roadmap, and normative
checklist and determine exactly which work package owns every requirement,
which evidence closes it, and which branch must contain the work.

The observable result is a closed WP00R package, ratified feature-branch status
in the contract and roadmap, a complete checklist with no unmapped normative
clause, passing documentation gates, and explicit authorization for WP00A,
WP00B, and WP01 to begin.

## Progress

- [x] (2026-08-04 23:33 UTC) Verified
  `feature/project-owned-config` and matching upstream at `87193bc35`.
- [x] (2026-08-04 23:33 UTC) Read package, ExecPlan, and security-review
  instructions.
- [x] (2026-08-04 23:33 UTC) Scaffolded package, tracker, active plan, and
  review artifact locations.
- [x] (2026-08-04 23:33 UTC) Generated 107 mandatory, 54 regression, and three
  advisory checklist entries.
- [x] (2026-08-04 23:33 UTC) Reconciled all 164 entries with a PC owner and
  downstream task; no orphan or duplicate task ID remains.
- [x] (2026-08-04 23:33 UTC) Completed governance and security reviews; all
  findings are resolved and both gates pass.
- [x] (2026-08-04 23:33 UTC) Ratified contract/roadmap status and closed
  package/tracker/plan.
- [x] (2026-08-04 23:33 UTC) Ran documentation and consistency gates.

## Surprises & Discoveries

- Observation: The mandatory inventory contains 107 paragraph/list groups, but
  three additional paragraphs contain only `SHOULD`/`MAY`.
  Evidence: Those clauses are now A-001 through A-003, bringing the complete
  downstream disposition ledger to 164 entries.

## Decision Log

- Decision: WP00R closes only PC-00; all runtime PC rows remain contracted.
  Rationale: Ratification authorizes implementation but is not implementation
  evidence.
  Date/Author: 2026-08-04 / Codex.

- Decision: Use paragraph/list-item checklist granularity rather than one row
  per `MUST` token.
  Rationale: A single normative paragraph often contains several related
  tokens that share one owner and one behavioral test, while section-15 bullets
  remain individually enumerated.
  Date/Author: 2026-08-04 / Codex.

## Outcomes & Retrospective

WP00R achieved its documentation-only purpose. The contract and roadmap are
ratified for implementation on `feature/project-owned-config`, PC-00 is closed,
and 164 detailed entries have named owners without claiming runtime completion.
Governance and security gates pass with zero unresolved blocker or medium/high
finding. WP00A, WP00B, and WP01 are authorized successors. Production remains
unchanged because the feature branch is noncanonical.

## Context and Orientation

The authoritative behavior is in
`docs/schemas/project-owned-config-contract.md`. The companion
`docs/schemas/project-owned-config-implementation-roadmap.md` decomposes that
behavior into WP00R, WP00A, WP00B, and WP01 through WP13, with PC-00 through
PC-21 closure ownership. “Normative” means a contract paragraph containing
`MUST` or `MUST NOT`, plus every bullet in contract section 15. “Ratified” in
this package means approved for implementation on the noncanonical
`feature/project-owned-config` branch. It does not mean promoted to `master`.

WP00R lives under
`docs/work-packages/20260804_project_config_contract_ratification/`. Its
checklist is
`artifacts/normative_requirement_checklist.md`; governance and security reviews
are separate artifacts in the same directory. `package.md` states scope and
closure; `tracker.md` is the operational handoff; this file is the executable
plan.

## Plan of Work

First, scaffold the package and record branch evidence. Then inventory every
normative contract paragraph and every required regression bullet. Assign each
entry to the narrowest PC row and its closure-owner package, name a tracker task
identifier that downstream scaffolds must import, and state the evidence type.

Next, reconcile the checklist in both directions: every inventory entry must be
mapped, and every PC row must have at least one entry. Review the roadmap for
branch, transfer, feature-flag, security, Forest, production, and alias-
retirement ownership. Capture governance and security findings with explicit
resolved, accepted-risk, or blocking status.

Finally, change the contract and roadmap from draft/not-approved language to
ratified-for-feature-branch-implementation language while preserving their
noncanonical status. Close WP00R only if reviews pass, the checklist is
complete, docs validate, and the root tracker identifies WP00R as completed.
Move this active plan to `prompts/completed/` and add an outcome note at
closure.

## Concrete Steps

Work from `/home/workdir/wepppy`.

Verify branch state:

    git branch --show-current
    git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'
    git status -sb

Expect the feature branch and matching remote with no unrelated changes before
WP00R edits.

Inventory contract clauses:

    rg -n '\bMUST\b|\bMUST NOT\b' docs/schemas/project-owned-config-contract.md
    markdown-extract '^15\\. Required Regression Evidence$' docs/schemas/project-owned-config-contract.md

Reconcile checklist coverage using source-line readback and searches for every
PC identifier. Validate all changed documents:

    wctl doc-lint --path docs/schemas/project-owned-config-contract.md \
      --path docs/schemas/project-owned-config-implementation-roadmap.md \
      --path docs/work-packages/20260804_project_config_contract_ratification \
      --path PROJECT_TRACKER.md
    diff -u <file> <(uk2us <file>)
    git diff --check

## Validation and Acceptance

Acceptance requires all of the following observable results:

- contract and roadmap state that they are ratified for implementation on the
  feature branch and noncanonical until promotion;
- the checklist states its inventory method and counts, maps every normative
  paragraph and every section-15 bullet, and includes every PC row;
- governance and security artifacts have passing verdicts with no unresolved
  blocker or medium/high security finding;
- package/tracker/plan and `PROJECT_TRACKER.md` identify WP00R as closed and
  WP00A/WP00B/WP01 as authorized successors; and
- documentation lint and diff checks pass.

No runtime tests, Forest deployment, RQ graph check, frontend tests, or
parameterization ADR are required because WP00R changes documentation and
authority only.

## Idempotence and Recovery

All WP00R edits are additive documentation changes and may be regenerated or
corrected without runtime state. If coverage reconciliation fails, leave the
contract status unratified and keep the package open. Do not delete or rewrite
unrelated work-package records. The feature branch can be safely reviewed
without affecting canonical `master`.

## Artifacts and Notes

Record the starting feature revision, final feature revision, checklist count,
review verdicts, and validation output in `tracker.md` and the completed plan
outcome. Do not copy secrets or configuration contents into any artifact.

## Interfaces and Dependencies

WP00R has no runtime interface. Its durable interface is documentation:

- Contract behavior: `docs/schemas/project-owned-config-contract.md`
- Sequencing and owners:
  `docs/schemas/project-owned-config-implementation-roadmap.md`
- Detailed coverage:
  `artifacts/normative_requirement_checklist.md`
- Successor ingress: WP00A, WP00B, and WP01 trackers must import checklist
  entries they own or contribute to.

Revision note (2026-08-04): Initial WP00R ExecPlan created for full scaffold,
inventory, review, ratification, and closure on the initiative branch.

Revision note (2026-08-04): Completed inventory and reviews, added advisory
coverage discovered during reconciliation, ratified the documents, and closed
WP00R with runtime requirements explicitly deferred to their owners.
