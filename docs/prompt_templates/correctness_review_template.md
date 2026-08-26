# Correctness and User-Experience Review - [Package Title]

> Use this artifact for production behavior changes and incident-driven fixes.
> Correctness review owns valid user states and user-reachable failure behavior;
> security review is additional and cannot substitute for this gate.

## Metadata

- **Package**: `docs/work-packages/YYYYMMDD_slug/`
- **Reviewer**: [Name/agent]
- **Date**: YYYY-MM-DD
- **Scope reviewed**: [Files/routes/jobs/user workflows]
- **Commit/branch context**: [SHA or branch]
- **Canonical contract(s)**: [Exact path and section]
- **Related QA/security artifacts**: [Paths or N/A]

## User Outcome

- **User goal**: [What the user is trying to accomplish]
- **Success presented to the user as**: [Observable result]
- **Failures that may reach the user**: [Error classes/messages/states]
- **Partial-state behavior**: [What remains after failure and how it is surfaced]

## Valid-State Matrix

Enumerate system state independently from request/input combinations. Do not
claim exhaustive coverage unless both matrices are covered.

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Resource absent / feature never used | yes/no | create, no-op, or explicit failure | test/path |
| Resource present but empty | yes/no | expected result | test/path |
| Resource populated | yes/no | expected result | test/path |
| Supported legacy state | yes/no | expected result | test/path |
| Malformed or hostile state | no | bounded explicit failure | test/path |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| [condition] | expected/exceptional | [result] | [contract/rationale] |

Expected absence of optional state must not become an internal exception unless
the canonical contract explicitly requires it. Every newly reachable exception
needs a contract-based justification and regression evidence.

## Review Checks

- [ ] Canonical intent is named; implementation and tests are not treated as
  authority for user behavior.
- [ ] Absent, empty, populated, supported legacy, and hostile states are either
  tested or explicitly ruled out by the contract.
- [ ] Input/flag combinations and stored/filesystem state combinations are
  reviewed as separate dimensions.
- [ ] At least one direct, unmocked test exercises each changed safety or
  persistence boundary.
- [ ] Mocks do not replace the function or boundary where the production
  failure can occur.
- [ ] Security controls prove noninterference with every valid state in
  addition to rejecting hostile states.
- [ ] Partial success, readiness, retry, and cleanup semantics are explicit.
- [ ] Error text and recovery guidance are understandable and actionable.
- [ ] Existing user workflows remain compatible unless an approved contract
  explicitly changes them.
- [ ] Claims such as "exhaustive", "complete", or "all combinations" identify
  every covered dimension and are supported by evidence.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | High/Medium/Low | [surface] | [finding] | [path/test] | [action] | Open/Resolved |

## Verdict

- **Gate status**: `pass | fail`
- **Unresolved findings**: High [count]; Medium [count]; Low [count]
- **Release recommendation**: `ship | ship-with-conditions | hold`
- **Reviewer sign-off**: [Name/agent and date]
