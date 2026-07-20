# Tracker - Pure UI Contract Ratification

> Living record for GOV-00A contract-standard ratification.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-17 01:48 UTC
**Current phase**: Milestone 1 - bounded remediation ancestor commit
**Last updated**: 2026-07-20 21:40 UTC
**Next milestone**: Commit the approved GOV-00A-M1A/REM-01 ancestor
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Ratify authority hierarchy and three-dimension lifecycle vocabulary.
- [ ] Publish the canonical schema, contract template, and derived reader index.
- [ ] Add `contract-obligations.json` and deterministic positive/negative
  governance validation.
- [ ] Reconcile umbrella, developer, and historical-authority links.
- [ ] Complete implementation reviews, disposition, and closeout.

### In Progress

- [ ] Complete Milestone 1 canonical README and obligation registry after the
  contract-first agent-governance slice.
- [ ] Commit the accepted bounded cross-owner remediation mechanism and REM-01 registration.

### Blocked

- None.

### Done

- [x] Created GOV-00A package, tracker, and active ExecPlan from explicit
  operator direction (2026-07-17 01:48 UTC).
- [x] Replaced optional-sounding `candidate` coverage with binding
  `contractual / unverified` semantics in the parent ledger
  (2026-07-17 01:48 UTC).
- [x] Completed two independent scaffold reviews, dispositioned one high, seven
  medium, and two low findings, and received both post-fix confirmations
  (2026-07-17).
- [x] Recorded operator authorization for a bounded cross-owner remediation
  mechanism and REM-01 as its first defect-scoped registration
  (2026-07-20 21:23 UTC).
- [x] Dual-reviewed and accepted GOV-00A-M1A and REM-01 with no unresolved
  high/medium findings (2026-07-20 21:40 UTC).
- [x] Recorded contract-first authority and sequencing in root, WEPPcloud,
  controller, NoDb, rq-engine, and direct RQ agent governance (2026-07-17).
- [x] Dispositioned two high/three medium authority findings and two high/four
  medium regression findings; both reviewers confirmed closure-ready with no
  remaining high/medium findings (2026-07-17 04:01 UTC).

## Dispatch Log

| Time (UTC) | Agent/role | Scope | Edit authority | Outcome |
| --- | --- | --- | --- | --- |
| 2026-07-17 01:48 | Contract authority reviewer | Challenge binding status, authority, deliverables, and acceptance | Read-only | One high, three medium, and two low findings; all accepted/fixed |
| 2026-07-17 01:48 | Regression/maintenance reviewer | Challenge executability, drift prevention, boundaries, and validation | Read-only | Four medium findings; all accepted/fixed |
| 2026-07-17 | Contract authority reviewer | Post-fix confirmation | Read-only | Closure-ready; no remaining high/medium findings |
| 2026-07-17 | Regression/maintenance reviewer | Post-fix confirmation | Read-only | Closure-ready; no remaining high/medium findings |
| 2026-07-17 03:46 | Contract authority reviewer | Review contract-first precedence, sequencing, and authority boundaries | Read-only | Two high and three medium findings; all accepted/fixed, post-fix pending |
| 2026-07-17 03:46 | Regression/maintenance reviewer | Challenge enforceability, missing-contract behavior, and code-first loopholes | Read-only | Two high and four medium findings; all accepted/fixed, post-fix pending |
| 2026-07-17 04:01 | Contract authority reviewer | Final post-fix confirmation | Read-only | Closure-ready; no remaining high/medium findings |
| 2026-07-17 04:01 | Regression/maintenance reviewer | Final post-fix confirmation | Read-only | Closure-ready; no remaining high/medium findings |

## Timeline

- **2026-07-17 01:48 UTC** - Operator clarified that registered items must be
  contractual now and requested a committed ratification package.
- **2026-07-17 01:48 UTC** - GOV-00A scaffolded under the active umbrella.
- **2026-07-17** - Operator required agents to treat contracts as authoritative
  and amend them before intended UI or RQ behavior changes; bounded Milestone 1
  governance execution began.

## Decisions Log

### 2026-07-20 21:23 UTC: Register bounded cross-owner remediation

**Context**: The Omni mod-state defect spans three planned owners whose normal
dependencies are incomplete, while an ad hoc package cannot be canonical.

**Decision**: Ratify a finite borrowed-boundary mechanism and register REM-01.
It inherits `high` security, requires dual review and an ancestor commit, and
does not advance the borrowed owners.

**Impact**: REM-01 may complete only its exact defect boundary before GOV-01;
all unrelated DOM-02/DOM-25A/DOM-25B work remains planned and dependency-gated.

### 2026-07-17 01:48 UTC: Separate obligation from evidence

**Context**: `candidate` could be interpreted by future agents as optional or
non-contractual, even though the register exists to bind maintenance work.

**Decision**: Every included item is `contractual`. `unverified`, `documented`,
and `verified` describe evidence maturity only. Package execution states are a
third independent dimension.

**Impact**: Missing metadata creates required ratification/audit work; it never
removes a surface from contractual scope.

### 2026-07-17 01:48 UTC: Ratify before shared foundations

**Context**: Shared macro, transport, bootstrap, and shell packages need a stable
schema before they can produce canonical contracts.

