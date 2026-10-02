# Milestone one correctness review

## Metadata

Reviewer: `/root/contract_correctness`, independent read-only review, 2026-10-01.
Base revision: `6cb552943`; accepted contract ancestor: `d3639f970` (ancestry
verified). Reviewed the working-tree account schema/store/evaluator, app models,
migration, registry fields/mappings and `tests/weppcloud/test_feature_access.py`.
The author applied fixes; the reviewer confirmed the final source/test changes.

## Valid-state coverage

Absent membership denies restricted actions without affecting ordinary anonymous
creation or non-embargoed inspection. Empty and legacy account schemas upgrade
without fabricated membership/acceptance or role changes. Populated memberships
respect expiration, review-only dates and current statement acknowledgment.
Legacy Dev/Root entitlement remains for role-or-group features; group-only
features deny those roles without membership. Supported Culvert integration
inputs still require existing resource authorization. Malformed grants, unknown
users/groups, invalid dates, unauthorized actors and database failures do not
commit partial state or grant access.

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| M1-C01 | Medium | Contrast dependency failures collapsed database/configuration errors into an entitlement denial | Preserve explicit unavailable/configuration reasons; direct regression drops the membership table between primary/dependency checks. Reviewer confirmed closed |
| M1-C02 | Medium | Expiry sampled before connection/row-lock waits could be stale | Database wall-clock membership predicate; write timestamp and future-expiry validation after locks; real locked-row regression with controlled clock. Reviewer confirmed closed |

The author also caught and corrected contrast-derived PATH-CE inspection: it
requires contrast read entitlement without unnecessarily requiring PATH-CE
execution membership. Reviewer confirmed the correction and regression test.

## Evidence and verdict

Initial post-fix isolated PostgreSQL suite: **26 passed**; final account/registry regression suite including the metadata guard: **180 passed**. Earlier focused run including
registry and existing route/interface tests: **293 passed**. The reviewer read
source/tests and checked whitespace but did not independently rerun these tests.
Real Flask app import/readback confirms all four ORM models are registered.
Full-suite outcome is recorded in the tracker.

Final reviewer verdict: M1 accepted, **zero unresolved High/Medium findings**.
This milestone implements the substrate; HTTP adapters, UI and protected data
consumers remain unwired. It is not runtime end-to-end or deployment acceptance.

Final metadata-guard readback: the correctness reviewer confirmed required-field checks on primary/dependency specs and preserved ordinary omissions; no new findings. The final targeted suite passed 180 cases.
