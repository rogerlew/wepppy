# Tracker - Pure UI Controller Contract Standardization

> Living record for the umbrella contract audit and its child work packages.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-17 00:30 UTC
**Current phase**: Milestone 1 - GOV-00A schema ratification
**Last updated**: 2026-07-21 22:15 UTC
**Next milestone**: Continue GOV-00A canonical schema and derived index work.
**Security impact**: `none` for scaffold; child packages reassess
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Execute Milestone 1: freeze inventory and ratify the canonical contract
  standard.
- [ ] Create and execute the WATAR pilot child package.
- [ ] Execute child packages in dependency/risk order.
- [ ] Add coverage enforcement after the pilot proves the metadata contract.
- [ ] Consolidate or redirect stale controller documentation.

### In Progress

- [ ] Execute GOV-00A and ratify the canonical contract schema.

### Blocked

- None.

### Done

- [x] Created umbrella package, active ExecPlan, child-package audit prompt, and
  initial audit register (2026-07-17 00:30 UTC).
- [x] Recorded explicit operator authority for bounded subagent dispatch and
  mandatory dual independent review (2026-07-17 00:30 UTC).
- [x] Dispositioned the first inventory-review findings by broadening route-local
  discovery, separating standard/pilot waves, and aligning lifecycle state
  (2026-07-17 00:47 UTC).
- [x] Closed both independent scaffold reviews with post-fix confirmation and no
  unresolved high/medium findings (2026-07-17 00:48 UTC).
- [x] Registered operator-authorized bounded remediation REM-01 across the
  exact DOM-02/DOM-25A/DOM-25B defect boundary (2026-07-20 21:23 UTC).
- [x] Dual-reviewed and accepted the bounded GOV-00A-M1A/REM-01 ancestor with
  no unresolved high/medium findings (2026-07-20 21:40 UTC).
- [x] Committed both REM-01 contract ancestors, executed its finite boundary,
  passed dual final review and broad validation, and closed the remediation
  without advancing DOM-02, DOM-25A, or DOM-25B (2026-07-20 22:42 UTC).
- [ ] REM-02 is registered for ratification: expose read-only TTL deletion
  timing in already-authorized Runs catalog rows, preserve Last Modified for
  disabled TTL, and publish a dedicated Usersum guide (2026-07-21 22:15 UTC).
- [x] Identified, corrected, dual-reviewed, and froze the 70-unit execution
  register with no unresolved high/medium findings (2026-07-17).
- [x] Began GOV-00A Milestone 1 by adding contract-first precedence to root and
  UI/RQ subsystem agent governance (2026-07-17; bounded review pending).

## Child Package Register

Detailed scope, dependencies, risk, security triggers, bootstrap allocation, and
exclusions are authoritative in
`artifacts/child_package_register.md`. Dated package paths are assigned only when
the corresponding stable ID starts.

| Stable IDs | Package class | Count | State | Review gate |
| --- | --- | --- | --- | --- |
| GOV-00 | Standard/population/register foundation | 1 | auditing | In progress |
| GOV-00A | Contract schema and lifecycle ratification | 1 | auditing | Contract-first governance reviewed; schema artifacts open |
| DOM-01..DOM-29 (including A-D facets) | Run-domain controller packages | 39 | planned | Two independent reviews each |
| GOV-01 | Change-aware maintenance enforcement | 1 | planned | Two independent reviews |
| SHR-01..SHR-07 (including A/B facets) | Shared-foundation packages | 9 | planned | Two independent reviews each |
| SURF-01..SURF-18 (including A/B facets) | Non-run/stateful Pure surfaces | 19 | planned | Two independent reviews each |
| GOV-99 | Authority cutover and closeout | 1 | planned | Two independent final reviews |

Total: 73 independently closable execution units. GOV-00 is this existing
umbrella; GOV-00A is the active ratification child; REM-01 is complete and
REM-02 is in ratification. The remaining units receive dated directories when
started. DOM-01 is the WATAR/Ash pilot.

Every new child package must be added here and to `PROJECT_TRACKER.md` before
implementation begins. A package is not closed merely because documentation was
written; both independent review columns must be complete and all findings must
be dispositioned.

