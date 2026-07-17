# Tracker - Pure UI Contract Ratification

> Living record for GOV-00A contract-standard ratification.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-17 01:48 UTC
**Current phase**: Scaffold closed; ready for Milestone 1 execution
**Last updated**: 2026-07-17 UTC
**Next milestone**: Execute Milestone 1 authority and lifecycle ratification
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

- None; execution has not started.

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

## Dispatch Log

| Time (UTC) | Agent/role | Scope | Edit authority | Outcome |
| --- | --- | --- | --- | --- |
| 2026-07-17 01:48 | Contract authority reviewer | Challenge binding status, authority, deliverables, and acceptance | Read-only | One high, three medium, and two low findings; all accepted/fixed |
| 2026-07-17 01:48 | Regression/maintenance reviewer | Challenge executability, drift prevention, boundaries, and validation | Read-only | Four medium findings; all accepted/fixed |
| 2026-07-17 | Contract authority reviewer | Post-fix confirmation | Read-only | Closure-ready; no remaining high/medium findings |
| 2026-07-17 | Regression/maintenance reviewer | Post-fix confirmation | Read-only | Closure-ready; no remaining high/medium findings |

## Timeline

- **2026-07-17 01:48 UTC** - Operator clarified that registered items must be
  contractual now and requested a committed ratification package.
- **2026-07-17 01:48 UTC** - GOV-00A scaffolded under the active umbrella.

## Decisions Log

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| `unverified` is treated as optional | High | Medium | Binding `contractual` axis, negative validation, review examples | Open |
| Reader index becomes competing authority | High | Medium | Make it derived; ledger/manifest/domain files retain named authority | Open |
| Schema is too vague for later automation | High | Medium | Exact fields, fixtures, negative tests, GOV-01 handoff | Open |
| Ratification expands into controller audits | Medium | Medium | Documentation/governance-only scope; domain evidence stays in registered children | Mitigated |
| Historical docs retain current-authority wording | Medium | High | Source/reference inventory and explicit redirect policy | Open |

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

## Watch List

- **Vocabulary drift**: reject reintroduction of optional-sounding included
  statuses such as `candidate`.
- **Authority drift**: the reader index is derived, not a parallel status table.
- **Evidence drift**: the obligation registry is the sole grade/revision summary
  authority; promotions and demotions update it atomically with domain evidence.
- **Scope drift**: controller-specific conformance evidence belongs to later
  child packages.

## Communication Log

### 2026-07-17 01:48 UTC: Operator ratification direction

**Participants**: Operator, Codex
**Question/Topic**: Registered Pure UI items must be contractual rather than
candidate; commit the register and scaffold ratification.
**Outcome**: Three-dimension semantics adopted and GOV-00A scaffolded for
independent review and later execution.