**Decision**: GOV-00A is inserted between GOV-00 and SHR-01 through SHR-04B.

**Impact**: Shared foundations and WATAR cannot claim contract completion
against an unratified vocabulary.

### 2026-07-17: Contracts precede implementation

**Context**: A same-change documentation rule does not prevent an agent from
editing code first and then rewriting a contract to match observed behavior.

**Decision**: Canonical contracts are normative authority. Agents identify the
applicable contracts before editing and amend them before intended behavior
changes to UI, WEPPcloud/rq-engine routes, or RQ workers. When code violates an
unchanged contract, the code is fixed and regression evidence is added; the
contract is not rewritten to legitimize the defect.

**Impact**: Contract-first sequencing is now an explicit review gate. Missing
domain contracts must be created or ratified through their registered package
before new UI-coupled RQ behavior is introduced.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| `unverified` is treated as optional | High | Medium | Binding `contractual` axis, negative validation, review examples | Open |
| Reader index becomes competing authority | High | Medium | Make it derived; ledger/manifest/domain files retain named authority | Open |
| Schema is too vague for later automation | High | Medium | Exact fields, fixtures, negative tests, GOV-01 handoff | Open |
| Ratification expands into controller audits | Medium | Medium | Documentation/governance-only scope; domain evidence stays in registered children | Mitigated |
| Historical docs retain current-authority wording | Medium | High | Source/reference inventory and explicit redirect policy | Open |
| Code is edited before intent is ratified | High | Medium | Finite authority, ancestor checkpoint, manual dual review, future GOV-01 enforcement | Mitigated; governance slice reviewed |

## Verification Checklist

### Scaffold

- [x] Two independent scaffold reviews complete.
- [x] Every scaffold finding has a primary disposition and post-fix confirmation.
- [x] Parent/child registers and counts are consistent.
- [x] Package documentation and `PROJECT_TRACKER.md` lint pass.
- [x] `git diff --check` passes.

### Package Closeout

- [ ] All included rows are contractual; no included `candidate` status remains.
- [ ] Normative README and contract template are complete.
- [ ] Authority and derived-index rules are deterministic.
- [ ] Agent governance and canonical schema agree that contracts precede UI/RQ
  implementation changes.
- [ ] Positive/negative governance checks pass.
- [ ] Both implementation reviews close without unresolved high/medium findings.
- [ ] Active ExecPlan is moved to `prompts/completed/` with outcomes.

## Progress Notes

### 2026-07-17 01:48 UTC: Initial scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Recorded the operator's contractual-status decision.
- Added GOV-00A to the parent's dependency spine.
- Created the package brief, tracker, and self-contained active ExecPlan.

**Blockers encountered**: None.

**Next steps**:

- Commit the umbrella/register and GOV-00A scaffold.
- Begin Milestone 1 only in a later explicit execution turn.

**Test results**: Six package files, 13 parent files, and
`PROJECT_TRACKER.md` lint clean; 71-unit DAG validation and `git diff --check`
pass.

### 2026-07-17: Contract-first governance slice

**Agent/Contributor**: Codex

**Work completed**:

- Strengthened root change-scope governance so contracts are normative.
- Added explicit contract-first workflows to WEPPcloud routes, Pure UI
  controllers, and rq-engine guidance.
- Updated GOV-00A scope, acceptance, and ExecPlan to preserve this operator
  decision in the authoritative work package.

**Blockers encountered**: GOV-00A still must publish the canonical schema,
template, and obligation registry. Registered DOM/SHR/SURF child packages own
the later per-domain contracts; governance requires their ratification before
behavior changes rather than treating current code as a substitute.

**Next steps**:

- Continue GOV-00A Milestone 1 with the canonical README and obligation registry.
- Continue Milestone 1 with the contracts README and obligation registry.

**Test results**: Root size gate, path-scoped documentation lint for all changed
governance/package files, and `git diff --check` pass. Regression reviewer also
reported frontend lint and 85 Jest suites / 636 tests passing.

## Watch List

- **Vocabulary drift**: reject reintroduction of optional-sounding included
  statuses such as `candidate`.
- **Authority drift**: the reader index is derived, not a parallel status table.
- **Evidence drift**: the obligation registry is the sole grade/revision summary
  authority; promotions and demotions update it atomically with domain evidence.
- **Scope drift**: controller-specific conformance evidence belongs to later
  child packages.
- **Implementation-first drift**: reject changes that infer normative behavior
  from current UI/RQ code or amend contracts only after implementation.

## Communication Log

### 2026-07-17 01:48 UTC: Operator ratification direction

**Participants**: Operator, Codex
**Question/Topic**: Registered Pure UI items must be contractual rather than
candidate; commit the register and scaffold ratification.
**Outcome**: Three-dimension semantics adopted and GOV-00A scaffolded for
independent review and later execution.

### 2026-07-17: Operator contract-first direction

**Participants**: Operator, Codex
**Question/Topic**: Agents must treat contracts as authoritative and amend them
before RQ route or UI code changes.
**Outcome**: Contract-first precedence added to agent governance and GOV-00A;
independent review is required before this slice closes.
