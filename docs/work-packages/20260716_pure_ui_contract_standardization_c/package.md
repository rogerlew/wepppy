# Pure UI Controller Contract Standardization

**Status**: Open (2026-07-16)
**Timezone**: UTC

## Overview

WEPPcloud's Pure UI controllers have a shared behavioral contract, but their
domain-specific DOM, request, persistence, reload, and event contracts are
distributed among source code, migration-era inventories, archived plans, and
module READMEs. That drift allowed a rendered field name to diverge from the
server parser without a contract test detecting it.

This package establishes the governance, standard, inventory, and iterative
execution protocol for auditing every Pure UI controller. It is an umbrella
package: implementation proceeds through bounded child work packages, each of
which produces current canonical documentation, regression evidence, and two
independent review dispositions.

## Objectives

- Define one canonical, evidence-backed documentation schema for a Pure UI
  controller's complete browser-to-persistence contract.
- Establish a complete, versioned register of Pure UI controllers and supporting
  components, including explicit inclusions, exclusions, owners, and audit state.
- Make every included register row a binding contractual obligation immediately;
  track implementation evidence separately from scope.
- Execute bounded child work packages until every in-scope controller has a
  current canonical contract and contract-focused regression coverage.
- Require the accepted contract-decision checkpoint and ancestor revision before
  intended changes to templates, controllers, routes, NoDb inputs, RQ behavior,
  or persisted state; keep implementation evidence and supporting docs together.
- Require two independent subagent reviews and a finding-disposition artifact
  for the umbrella package and every child work package.
- Register operator-authorized bounded remediation packages without treating
  borrowed future owner packages as executed or dependency-complete.

## Scope

### Included

- Domain controllers used by the Pure run UI and Pure standalone consoles.
- The controller's rendered template and macro calls, including the distinction
  between DOM `id`, submitted `name`, and `data-*` behavior hooks.
- Controller bootstrap, hydration, caching, events, serialization, transport,
  completion, error, and reload behavior.
- Browser/session and rq-engine routes, `parse_request_payload` normalization,
  NoDb `parse_inputs` or equivalent mutation code, persistence, and RQ handoff.
- Current tests and missing regression tests for the documented contract.
- Shared Pure controller infrastructure when it defines a cross-controller
  contract, documented once and referenced by domain contracts.
- Canonical documentation under `docs/ui-docs/contracts/`, a coverage register,
  and maintenance guidance in the nearest developer documentation.
- Child work packages that correct confirmed contract defects discovered by an
  audit, provided each correction stays within the audited controller boundary.
- Bounded cross-owner remediation packages ratified through GOV-00A when a
  concrete production defect spans planned owners before their normal
  dependency order is complete.

### Explicitly Out of Scope

- Visual redesign, feature additions, or controller rewrites unrelated to a
  confirmed contract mismatch.
- Treating generated `wepppy/weppcloud/static/js/controllers-gl.js` as an
  editable source.
- Deploying to forest or production without a separate operator request.
- Changing model parameter defaults, formulas, units, thresholds, or fallback
  rules as part of a documentation audit.
- Broad route, queue, or NoDb refactors merely because an audit finds an awkward
  but internally consistent interface.
- `wepppy/weppcloud/routes/usersum/generated/docs_index.json`, which remains an
  ignored generated artifact unless separately requested.

## Implementation Fidelity and Evidence

- **Fidelity target**: `contract-first conformance audit`
- **Normative authority paths**: applicable current canonical shared/cross-
  cutting contracts and each domain path registered by GOV-00A; until a domain
  contract is ratified, its registered child package records operator-approved
  intent and may not infer it from implementation
- **Implementation evidence paths**: `wepppy/weppcloud/templates/`,
  `wepppy/weppcloud/controllers_js/`, paired WEPPcloud/rq-engine routes, NoDb
  controllers, RQ workers, and focused tests are authoritative only for observed
  behavior and conformance evidence; they cannot define intended behavior
- **Cutover proof required**: every canonical contract is linked from the
  coverage register and is backed by an automated rendered-template or request
  boundary test for its risk-bearing fields; documentation-only source reading
  is not sufficient for a completed audit.
- **Acceptance evidence type**: `both`

## Stakeholders

- **Primary**: WEPPcloud frontend, NoDb, and rq-engine maintainers
- **Reviewers**: two independent subagents per package: one contract/code
  reviewer and one regression/QA reviewer
- **Security Reviewer**: assigned by a child package when its audit remediation
  changes a high-impact surface
- **Informed**: forest and production operators, domain-controller owners

## Operator-Authorized Subagent Dispatch

The operator explicitly authorizes the executing primary agent to dispatch
subagents for this umbrella package and its child packages. Authorized scopes
are bounded inventory, source tracing, contract drafting, focused implementation,
test execution, and independent review. The primary agent remains responsible
for scope control, shared-worktree coordination, evidence verification, finding
disposition, and all final claims.

Every package must record each dispatch in its tracker with the agent or role,
bounded task, edit authority, and outcome. At least two reviewers must be
independent of the authoring agent and of one another. Review agents are
read-only unless the primary agent explicitly reassigns a finding for
implementation; an agent that implements a finding cannot approve its own fix.

This authority does not authorize scope expansion, branch creation/switching,
commits or pushes, deployment, production mutation, secret access, destructive
git operations, external writes/publication, or broader write ownership unless
the primary agent explicitly assigns that bounded action and existing operator/
repository gates permit it.

## Success Criteria

