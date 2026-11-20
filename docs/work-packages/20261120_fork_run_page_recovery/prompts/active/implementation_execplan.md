# Preserve project access during fork recovery

Maintain this plan under the [ExecPlan guidance](../../../../prompt_templates/codex_exec_plans.md).

## Purpose

An authorized user can open the destination project URL, see what happened to
the fork, and recover access to results when they are ready.

## Progress

- [x] Record the production failure and proposed contract.
- [x] Complete the independent reviews and commit the contract ancestor as `7aab6d3b1`.
- [x] Correct the live dashboard contract in `1993ef29d` after two reviews.
- [x] Implement project status, optional query cookie, and dashboard availability.
- [x] Complete focused route, template, Query Engine, Redis, and JavaScript checks.
- [x] Record verification limits and independent reviews.

## Surprises & Discoveries

- Flask rendered the project but its after-request query hook turned an expected
  lifecycle conflict into HTTP 500. The WEPP simulation was already complete.
- The production URL preprocessor resolved the destination before the view ran.
  Focused Flask dispatch reproduced the preprocessor's 404 for an absent root.
  The project view now resolves only after it checks the fork state.

## Decision Log

- 2026-11-20. Use the existing fork receipt to describe lifecycle status.
  The live embedded project map has no query-backed WEPP result selectors.
  Keep catalog readiness with the existing GL Dashboard and control its two
  project-link entry points while a fork is protected.

## Outcomes & Retrospective

Local Flask dispatch with disposable Redis exercised 15 recovery scenarios.
The focused Python selection passed 612 tests. The existing frontend suite
passed 1,109 Jest tests and nine Node tests. The full pytest preflight found
both native parser artifacts missing. Runtime rollout and verification of a
full model-backed fork page remain pending.

## Implementation and acceptance

Wire the receipt and core file checks into the existing project route. Reuse
the rendered project shell for readable destinations and show a status view
for incomplete copies. Handle the exact query cookie conflict in its shared
hook. Show the existing dashboard link or a fork explanation through the
project header and the existing authorized WEPP Reports fragment.
Run focused Flask, Query Engine and controller tests, documentation lint, and
frontend gates. Exercise an actual Flask response with authorized and denied
viewers, and confirm unchanged query denial and successful cookie issuance.
