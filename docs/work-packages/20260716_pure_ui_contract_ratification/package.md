# Pure UI Contract Ratification

**Stable ID**: GOV-00A
**Status**: Open (2026-07-17)
**Timezone**: UTC

## Overview

The Pure UI coverage register is binding, but the canonical contract schema and
authority hierarchy are not yet published under `docs/ui-docs/contracts/`.
This child package ratifies the rule that every included register item is
contractual now while keeping implementation-conformance evidence on a separate
`unverified` → `documented` → `verified` axis.

Ratification prevents agents from treating incomplete evidence as permission to
ignore a controller. It also gives every later domain package one standard for
DOM fields, payloads, route normalization, persistence, RQ behavior, reload,
compatibility, security, and review evidence.

Canonical domain and repository contracts are normative authority. UI, route,
worker, and test code is conformance evidence. An intended behavior change must
amend every applicable contract before implementation begins; restoring code to
an existing contract does not rewrite the contract's normative behavior.

## Objectives

- Publish a normative Pure UI contract schema and authority hierarchy.
- Make `contractual` the binding status for every included coverage row.
- Separate contractual scope, evidence grade, and package execution state.
- Ratify contract-first sequencing for UI, WEPPcloud/rq-engine route, and RQ
  worker changes.
- Provide one reusable canonical contract template and derived reader-index
  policy.
- Ratify compatibility, discrepancy, security, and dual-review requirements
  before shared-foundation and domain audits begin.
- Ratify a bounded cross-owner remediation mechanism for finite production
  defects discovered before the normal domain dependency spine is complete.

## Scope

### Included

- `docs/ui-docs/contracts/README.md` as the normative schema, lifecycle policy,
  and derived reader index.
- `docs/ui-docs/contracts/_contract_template.md` as the reusable template.
- `docs/ui-docs/contracts/contract-obligations.json` as the sole machine
  authority for obligation scope, execution owner, evidence grade, canonical
  contract path, and verified revision/date summary.
- `tools/ui_contract_ratification.py` with `check` and `write-index` commands,
  plus `tests/tools/test_ui_contract_ratification.py` and fixtures under
  `tests/fixtures/ui_contract_ratification/`.
- `docs/standards/contract-first-change-standard.md` as immediate contract-first
  governance, including the finite pre-cutover authority set, checkpoint, and
  bounded cross-owner remediation rules.
- Targeted updates to the finite authority set:
  `docs/ui-docs/controller-contract.md`, `docs/ui-docs/README.md`,
  `wepppy/weppcloud/controllers_js/README.md`,
  `AGENTS.md`, `wepppy/weppcloud/AGENTS.md`,
  `wepppy/weppcloud/controllers_js/AGENTS.md`,
  `wepppy/microservices/rq_engine/AGENTS.md`, `wepppy/nodb/AGENTS.md`,
  `wepppy/rq/AGENTS.md`, the parent package/ledger/register/ExecPlan/tracker, this child package, and
  `PROJECT_TRACKER.md`.
- Reconciliation of the umbrella coverage ledger, execution register, child
  prompt, and future manifest specification with the ratified vocabulary.
- Deterministic documentation/schema checks appropriate to a governance-only
  package.
- Two independent read-only reviews and a primary disposition with post-fix
  confirmation.

### Explicitly Out of Scope

- Auditing or verifying any one domain controller's complete runtime behavior.
- Implementing GOV-01's change-aware source/contract/test enforcement.
- Editing controller JavaScript, templates, routes, NoDb state, RQ workers, or
  generated bundles.
- Changing UI behavior, model parameters, defaults, units, formulas, or
  compatibility aliases.
