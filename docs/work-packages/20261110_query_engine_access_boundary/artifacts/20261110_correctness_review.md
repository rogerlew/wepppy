# Correctness and user-experience review - Query-engine run access boundary

## Current implementation disposition (2026-11-11 UTC)

Independent local correctness review: PASS; no unresolved medium/high source findings.
See [implementation review dispositions](20261111_implementation_reviews.md).
Browser capacity/environment and deployment gates remain separate. The sections
below retain the initial planning assessment and are not a deployment receipt.


## Metadata

- **Package**: `docs/work-packages/20261110_query_engine_access_boundary/`
- **Initial planning reviewer**: unassigned.
- **Date**: 2026-11-10 Pacific / 2026-11-11 UTC.
- **Scope reviewed**: proposed access, path, browser-token, activation, and error
  behavior; implementation does not yet exist.
- **Commit/branch context**: local `b3786ae7e`; fetched
  `origin/master` `ef5b4e289`.
- **Canonical contracts**: pending M0 amendments listed in the draft decision.
- **Related security artifact**: [security review](20261110_security_review.md).

## User Outcome

- **User goal**: query a run they may inspect through existing dashboards,
  query console, or authorized API client.
- **Success presented to the user as**: unchanged query records/schema and
  functional public/private dashboards after authorization.
- **Failures that may reach the user**: authentication required, forbidden,
  invalid identifier, not found, method not allowed, origin/CSRF denial, stale or
  revoked token, and catalog/query failure.
- **Partial-state behavior**: denied requests leave no new/changed catalog or log;
  authorized catalog preparation remains truthful and recoverable.

## Failure-Class Coverage

The broken assumption is that filesystem resolution implies access. The bounded
consumer and variant assessment is retained in
[the failure-class matrix](20261110_failure_class_matrix.md). Closure requires
disposition of all HTTP handlers and documented run layouts, plus MCP
non-regression. The originally reported ordinary route is not class-wide proof.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Run absent | yes | bounded non-disclosing not-found; no artifacts | Pending |
| Run present but catalog absent/empty | yes | authorized preparation or actionable contracted response | Pending |
| Run populated and public | yes | anonymous contracted read succeeds | Pending |
| Run populated and private, owner | yes | direct browser/API read succeeds | Pending |
| Run populated and private, unrelated | no for caller | bounded denial; no side effects | Pending |
| Supported legacy root | yes | same policy and results as canonical run | Pending |
| Supported grouped/Omni/profile form | yes | documented inherited/group policy | Pending |
| Stale/revoked token | no for caller | bounded reauth/denial without loop | Pending |
| Malformed/path/symlink/cache escape | no | reject before filesystem access | Pending |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Missing identity on private run | Expected | 401/re-auth path per ratified contract | Private access requires identity |
| Unrelated identity | Expected | 403 | Identity is valid but lacks run access |
| Public anonymous read | Expected valid | Existing 200 query result | Public policy is preserved |
| Malformed identifier | Expected hostile/invalid | 400 or 404 without path details | Identifier grammar |
| Missing run | Expected | 404 without ownership/path details | Normal absent state |
| GET forced activation | Expected invalid | 405 | State-changing GET removed |
| Cross-origin cookie activation | Expected hostile | 403 | Browser mutation boundary |
| Internal catalog/query error | Exceptional | Safe correlated error | Full details stay server-side |

Exact statuses remain provisional until M0 ratifies them.

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| Request intent | exact run/config/operation | retained redacted HTTP matrix | Pending |
| Reloaded state | public/owners/session marker | canonical reader output | Pending |
| Generated catalog | correct authorized catalog; none on denial | manifest parse and hash | Pending |
| Consumed dataset | file under authorized run/parent contract | resolved path plus semantic read | Pending |
| Query output | unchanged records/schema/row count | before/after controlled response | Pending |
| User-facing result | dashboard/console works or safe denial | browser trace/screenshots | Pending |

- **Direct unmocked failing boundary**: pending real resolver + JWT + temporary
  filesystem test.
- **Actual-project/environment evidence**: pending forest/equivalent and controlled
  wepp1 fixtures.
- **Highest completion claim supported**: diagnosed.
- **Deployment/recovery still outstanding**: all implementation and rollout.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-F1 | High | Private browser query | A guard without a query-scoped cookie would reject legitimate owners | Current cookie path | Deliver/test HttpOnly query cookie | Open |
| COR-F2 | High | Run layout compatibility | Root-only hardening may reject legacy/group/profile forms or authorize too broadly | Composite spec and `get_wd` | Complete direct variant matrix | Open |
| COR-F3 | Medium | Empty/catalog-absent run | Security ordering must preserve valid authorized catalog preparation | `auto_activate=True` paths | Define and test artifact behavior | Open |

## Verdict

- **Gate status**: fail.
- **Unresolved findings**: High 2; Medium 1; Low 0.
- **Release recommendation**: hold.
- **Reviewer sign-off**: pending independent implementation review.

Correctness approval cannot be inferred from a security denial suite. Final
review must separately prove valid public, owner, legacy, grouped, Omni, profile,
empty, and populated behaviors under production-equivalent configuration.

## M0 contract review checkpoint, 2026-11-11

Independent design review passed; see [contract review disposition](20261110_contract_reviews.md).
This closes design findings only. The runtime findings and release hold above
remain open. Exact operator ratification and ancestor commit are pending.