- [ ] `docs/ui-docs/contracts/README.md` defines the canonical schema, derived
  published reader index, evidence levels, ownership rules, and contract-first
  checkpoint policy without becoming a competing status authority.
- [ ] The audit register contains every in-scope Pure UI controller and every
  shared component that can alter a submitted or hydrated value; exclusions
  include a rationale and evidence path.
- [ ] Every in-scope controller reaches `verified` status through a closed child
  work package and a canonical contract under `docs/ui-docs/contracts/`.
- [ ] Each verified contract traces rendered DOM names/ids through JavaScript,
  request parsing, server mutation, persisted state, reload behavior, events,
  errors, and relevant RQ completion behavior.
- [ ] Risk-bearing field names, enum selectors, disabled/hidden semantics, and
  legacy aliases have automated contract-focused regression coverage.
- [ ] A source-to-contract manifest maps every controller and shared producer to
  its contracts and contract tests; a change-aware gate rejects unmaintained
  source changes or requires an independently reviewed no-impact attestation.
- [ ] Every child package contains two raw independent review artifacts plus a
  primary-agent disposition artifact with no unresolved high/medium findings.
- [ ] Coverage and documentation lint checks pass, controller bundles rebuild
  when source changes, and relevant frontend/backend test gates pass.
- [ ] `controllers_js/AGENTS.md`, `controllers_js/README.md`, and affected domain
  docs point to canonical contracts instead of archived plans.

## Parameterization ADR Gate

- **Parameterization change present**: `no`
- **ADR required**: `no`
- **ADR link(s)**: N/A
- **Decision provenance captured**: `yes` - operator request recorded in this
  package and tracker

If an audit discovers a model-parameter defect, create or amend a child package
and satisfy `docs/standards/parameterization-adr-standard.md` before changing the
parameterization behavior.

## Dependencies

### Prerequisites

- `docs/ui-docs/controller-contract.md` for existing cross-controller invariants.
- `wepppy/weppcloud/controllers_js/AGENTS.md` and `README.md` for controller
  architecture and validation commands.
- `docs/ui-docs/control-ui-styling/control-inventory.md` as historical inventory,
  not as presumed-current authority.
- A clean baseline or an explicitly recorded list of unrelated worktree changes
  before each child package begins.

### Blocks

- A trustworthy answer to whether a Pure UI controller's browser/server contract
  is current and regression-protected.
- Retirement or consolidation of stale archived controller plans.

## Related Packages

- **Related**: `docs/work-packages/20251023_controller_modernization/`
- **Related**: `docs/work-packages/20251023_frontend_integration/`
- **Incident precedent**: the WATAR selector/value persistence regression,
  documented in the ash domain and used as the pilot audit case
- **Follow-up**: bounded child packages generated from the audit register

## Timeline Estimate

- **Expected duration**: 18-32 serial weeks for GOV-00, GOV-00A, SHR-01 through
  SHR-04B, the WATAR pilot, and maintenance gate; 24-36 months for all 72 execution units
  with one authoring package active at a time, or roughly 12-20 months with
  separately authorized isolated worktrees and at most two disjoint writers
  after the shared foundation
- **Complexity**: High
- **Risk level**: Medium

## Security Impact and Review Gate

- **Security impact triage**: `none` for this documentation/governance scaffold
- **Dedicated security review required**: `no`
- **Triage rationale**: this package defines documentation and review workflow;
  it does not change an attack surface. Every child package must repeat triage,
  and changes to auth, CSRF, public routes, uploads, paths, queues, or external
  egress are `high` by default.
- **Security review artifact**: N/A

## Risk Assessment

The initiative's documentation-only scaffold is low risk. Executing the full
initiative is **medium risk** because the audit will cross browser, route, NoDb,
and RQ boundaries and may uncover mismatches whose repair affects live projects.
The highest regression risk is making stale prose look authoritative or fixing
one layer without proving end-to-end propagation.

Mitigation is structural: preserve current behavior until a mismatch is proven;
capture rendered request evidence before editing; use one bounded controller or
cohesive low-risk family per child package; add the exact failing regression;
verify persisted and reloaded state; require two independent reviews; and keep
deployment outside the package unless separately authorized. These controls
reduce risk materially but do not make it zero, especially for configuration-
specific controls and legacy aliases exercised only by old saved runs.

## References

- `docs/prompt_templates/codex_exec_plans.md`
- `docs/work-packages/README.md`
- `docs/ui-docs/controller-contract.md`
- `docs/ui-docs/control-ui-styling/control-inventory.md`
- `docs/dev-notes/frontend-change-checklist.md`
- `wepppy/weppcloud/controllers_js/AGENTS.md`
- `wepppy/weppcloud/controllers_js/README.md`

## Deliverables

- Active umbrella ExecPlan and reusable child-package audit prompt.
- Auditable controller coverage register plus the stable 71-unit execution
  register and status; GOV-00 is this umbrella, GOV-00A is the active
  ratification child, and the other 69 dated package directories are created
  only when started.
- `docs/ui-docs/contracts/contract-obligations.json` as the sole machine
  obligation/evidence-summary authority after GOV-00A ratification.
- Canonical Pure UI contract standard/coverage index and per-controller
  contracts.
- Source-to-contract manifest and change-aware maintenance gate.
- Focused regression tests and review dispositions produced by child packages.

## Follow-up Work

- Child packages are created only from approved register entries and are linked
  from the umbrella tracker and `PROJECT_TRACKER.md`.
- Defects outside a controller's bounded contract become separate work packages
  rather than expanding the current child package silently.