- Deploying to forest or production.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful extraction` of the operator-approved governance
  contract and existing repository invariants
- **Normative governance authority paths**:
  `docs/standards/contract-first-change-standard.md`, this active package, and
  the parent contractual/execution registers
- **Schema evidence paths**: `docs/ui-docs/controller-contract.md` for shared
  invariants and Pure controller/template sources as representational examples;
  neither source code nor historical prose defines domain intent
- **Cutover proof required**: every enumerated obligation has exactly
  `contract_scope="contractual"`, one allowed evidence grade, and one registered
  execution owner in `contract-obligations.json`; current documentation points
  to the ratified authority; deterministic positive/negative checks and both
  reviews pass
- **Acceptance evidence type**: `both` repository-source reconciliation and
  executable documentation/schema validation

## Stakeholders

- **Primary**: WEPPcloud frontend, route, NoDb, and RQ maintainers
- **Reviewers**: two independent subagents, one contract/authority reviewer and
  one regression/maintainability reviewer
- **Security Reviewer**: not required for this documentation-only package;
  later remediation packages repeat security triage
- **Informed**: forest and production operators and domain-controller owners

## Operator-Authorized Subagent Dispatch

The operator's umbrella authorization applies to bounded inventory, drafting,
validation, and independent review for GOV-00A. The primary agent records every
dispatch in `tracker.md`, owns integration and disposition, and does not infer
deployment, production mutation, branch creation, external publication, or
secret access. Reviewers remain read-only and independent unless explicitly
reassigned; an implementer cannot approve their own work.

## Success Criteria

- [ ] Every included coverage row is normatively `contractual`; missing evidence
  is represented only by its evidence grade.
- [ ] `docs/ui-docs/contracts/README.md` defines authority, required sections,
  lifecycle, compatibility, security, review, and derived-index policy.
- [ ] A canonical contract template distinguishes DOM id, submitted name,
  labels, enum tokens, parser keys, persisted attributes, and reload values.
- [ ] The standard defines absent/hidden/disabled/unchecked/file semantics,
  aliases/conflict precedence, RQ completion/error behavior, and configuration
  evidence.
- [ ] `docs/ui-docs/controller-contract.md`, umbrella artifacts, child prompt,
  and tracker links agree with the ratified authority.
- [ ] Agent governance requires contract identification before implementation,
  contract amendment before intended behavior changes, and regression evidence
  when restoring code to an unchanged contract.
- [ ] Intended behavior changes require an operator-approved, dual-reviewed
  contract-decision artifact committed as an ancestor before implementation.
- [ ] A bounded cross-owner remediation is registered, inherits the highest
  borrowed-owner security impact, remains defect-scoped, and cannot advance or
  bypass the borrowed owners' normal execution state.
- [ ] Governance checks positively enumerate every obligation and require
  contractual scope, allowed evidence grade, registered owner, and uniqueness.
- [ ] Negative fixtures cover missing, blank, optional, improperly excluded,
  duplicate, unknown-scope, unknown-grade, and unknown-owner records plus
  missing required sections and derived-index drift.
- [ ] Two independent reviews are dispositioned with no unresolved high/medium
  findings and post-fix confirmations are recorded.
- [ ] Canonical documentation lint and `git diff --check` pass.

## Parameterization ADR Gate

- **Parameterization change present**: `no`
- **ADR required**: `no`
- **ADR link(s)**: N/A
- **Decision provenance captured**: `yes` — operator direction is recorded in
  the umbrella and this package

## Dependencies

### Prerequisites

- GOV-00 population and execution register:
  `docs/work-packages/20260716_pure_ui_contract_standardization_c/`
- Existing shared invariant document: `docs/ui-docs/controller-contract.md`

### Blocks

- SHR-01 through SHR-04B shared-foundation contract packages.
- DOM-01 WATAR/Ash contract pilot.
- GOV-01 change-aware maintenance gate.

## Related Packages

- **Parent**: `docs/work-packages/20260716_pure_ui_contract_standardization_c/`
- **Follow-up**: SHR-01 through SHR-04B, DOM-01, and GOV-01 as registered in the
  parent's child-package register
- **Historical context**: `docs/work-packages/20251023_controller_modernization/`

## Timeline Estimate

- **Expected duration**: 2-4 focused weeks
- **Complexity**: Medium
- **Risk level**: Medium contract-governance risk; low repository mutation risk

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: this package changes documentation, validation, and
  governance only. It does not change an attack surface. Any later change to
  auth/session/CSRF/CAP, public routes, uploads/downloads, files/paths, queues,
  workers, secrets, or egress is high by default and requires re-triage.
- **Security review artifact**: N/A

## Risk Assessment

The primary risk is semantic: a vague standard could make stale prose look
authoritative, or let `unverified` be misread as optional. The mitigation is an
explicit three-dimension model, positive enumeration, deterministic negative
checks, one authority hierarchy, exact contract fields, and dual independent
review. This package deliberately
does not claim that implementation behavior is verified; it ratifies the
obligation and the evidence needed to make that later claim.

## References

- `docs/prompt_templates/codex_exec_plans.md`
- `docs/work-packages/README.md`
- `docs/ui-docs/controller-contract.md`
- `docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/controller_audit_register.md`
- `docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/child_package_register.md`

## Deliverables

- Active ratification ExecPlan and tracker.
- Normative contracts README, reusable contract template, and contractual
  obligation registry.
- `tools/ui_contract_ratification.py`, focused tests, and isolated fixtures.
- Ratified lifecycle/authority updates across umbrella and developer docs.
- Deterministic governance validation evidence.
- Two raw independent reviews and primary disposition.

## Follow-up Work

After ratification, execute shared-foundation packages in dependency order,
then the DOM-01 WATAR/Ash pilot. GOV-01 implements machine-readable fan-out,
contract-decision ancestry enforcement, and subsequent implementation-evidence
maintenance after the pilot proves stable metadata.
