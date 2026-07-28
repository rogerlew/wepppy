# Pure UI Controller Contract Standardization

**Status**: Open (2026-07-16)
**Timezone**: UTC

## Overview

WEPPcloud's Pure UI controllers have a shared behavioral contract, but their
domain-specific DOM, request, persistence, reload, and event contracts are
distributed among source code, migration-era inventories, archived plans, and
module READMEs. That drift allowed a rendered field name to diverge from the
server parser without a contract test detecting it.

This package maintains the inventory and the one-controller execution protocol.
Each child writes tests against actual rendered and downstream behavior,
repairs confirmed mismatches minimally, and retains the regression coverage
before the next controller begins. Tooling is extracted only from repeated test
work.

## Objectives

- Define a concise test convention for a controller's rendered-to-persistence
  contract.
- Establish a complete, versioned register of Pure UI controllers and supporting
  components, including explicit inclusions, exclusions, owners, and audit state.
- Make every included register row a binding contractual obligation immediately;
  track implementation evidence separately from scope.
- Execute bounded child work packages until every in-scope controller has a
  current canonical contract and contract-focused regression coverage.
- Write actual-render and focused downstream tests before patching confirmed
  mismatches when practical.
- Keep production patches small, backward-compatible, and free of unrelated
  cleanup or redesign.
- Extract test helpers only after repeated controller tests demonstrate that
  they improve clarity and accuracy.
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
- Concise controller contract/field matrices, the reviewed inventory, and
  maintenance guidance in the nearest developer documentation.
- Child work packages that correct confirmed contract defects discovered by an
  audit, provided each correction stays within the audited controller boundary.
- Existing bounded remediation history; future controller work uses the ordinary
  one-controller test loop unless the operator explicitly broadens scope.

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
- Machine obligation registries, generated contract indexes, source/test
  manifests, change classifiers, consumer dependency engines, attestations, or
  new CI workflows without measured need and explicit operator approval.
- `wepppy/weppcloud/routes/usersum/generated/docs_index.json`, which remains an
  ignored generated artifact unless separately requested.

## Implementation Fidelity and Evidence

- **Fidelity target**: `contract-first conformance audit`
- **Normative authority paths**: applicable current canonical shared/cross-
  cutting contracts plus the concise intent/field matrix recorded by the
  controller package; intent may not be inferred from implementation
- **Implementation evidence paths**: `wepppy/weppcloud/templates/`,
  `wepppy/weppcloud/controllers_js/`, paired WEPPcloud/rq-engine routes, NoDb
  controllers, RQ workers, and focused tests are authoritative only for observed
  behavior and conformance evidence; they cannot define intended behavior
- **Cutover proof required**: every completed controller has automated
  actual-render and applicable downstream tests for risk-bearing fields;
  documentation-only source reading is insufficient.
- **Acceptance evidence type**: `both`

## Stakeholders

- **Primary**: WEPPcloud frontend, NoDb, and rq-engine maintainers
- **Reviewers**: one independent correctness reviewer for a production patch; a
  second review only for high-risk behavior changes, material shared fan-out,
  or explicit operator request
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

Every package records any dispatch in its tracker with the bounded task, edit
authority, and outcome. Reviewers remain independent of the production patch
they review; an implementer cannot approve their own fix.

This authority does not authorize scope expansion, branch creation/switching,
commits or pushes, deployment, production mutation, secret access, destructive
git operations, external writes/publication, or broader write ownership unless
the primary agent explicitly assigns that bounded action and existing operator/
repository gates permit it.

## Success Criteria

- [ ] The reusable prompt defines the concise one-controller, tests-first loop
  and its simplicity budget.
- [ ] The audit register contains every in-scope Pure UI controller and every
  shared component that can alter a submitted or hydrated value; exclusions
  include a rationale and evidence path.
- [ ] Every in-scope controller reaches `verified` through a closed child
  package with retained executable regression coverage.
- [ ] Each verified contract traces rendered DOM names/ids through JavaScript,
  request parsing, server mutation, persisted state, reload behavior, events,
  errors, and relevant RQ completion behavior.
- [ ] Risk-bearing field names, enum selectors, disabled/hidden semantics, and
  legacy aliases have automated contract-focused regression coverage.
- [ ] Tooling remains test-only, stateless, extracted from repetition, and
  smaller than the controller tests using it.
- [ ] Production patches have required correctness/security review with no
  unresolved high/medium findings.
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

- **Expected duration**: measured one controller at a time; reassess after five
  completed controllers rather than projecting from inventory size
- **Complexity**: Low per iteration
- **Risk level**: Low when tests precede minimal compatible patches; re-triage
  actual security or parameterization changes

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

Mitigation is direct: test actual rendered markup, reproduce a mismatch before
repair when practical, patch only that mismatch, preserve compatibility, run
focused tests before existing broad gates, and review actual production changes.
Stop-loss rules prevent test tooling from becoming a second product.

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
- Auditable controller inventory and one-at-a-time execution status.
- Concise controller contract/field matrices.
- Actual-render and focused downstream regression tests.
- Minimal confirmed mismatch repairs and proportional review evidence.
- Five-controller value assessment before any maintenance-tooling proposal.

## Follow-up Work

- Child packages are created only from approved register entries and are linked
  from the umbrella tracker and `PROJECT_TRACKER.md`.
- Defects outside a controller's bounded contract become separate work packages
  rather than expanding the current child package silently.
