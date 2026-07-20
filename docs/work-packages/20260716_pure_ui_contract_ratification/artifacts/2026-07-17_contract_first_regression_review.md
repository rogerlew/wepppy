# Contract-First Regression and Maintenance Review

**Reviewer**: `/root/contract_governance_review`
**Mode**: Read-only
**Date**: 2026-07-17 UTC
**Initial verdict**: Not closure-ready

## Findings

### H1 - Canonical authority was undefined before registry cutover

The global rule could promote stale prose even though the GOV-00A schema,
registry, and domain contracts are not yet ratified. The tracker also incorrectly
assigned future per-domain contract publication to GOV-00A.

Required disposition: define canonical authority as a finite ratified set,
publish an explicit pre-cutover allowlist and registered ratification path, mark
unlisted docs as history/evidence, and correct GOV-00A versus child ownership.

### H2 - Ordering lacked a verifiable pre-code gate

Same-change files and review prose could not prove that a contract was accepted
before implementation. Operator approval and dual review were not consistently
required before code edits.

Required disposition: require a pre-implementation decision checkpoint with base
revision, applicable contracts, normative delta, rationale, compatibility and
security impact, classification, operator decision, and two reviews. Commit the
accepted checkpoint/contract revision as an ancestor before implementation.
Define a bounded urgent-restoration path and preserve the distinction in GOV-01.

### M1 - Cross-contract conflicts lacked resolution

No rule defined what happens when applicable domain and cross-cutting contracts
disagree.

Required disposition: block implementation, record the conflict, identify owners,
reconcile/cross-link all contracts, and require operator plus dual-review
disposition. Add deterministic negative evidence when representable.

### M2 - Enforceable scope was incomplete

Root/subsystem guidance omitted parts of the browser-to-RQ boundary, including
shared helpers/macros, NoDb persistence/reload, and direct `wepppy/rq/` work.

Required disposition: align governance across the full boundary and add direct
RQ worker guidance.

### M3 - Active plan and tracker state conflicted

Root AGENTS still declared no active work-package ExecPlan, and the tracker
misassigned per-domain contract creation to GOV-00A.

Required disposition: point root guidance to GOV-00A with umbrella coordination
and correct package ownership.

### M4 - Broad documentation maintenance was weakened

The initial patch replaced the repository-wide same-change documentation rule
with a narrower UI/RQ intent rule.

Required disposition: restore the broad user/operator/developer documentation
obligation and keep contract-first ordering additive.

## Initial Validation

The reviewer reported path-scoped documentation lint and `git diff --check`
clean. Frontend lint plus 85 Jest suites and 636 tests also passed. The default
staged-only documentation command initially selected no files, so the reviewer
reran explicit path-scoped lint.

## Post-Fix Confirmation

At 2026-07-17 04:01 UTC the reviewer reported closure-ready with no remaining
high or medium findings. The final pass confirmed both normal and urgent paths
require a committed pre-code ancestor, with the urgent ancestor recording the
unchanged contract, strict classification, regression plan, explicit operator
authorization, and UTC timestamp. Missing commit authority blocks work; both
post-implementation reviews remain mandatory.
