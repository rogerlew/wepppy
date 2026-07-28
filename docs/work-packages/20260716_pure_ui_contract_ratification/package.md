# Pure UI Controller Test Convention

**Stable ID**: GOV-00A
**Status**: Closed (2026-07-28)
**Timezone**: UTC

## Overview

Publish the minimum shared convention needed to test and repair Pure UI
controllers one at a time. The convention separates intended behavior from
observed behavior, requires actual rendered evidence, and keeps tooling and
review proportional to demonstrated controller work.

Earlier GOV-00A remediation milestones remain historical authority for REM-01
through REM-05. They do not require the rejected registry/enforcement platform.

## Objectives

- Define the risk-bearing field/action values a controller test records.
- Require actual Jinja render coverage where templates or macros define fields.
- Require only the downstream tests applicable to a value.
- Establish tests-first, minimal, backward-compatible mismatch repair.
- Define a strict simplicity budget for reusable test helpers.
- Unblock DOM-01 without shared-foundation or GOV-01 prerequisites.

## Scope

### Included

- A concise convention in `docs/ui-docs/controller-contract.md` or one small
  linked current-authority document.
- Reconciliation of the umbrella roadmap, child prompt, register, tracker,
  active ExecPlan, and `PROJECT_TRACKER.md`.
- Preservation of completed REM-01 through REM-05 governance history.
- Documentation validation and one proportional independent review.

### Explicitly Out of Scope

- `contract-obligations.json`.
- Generated contract indexes.
- Source/contract/test manifests.
- Base-revision diff or change-classification engines.
- Shared-consumer dependency graphs.
- No-impact attestations or machine ancestry checks.
- New CI workflows, receipts, recovery, or attestation systems.
- Auditing or patching a controller; DOM-01 performs the first iteration.

## Controller Test Convention

For each risk-bearing field or action, record only applicable values:

- intended DOM id, submitted name, type, token, and default/state;
- parser key/type/default/alias;
- persisted attribute and reload value;
- RQ input or lifecycle only when the value reaches RQ; and
- exact actual-render and focused downstream tests.

Tests precede production repair when practical. Each confirmed mismatch receives
the smallest compatible patch. Shared code changes require direct-consumer
coverage; otherwise they are narrowed or deferred.

## Tooling and Value Rules

- Direct assertions first.
- Extract a helper after at least two repeated tests.
- Helpers are stateless, test-only, smaller than the tests using them, and
  expose field mappings in failures.
- No separate tooling package.
- Review value after five controllers using mismatches found, regression
  sensitivity, runtime, helper size, false tooling failures, and operator time.
- GOV-01 remains deferred without measured need and explicit approval.

## Success Criteria

- [x] Current guidance explains the one-controller loop without a registry.
- [x] Actual-render evidence is mandatory for template-defined fields.
- [x] Downstream testing is required only where the field/action applies.
- [x] Production patches are tests-first, minimal, and compatibility-preserving.
- [x] Test/documentation work begins with security impact `none`.
- [x] One independent correctness review applies to a production patch; extra
  security/review gates follow actual risk.
- [x] Stop-loss rules and the five-controller value review are documented.
- [x] DOM-01 is unblocked without SHR or GOV-01 completion.
- [x] Documentation lint, spelling preview, references, and diff checks pass.

## Dependencies

- **Parent**:
  `docs/work-packages/20260716_pure_ui_contract_standardization_c/`
- **Blocks**: only publication of the concise convention before DOM-01 begins.
- **Does not block**: speculative shared packages or a maintenance platform.

## Security and Parameterization

- **Security impact**: `none`; documentation and test convention only.
- **Dedicated security review**: `no`.
- **Parameterization change**: `no`.

Actual controller patches repeat security and ADR triage based on the files and
behavior they change.

## Risk Assessment

The primary risk is process expansion. The simplicity budget, controller-first
ordering, direct-assertion rule, stop-loss conditions, and measured value review
keep governance subordinate to executable regression coverage.

## References

- `docs/ui-docs/controller-contract.md`
- `docs/standards/contract-first-change-standard.md`
- `docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/controller_contract_test_roadmap.md`
- `docs/work-packages/20260716_pure_ui_contract_standardization_c/prompts/active/controller_contract_audit_iteration_prompt.md`
- `/workdir/openWEPP/docs/work-packages/20260723-testgate-incompatible-recovery-receipt-001/artifacts/testgate-trajectory-and-value-assessment.md`

## Deliverables

- Concise current-authority controller test convention.
- Reconciled one-controller roadmap and child protocol.
- DOM-01 start condition.
- Validation and proportional review evidence.
