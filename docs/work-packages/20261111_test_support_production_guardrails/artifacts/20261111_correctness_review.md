# Correctness and user-experience review - Test-support production guardrails

**Status**: Scaffold; review not started
**Package**: `docs/work-packages/20261111_test_support_production_guardrails/`
**Reviewer**: contract_correctness (reviewer)
**Date**: 2026-11-12 UTC
**Starting revision**: `cfa1fc6e79ad1db643bd70c95bc8d44dc7083367`

## User Outcome

- **User goal**: authorized agents run existing WEPPcloud smoke provisioning and
  cleanup with no manual authentication ceremony, while production cannot
  expose support routes.
- **Success presented as**: `wctl run-playwright` performs authenticated
  ping/create/load/delete in non-production; production route inventory is
  empty.
- **Potential user-reachable failures**: invalid/unknown profile startup error,
  production-support startup error, token mint failure, 401/403 support denial,
  smoke cleanup failure, or missing combined-readiness evidence.
- **Partial-state behavior**: token mint/auth denial creates no run; create
  failure cleans its partial run; delete failure remains visible and leaves the
  target for authorized cleanup.

## Failure-Class Coverage

The shared failure is documented in
`20261111_failure_class_matrix.md`. Final review must verify every route,
registration/configuration variant, wctl/Playwright client, and deployment
variant. A unit test of one handler cannot close the configuration class.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Profile absent, feature unused | yes | production default; routes absent | pending |
| Production profile, flag false | yes | normal startup; routes absent | pending |
| Production profile, flag true | no configuration | actionable startup failure before registration | pending |
| Development/test, flag false | yes | normal startup; routes absent | pending |
| Development/test, flag true, valid JWT | yes | existing ping/create/delete behavior | pending |
| Development/test, flag true, missing/invalid JWT | expected denial | 401, no parse/filesystem side effect | pending |
| Development/test, valid JWT missing scope | expected denial | 403, no side effect | pending |
| Unknown profile | no configuration | actionable startup failure | pending |
| Existing direct anonymous smoke client | supported legacy workflow requiring migration | wrapper/helper supplies bearer automatically | pending |
| Token mint unavailable | expected operational failure | wrapper stops before ping/npm with actionable text | pending |
| Created run partially initialized | exceptional | existing bounded cleanup and visible failure | pending |
| Delete fails | exceptional | explicit failure; target remains diagnosable | pending |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Missing/invalid bearer | expected | 401 without side effect | bearer contract |
| Valid bearer lacking scope | expected | 403 without side effect | least privilege |
| Production plus support true | expected configuration rejection | startup error naming profile/flag | fail-closed invariant |
| Unknown profile | expected configuration rejection | startup error listing valid values | typo must not weaken profile |
| Token mint failure | expected operational failure | wctl exits before test with actionable error | no anonymous fallback |
| Cleanup filesystem failure | exceptional | explicit test failure and retained run ID | artifact correctness |

## Generated Artifact Evidence

Model/report artifact validation is not applicable. Disposable run directories
are created and deleted, so final review must read back the actual directory and
returned run page rather than relying on response status alone.

- **Direct unmocked boundary**: pending actual configured Flask/wctl smoke.
- **Actual environment evidence**: local non-production stack required; forest
  or production-equivalent work remains a separately authorized deploy plan.
- **Highest completion claim supported**: scaffolded.

## Review Checks

- [ ] Canonical profile/test-support contract is ratified first.
- [ ] Every valid state remains usable and every invalid state is explicit.
- [ ] Cookie-only and bearer-only CSRF behavior is direct-tested.
- [ ] Denial cases assert no run/filesystem side effect.
- [ ] Authorized create/load/delete reads back run and cleanup results.
- [ ] wctl error text is actionable and token-free.
- [ ] Direct npm/Playwright compatibility is documented.
- [ ] F1-F7 readiness language matches actual evidence grades.
- [ ] No production deployment or incident-resolution claim is made.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | TBD | TBD | Populate during independent review | TBD | TBD | Open |

## Verdict

- **Gate status**: fail until review is complete.
- **Unresolved findings**: High 0 known; Medium 0 known; scaffold placeholder open.
- **Release recommendation**: hold implementation closeout.
- **Reviewer sign-off**: pending.


## Implementation review disposition

Reviewer: `contract_correctness (reviewer)`; read-only independent review on 2026-11-12 UTC,
against the scoped implementation after contract ancestor `21a75b794`.

Native test discovery and custom URL-prefix medium findings were fixed and independently rechecked. No open medium/high code findings. Preliminary traceback-local exposure was retracted after verifying installed Typer defaults; explicit no-locals behavior now pins the intent.

Verdict: source review approved; release acceptance HOLD. Real NFS deletion
returned 200 with a remaining directory. Full automatic browser lifecycle and
artifact token scan remain unproven. See [validation](20261112_validation.md).
The final combined revision and F6 M4 remain unavailable; this is not final
F1-F7 release approval.
