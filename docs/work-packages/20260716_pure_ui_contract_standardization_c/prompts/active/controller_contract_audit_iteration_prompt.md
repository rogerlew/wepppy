# Execute one Pure UI controller contract audit child package

> **Purpose**: Reusable protocol for creating, executing, reviewing, and closing
> one bounded child package from the umbrella audit register.
> **Target**: Primary Codex agent with operator-authorized subagent dispatch
> **Created**: 2026-07-16
> **Status**: Active

## Authority and Boundary

The operator has authorized the primary agent to dispatch subagents for bounded
inventory, tracing, implementation, testing, and independent review within this
initiative. Record every dispatch in the child tracker. This authority does not
authorize scope expansion, branch creation/switching, commits or pushes,
deployment, production mutation, secret access, destructive git operations,
external writes/publication, or broader write ownership unless the primary
agent explicitly assigns that bounded action and existing operator/repository
gates permit it.

Select exactly one controller or a small cohesive family from
`artifacts/controller_audit_register.md`. Do not combine unrelated controllers
to reduce package count. A high-risk controller involving uploads, auth, public
routes, queue wiring, or complex persisted state should receive its own package.

## Required Package Creation

Create a standard work package using `docs/work-packages/README.md` and
`docs/prompt_templates/`. The child package must include:

- `package.md` with faithful-extraction scope, security triage, risk assessment,
  exact controller boundary, and success criteria;
- `tracker.md` with dispatch log, source matrix, decisions, tests, and review
  status;
- `prompts/active/<scope>_execplan.md` following
  `docs/prompt_templates/codex_exec_plans.md`;
- `artifacts/<date>_baseline_contract_evidence.md`;
- `artifacts/<date>_contract_review.md` containing the first reviewer's raw or
  verbatim findings and identity;
- `artifacts/<date>_regression_qa_review.md` containing the second reviewer's raw
  or verbatim findings and identity;
- `artifacts/<date>_review_disposition.md` owned by the primary agent;
- a security review artifact when child triage is `high`.

Add the child package to the umbrella tracker, the audit register, and
`PROJECT_TRACKER.md` before implementation begins.

## Required Inputs

Read all applicable nearest `AGENTS.md` files and at least:

- the umbrella `package.md`, `tracker.md`, active ExecPlan, and audit register;
- `docs/ui-docs/contracts/README.md` after Milestone 1 creates it;
- `docs/ui-docs/controller-contract.md`;
- `wepppy/weppcloud/controllers_js/AGENTS.md` and `README.md`;
- the controller source, Pure template/macro calls, generated host context, paired
  browser/rq-engine routes, mutation owner, RQ worker, and focused tests;
- historical/domain docs only as leads, never as presumed-current authority.

## Baseline Before Editing

1. Record the starting commit and worktree state. Preserve unrelated changes.
2. Render or obtain representative HTML for every relevant config gate. Record
   the exact form id, input id, submitted name, option value, checked/disabled/
   hidden state, and `data-*` hook for every state-changing field.
3. Capture the controller's actual serialized FormData/JSON and request URL,
   method, encoding, auth/session/CSRF behavior, and file handling.
4. Trace every canonical key through route parsing and normalization, NoDb or
   server mutation, lock/dump/invalidation, RQ handoff, persisted representation,
   and bootstrap/reload hydration.
5. Record current tests and demonstrate each material gap. For a confirmed bug,
   add a failing regression before the fix when practical.

Do not edit code until the baseline evidence distinguishes current behavior,
documented intent, and confirmed mismatch.

Build a per-field, per-mode, and per-configuration evidence matrix. Every value
that is submitted, hydrated, persisted, enum/file-bearing, sensitive to hidden
or disabled state, or controls RQ execution/completion is material/risk-bearing
by default. Excluding a value or variant requires a written rationale and both
independent reviewers' approval. Untested material variants may be
`documented`; they cannot be `verified`.

## Canonical Contract Output

Create or update `docs/ui-docs/contracts/<controller>.md` and its authoritative
manifest/register metadata. Regenerate or verify the derived published reader
entry in `docs/ui-docs/contracts/README.md`; do not hand-maintain a competing
coverage status there. The controller file must contain:

1. **Identity and scope** - user purpose, configs/mods, controller singleton,
   source/template/route/state owners, security and risk tier.
2. **Prerequisites and lifecycle** - bootstrap, absent-section behavior,
   upstream readiness, dynamic loading, completion authority, reload.
3. **DOM and interaction matrix** - ids, submitted names, types, defaults,
   labels/units, `data-*` hooks, visibility/disabled semantics, actions.
4. **Client state and events** - seed data, caches, capture/restore behavior,
   emitted and consumed events, idempotence.
5. **Transport contract** - endpoints, methods, encodings, canonical payload
   schema, enum tokens, files, auth/session/CSRF, errors.
6. **Server normalization and mutation** - parser/defaults, aliases and conflict
   precedence, validation, state owner, locks/dumps, invalidation/timestamps.
7. **RQ and outputs** - enqueue/dependencies, job hints, terminal state, error
   propagation, produced/readiness artifacts when applicable.
8. **Persistence and compatibility** - stored representation, old-run behavior,
   round-trip evidence, deprecations and removal gates.