## Dispatch Log

| Time (UTC) | Agent/role | Scope | Edit authority | Outcome |
| --- | --- | --- | --- | --- |
| 2026-07-17 00:30 | Controller inventory auditor | Enumerate Pure UI controller/template/route/test coverage and grouping | Read-only | Complete; found 33 run-page bootstrap entries, 26 main panels, and Batch Runner as a separate Pure surface |
| 2026-07-21 22:15 | Primary Codex | REM-02 TTL catalog contract checkpoint and registration | Documentation only | In progress; implementation blocked pending independent ratification review and standalone ancestor |
| 2026-07-17 00:30 | Contract governance reviewer | Challenge schema, package protocol, review gate, and risk controls | Read-only | Complete; recommended canonical contracts directory, normative/observed split, and independent semantic/QA gates |
| 2026-07-17 00:39 | Reviewer A | Final contract/source review of the authored scaffold | Read-only | One medium and three low findings; all accepted and fixed |
| 2026-07-17 00:39 | Reviewer B | Final regression/governance review of the authored scaffold | Read-only | One high, three medium, and three low findings; all accepted and fixed |
| 2026-07-17 00:47 | Reviewer A | Post-fix confirmation of A findings | Read-only | Closure-ready; no new high/medium findings |
| 2026-07-17 00:47 | Reviewer B | Post-fix confirmation of B findings | Read-only | Closure-ready; no new high/medium findings |
| 2026-07-17 00:55 | Controller inventory auditor | Reconcile 33 production controllers into exact bounded packages with routes/tests/security | Read-only | Complete; proposed 33 domain packages and identified missing rendered seams |
| 2026-07-17 00:55 | Contract governance reviewer | Reconcile shared and route-local Pure surfaces and challenge package sizing | Read-only | Complete; reconciled 56 modules and proposed 7 shared plus 12 stateful surface packages |
| 2026-07-17 01:08 | Reviewer A | Production/accounting review of the initial 55-unit register draft | Read-only | Complete; three high, two medium, and one low finding accepted for disposition |
| 2026-07-17 01:08 | Reviewer B | Governance/risk/executability review of the initial 55-unit register draft | Read-only | Complete; two high, six medium, and two low findings accepted for disposition |
| 2026-07-17 | Primary agent | Apply register-review findings: populate item ledger, add inherited account/security, ERMiT, RQ Info, and DEVAL surfaces, split broad packages, fix ownership/dependencies, and re-estimate | Write | In progress; register expanded to 70 units |
| 2026-07-17 | Reviewer A | Post-fix 67-unit production/accounting review | Read-only | No high; two medium and two low findings; all accepted for correction |
| 2026-07-17 | Reviewer B | Post-fix 67-unit governance/executability review | Read-only | Three high, three medium, and one low finding; all accepted for correction |
| 2026-07-17 | Reviewer A | Final 70-unit production/accounting confirmation | Read-only | Closure-ready; no remaining high/medium findings |
| 2026-07-17 | Reviewer B | Final 70-unit governance/DAG confirmation | Read-only | Closure-ready; no remaining high/medium findings |
| 2026-07-17 01:48 | GOV-00A contract authority reviewer | Review contractual status, authority, deliverables, and acceptance | Read-only | One high, three medium, and two low findings; all accepted/fixed |
| 2026-07-17 01:48 | GOV-00A regression/maintenance reviewer | Review DAG, drift prevention, validation, scope, and executability | Read-only | Four medium findings; all accepted/fixed |
| 2026-07-17 | GOV-00A contract authority reviewer | Post-fix scaffold confirmation | Read-only | Closure-ready; no remaining high/medium findings |
| 2026-07-17 | GOV-00A regression/maintenance reviewer | Post-fix scaffold confirmation | Read-only | Closure-ready; no remaining high/medium findings |
| 2026-07-17 03:46 | GOV-00A contract authority reviewer | Review contract-first governance slice | Read-only | Two high and three medium findings; all accepted/fixed, post-fix pending |
| 2026-07-17 03:46 | GOV-00A regression/maintenance reviewer | Review enforcement and regression loopholes | Read-only | Two high and four medium findings; all accepted/fixed, post-fix pending |
| 2026-07-17 04:01 | GOV-00A contract authority reviewer | Final post-fix confirmation | Read-only | Closure-ready; no remaining high/medium findings |
| 2026-07-17 04:01 | GOV-00A regression/maintenance reviewer | Final post-fix confirmation | Read-only | Closure-ready; no remaining high/medium findings |

