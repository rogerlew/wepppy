# Preserve project access during fork recovery

Maintain this plan under the [ExecPlan guidance](../../../../prompt_templates/codex_exec_plans.md).

## Purpose

An authorized user can open the destination project URL, see what happened to
the fork, and recover access to results when they are ready.

## Progress

- [x] Record the production failure and proposed contract.
- [ ] Complete the independent reviews and commit the contract ancestor.
- [ ] Implement and exercise the project status, optional cookie, and catalog wait.
- [ ] Record production-equivalent verification limits and independent code reviews.

## Surprises & Discoveries

- Flask rendered the project but its after-request query hook turned an expected
  lifecycle conflict into HTTP 500. The WEPP simulation was already complete.

## Decision Log

- 2026-11-20. Use the existing fork receipt to describe lifecycle status. Use
  the existing catalog handshake only for controls that need Query Engine.

## Outcomes & Retrospective

Pending implementation and verification.

## Implementation and acceptance

Wire the receipt and core file checks into the existing project route. Reuse
the rendered project shell for readable destinations and show a status view
for incomplete copies. Handle the exact query cookie conflict in its shared
hook. Use the existing browser catalog client from the WEPP loss controls.
Run focused Flask, Query Engine and controller tests, documentation lint, and
frontend gates. Exercise an actual Flask response with authorized and denied
viewers, and confirm unchanged query denial and successful cookie issuance.