9. **Verification** - exact tests, rendered/runtime evidence, accessibility
   evidence where applicable, manual matrix, last verified commit and UTC date.
10. **Discrepancy ledger** - for every mismatch, explicit `Observed`,
    `Normative`, `Authority/rationale`, `Discrepancy status`, and `Disposition
    evidence` fields. State `none found` only after completing the evidence
    matrix. A material unresolved discrepancy blocks `verified`.
11. **Known gaps** - unresolved low-risk limitations and linked follow-up work;
    name every untested configuration and keep the contract `documented` when a
    material variant lacks evidence.

Reference shared invariants rather than duplicating them. If actual behavior is
defective, label it as a defect; do not write desired behavior as if deployed.

## Change Discipline

- Make the smallest change that repairs a confirmed mismatch.
- Preserve public payload keys and persisted fields by default. Additive aliases
  require explicit precedence, warning/deprecation behavior, and tests.
- Do not silently accept both a canonical and legacy field with ambiguous
  last-write-wins behavior.
- Treat macro changes as cross-controller until all call sites are audited.
- Do not edit generated controller bundles directly; rebuild them from source.
- Update authoritative contract and domain documentation in the same change.
- If parameter defaults, formulas, units, thresholds, or fallbacks would change,
  satisfy the parameterization ADR gate before implementation.
- Immediately repeat security triage before implementing any discovered
  remediation. Auth/session/JWT/CSRF/OAuth, secrets, public route handlers,
  uploads/downloads, file/path handling, queue wiring, worker subprocess/shell,
  CI/CD permissions, deployment wiring, or external egress changes are `high` by
  default and require the child security artifact before implementation.
- If RQ enqueue sites or dependency edges change, update
  `wepppy/rq/job-dependencies-catalog.md`, run `wctl check-rq-graph`, and manually
  validate a live job tree.

## Required Regression Evidence

At minimum, add or identify tests proving:

- rendered field `name` values match parser keys independently of DOM ids;
- JavaScript emits the documented payload and enum values;
- route parsing normalizes types, defaults, missing values, and files correctly;
- mutation reaches the documented NoDb/server attributes;
- persisted values survive dump/reload and rehydrate the controller where state
  is durable;
- legacy alias/conflict behavior is deterministic when supported;
- RQ-backed actions expose correct enqueue and terminal/error semantics.

Run the narrowest applicable tests during iteration, then the standard frontend
gates for source changes:

```bash
wctl run-npm lint
wctl run-npm test
python wepppy/weppcloud/controllers_js/build_controllers_js.py
```

Run paired backend tests with `wctl run-pytest`, documentation lint for every
changed Markdown file, `git diff --check`, broad-exception enforcement when
production Python changes, and the full suite before package closeout unless the
child ExecPlan documents a justified, operator-approved alternative.

## Mandatory Dual Independent Review

After implementation and validation, dispatch two reviewers who did not author
the changes:

- **Reviewer A - contract/code**: independently trace template -> controller ->
  transport -> parser -> mutation -> RQ/persistence and identify incorrect,
  missing, or ambiguous contract claims.
- **Reviewer B - regression/QA**: challenge rendered coverage, config variants,
  hidden/disabled/absent semantics, old-run compatibility, error/completion
  behavior, test quality, and documentation maintenance hooks.

Both reviewers are read-only. Record reviewer identities, scope, commands or
evidence, severity, recommendation, and residual risk. The primary agent records
every finding in the separate review disposition artifact as accepted-fixed,
rejected-with-evidence, accepted-follow-up, or operator-accepted residual risk.
High/medium findings must be fixed and reviewer-confirmed before closure;
deferral requires explicit operator acceptance with an owner/date/rationale, not
agent judgment alone. Any behavior-changing disposition reruns affected gates.

## Closure Gate

The child package is complete only when:

- the canonical contract and audit-register row are `verified` at a named
  commit/date;
- source-to-contract manifest mappings are current, and the change-aware gate
  confirms that mapped source and contract-test maintenance obligations are met;
- executable evidence covers every risk-bearing field and state transition;
- relevant tests and docs checks pass;
- both raw/verbatim independent review artifacts, post-fix confirmations, and
  the primary disposition are complete;
- security review is complete when required;
- child and umbrella trackers plus `PROJECT_TRACKER.md` are current;
- the active child ExecPlan is moved to `prompts/completed/` with outcomes.

Report truthfully when config coverage, fixtures, or manual evidence is partial.
Partial audit evidence may advance a row to `documented`; it cannot advance it
to `verified`.

## Anti-Patterns

- Do not copy field tables from `control-inventory.md` without re-verification.
- Do not test only the DOM id when the browser submits the `name`.
- Do not treat a successful enqueue as proof that values persisted or were used.
- Do not infer saved-run compatibility from constructor defaults.
- Do not let a reviewer edit and then approve the same fix.
- Do not close a package with an unwritten "looks good" review.
- Do not expand one controller audit into a general UI redesign.

## Handoff Format

Report the child package, canonical contract, verified commit/date, tests,
rendered/runtime evidence, both raw review artifacts and their disposition,
security status, remaining low-risk gaps, and the next register entry recommended
for execution.