The operator authorized bounded subagent dispatch in the initiating request.
This authority does not authorize scope expansion, branch creation/switching,
commits or pushes, deployment, production mutation, secret access, destructive
git operations, external writes/publication, or broader write ownership unless
the primary agent explicitly assigns that bounded action and existing operator/
repository gates permit it.

## Timeline

- **2026-07-17 00:30 UTC** - Package created from the operator's request for a
  comprehensive Pure UI contract maintenance pass.
- **2026-07-17 00:30 UTC** - Two read-only subagents dispatched for independent
  inventory and governance analysis.
- **2026-07-17 00:42 UTC** - Initial analyses returned; their evidence and
  recommendations were incorporated into the register and ExecPlan before final
  scaffold review.
- **2026-07-17 00:48 UTC** - Both independent reviewers confirmed all findings
  resolved; scaffold validation and review gate closed.
- **2026-07-17** - The exact register closed at 70 units after adding omitted
  ERMiT, RQ Info Details, and DEVAL stateful surfaces; both reviewers confirmed
  closure-ready.
- **2026-07-17** - GOV-00A began bounded execution after the operator required
  contracts to be authoritative and amended before intended UI/RQ code changes.

## Decisions Log

### 2026-07-20 21:23 UTC: Register REM-01 without advancing borrowed owners

**Context**: The reported Omni state defect touches the Project shell plus Omni
scenario and contrast boundaries before their normal package order is ready.

**Decision**: Add REM-01 as the 72nd registered execution unit under the GOV-00A
bounded remediation mechanism. Its exact exclusions are binding.

**Impact**: REM-01 can be reviewed and closed independently. DOM-02, DOM-25A,
and DOM-25B remain planned with all existing dependencies intact.

### 2026-07-21 22:15 UTC: Register REM-02 TTL catalog presentation remediation

**Context**: The operator requested a visible TTL deletion time and dedicated
documentation in the registered Runs catalog surface before its normal package
dependency spine is complete.

**Decision**: Register a finite REM-02 borrower of SURF-06. It may read TTL
metadata only for rows that SURF-06 already authorizes, change the lifecycle
cell, and publish the explanation. It cannot alter TTL behavior, catalog access,
or deletion operations.

**Impact**: REM-02 must complete the same high-security checkpoint, reviews,
and standalone ancestor as every bounded remediation. SURF-06 remains planned.

### 2026-07-17 00:30 UTC: Use an umbrella ExecPlan with bounded child packages

**Context**: A single package covering every controller would exceed the normal
1-4 week work-package boundary and make review and rollback ambiguous.

**Options considered**:

1. One monolithic audit and remediation package.
2. Independent packages with no shared control plane.
3. One umbrella plan that creates, executes, reviews, and closes bounded child
   packages against one standard.

**Decision**: Use option 3. The umbrella owns inventory, standard, sequencing,
coverage, and closeout. Child packages own verified controller contracts and any
small confirmed repairs.

**Impact**: Progress is incremental and reviewable, while the complete inventory
prevents low-visibility controllers from being forgotten.

### 2026-07-17 00:30 UTC: Separate shared invariants from domain contracts

**Context**: `docs/ui-docs/controller-contract.md` already describes singleton,
bootstrap, StatusStream, error, and request invariants, but it does not define
the field-level contract for each controller.

**Decision**: Retain and update the shared invariant document. Add one canonical
contract per domain controller under `docs/ui-docs/contracts/`; do not duplicate
shared rules into every file.

**Impact**: Domain contracts can focus on evidence-bearing mappings while shared
behavior remains maintainable in one place.

### 2026-07-17 00:30 UTC: Require rendered and persistence evidence

**Context**: The WATAR regression occurred because a macro used one token for
both DOM id and submitted name while the server parser expected another key.
Source-level intent alone would not have caught the rendered payload mismatch.

**Decision**: A controller cannot reach `verified` from prose or source reading
alone. Its child package must prove risk-bearing rendered field names and, where
state is persisted, the saved-and-reloaded value.

**Impact**: Contract files describe executable behavior rather than intended
behavior.

### 2026-07-17 00:30 UTC: Dual reviews are independent gates

**Decision**: Reviewer A evaluates contract/source correctness across all
layers. Reviewer B evaluates regression coverage, compatibility, and executable
evidence. Neither reviewer authors the audited change, and an implementer cannot
approve their own fix.

**Impact**: Every package records two raw/verbatim reviewer artifacts and a
separate primary-agent disposition. Reviewer identity and post-fix confirmation
are retained; unresolved high/medium findings block closure.

### 2026-07-17 00:47 UTC: Enforce contract maintenance

**Context**: A coverage check that validates only file existence and headings
cannot detect a later source change that leaves a contract untouched.

**Decision**: Publish a machine-readable source-to-contract manifest. The
change-aware gate compares a base revision, maps changed template/controller/
route/NoDb/RQ paths to contracts and contract tests, verifies the accepted
contract-decision ancestor for intended behavior changes, and requires later
implementation evidence or a package-scoped no-contract-impact attestation
confirmed by both reviewers. Shared macro/helper changes fan out to every mapped
consumer.

**Impact**: The initiative enforces maintenance behavior, not merely initial
documentation coverage.

### 2026-07-17: Freeze coverage and execution authorities separately

**Context**: The initial draft could have left three editable status sources:
the audit register, child-package register, and contracts README.

**Decision**: Before GOV-00A cutover, the audit register is the reviewed coverage
source. GOV-00A creates `contract-obligations.json` as the sole machine
scope/owner/evidence/revision-summary authority. The audit register then becomes
its key-reconciled discovery projection; the child register owns stable
execution boundaries; the contracts README index is generated from the JSON.

**Impact**: Package state, machine obligation status, detailed domain evidence,
and the reader index have distinct owners and deterministic reconciliation.

### 2026-07-17: Expand and pre-split the register to 70 execution units

**Context**: Independent review found omitted inherited security/account pages,
shared producer ownership conflicts, and broad Map, Landuse, Climate, AgFields,
WEPP/SWAT, bootstrap/shell, and Batch boundaries.

**Decision**: Register 3 governance, 39 run-domain, 9 shared-foundation, and 19
stateful-surface units. Give every bootstrap key one primary owner and express
secondary work as facets/consumers.

**Impact**: The plan is longer (24-36 months serial) but each unit has a
credible four-week maximum boundary and an independent review gate.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Stale prose is promoted as authority | High | Medium | Derive contracts from rendered/runtime evidence; record verified commit/date and tests | Open |
| Audit fixes one layer and breaks another | High | Medium | End-to-end field matrix, exact regressions, persistence/reload tests, dual review | Open |
| Scope grows into controller redesign | Medium | High | Faithful-extraction target; confirmed mismatch only; spin off broader work | Mitigated |
| Low-use/config-gated controls are omitted | High | Medium | Complete source-derived register with explicit exclusions and configuration evidence | Open |
| Review becomes ceremonial | Medium | Medium | Independent roles, written findings, dispositions, and re-review after fixes | Mitigated |
| Legacy saved runs use undocumented aliases | High | Medium | Search history/tests, document aliases/conflict precedence, exercise old-state fixtures where available | Open |
| Too many concurrent edits collide | Medium | Medium | One author per child package, read-only reviewers, bounded dispatch log, shared-worktree checks | Mitigated |
| Source changes leave an existing contract stale | High | Medium | Source-to-contract manifest, change-aware gate, reviewed no-impact attestations, shared-helper fan-out | Open |

## Verification Checklist

### Scaffold

- [x] Two independent scaffold reviews complete.
- [x] Every scaffold finding has an explicit disposition.
- [x] `wctl doc-lint` passes for the package and `PROJECT_TRACKER.md`.
- [x] `git diff --check` passes.
- [x] `uk2us` preview produces no unintended authored changes; raw reviewer
  wording is preserved verbatim.

### Pre-GOV-00A Package Register Baseline

- [x] Both independent register reviewers confirmed closure-ready with no
  unresolved high/medium findings.
- [x] Register arithmetic is 3 GOV + 39 DOM + 9 SHR + 19 SURF = 70.
- [x] All 33 bootstrap keys have one primary owner.
- [x] All 56 bundled modules have one producer owner.
- [x] Expanded dependency graph is acyclic from GOV-00 to GOV-99.
- [x] Package documentation and `PROJECT_TRACKER.md` lint pass with zero
  errors/warnings; `git diff --check` passes.

### Current Contractual Register

- [x] GOV-00A is registered as the fourth governance unit.
- [x] Current arithmetic is 4 GOV + 39 DOM + 9 SHR + 19 SURF = 71.
- [x] Every included ledger row has explicit `contractual` scope and a separate
  evidence grade.
- [x] Expanded dependency graph is acyclic from GOV-00 through GOV-00A to
  GOV-99.
- [x] GOV-00A scaffold reviews are dispositioned and confirmed.
- [x] GOV-00A contract-first agent-governance review is dispositioned and
  confirmed.

### Initiative Closeout

- [ ] Canonical standard and audit register are complete.
- [ ] Every in-scope register row is `verified` or has an operator-approved,
  documented exclusion.
- [ ] Every child package has two independent reviews and no unresolved
  high/medium findings.
- [ ] Contract coverage enforcement passes.
- [ ] Change-aware maintenance enforcement passes against the selected base
  revision, including shared producer fan-out.
- [ ] Required frontend, backend, and full-suite gates are recorded.
- [ ] Shared and domain documentation no longer points at missing or archived
  plans as current authority.
- [ ] Active ExecPlan is moved to `prompts/completed/` with outcomes recorded.

## Progress Notes

### 2026-07-17 00:30 UTC: Initial scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Established the umbrella/child-package structure.
- Defined contract coverage from rendered DOM through persistence and reload.
- Made dual independent review and dispatch logging mandatory.
- Selected WATAR/Ash as the pilot because it supplies a recent, concrete field-
  name/value-persistence failure mode.

**Blockers encountered**: None.

**Next steps**:

- Integrate independent inventory and governance findings.
- Complete the two scaffold reviews and disposition.
- Run documentation validation.

**Test results**: Package docs lint passed 9 files with 0 errors/warnings;
`PROJECT_TRACKER.md` lint passed with 0 errors/warnings; `git diff --check`
passed; spelling preview was clean after one package-local normalization.

## Watch List

- **Controller population boundary**: reconcile bundled modules, bootstrap
  registry, Pure templates, and standalone consoles rather than trusting one
  filename convention.
- **WATAR naming**: the canonical contract must distinguish public model labels,
  internal enum values, rendered field names, and persisted NoDb values.
- **Generated bundles**: audit source modules; verify generated bundle parity
  only when source changes.
- **Historical plans**: preserve them as history, but remove current-authority
  links after their replacement contracts exist.
- **Hand-authored Jest DOM**: all current bootstrap controllers have JavaScript
  suites, but many fixtures restate expected markup and therefore cannot prove
  Jinja/macro output. Require rendered-template seam tests.
- **No-impact attestations**: monitor for routine use. They are an exception path
  requiring evidence and both reviewers, not a substitute for contract upkeep.
- **Implementation-first drift**: code and tests are conformance evidence. Reject
  intended UI/RQ behavior changes that do not amend the canonical contract first.

## Communication Log

### 2026-07-17 00:30 UTC: Operator scope and authority

**Participants**: Operator, Codex
**Question/Topic**: Create a comprehensive, iterative ExecPlan for Pure UI
controller contract audit and standardization, with dual-agent review for each
work package and explicit subagent dispatch authority.
**Outcome**: Scope and dispatch authority recorded in `package.md`, the active
ExecPlan, and the reusable child-package prompt.
