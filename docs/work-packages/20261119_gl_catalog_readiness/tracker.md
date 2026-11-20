# GL catalog readiness tracker

## Progress

- [x] 2026-11-20 00:40 UTC. Scaffolded the package, draft decision, scoped test matrix and execution plan.
- [x] Approved for execution by the operator. Two reviewers accepted the amended contract. See [review dispositions](artifacts/20261120_contract_review_disposition.md).
- [x] Committed the reviewed standalone checkpoint at `fdba3295c`.
- [x] Add and run scoped server, admission, client and browser tests. Query Engine/RQ passed 371 with two skips. Route rendering passed 292. Frontend lint, 1,097 Jest tests, nine Node tests, and two Playwright smoke tests passed.
- [x] Verify real publication and both dashboards against the result fixture. Retain [correctness](artifacts/20261120_correctness_review.md) and [security](artifacts/20261120_security_review.md) reviews.
- [ ] Verify production-equivalent worker and scheduler readiness before separately authorized rollout.

## Decisions

- **2026-11-20 00:40 UTC.** Use a readiness handshake before GL query fan-out and a pending response for late invalidation. The operator requested the user-visible handshake. The reviewed wire and failure matrix is in checkpoint `fdba3295c`.
- **2026-11-20 00:40 UTC.** Reuse current catalog workers and scheduler. Keep work isolated on `task/gl-catalog-readiness`, based on the available `origin/master` revision.

## Handoff

The active plan is [implementation_execplan.md](prompts/active/implementation_execplan.md). The handshake and scoped tests passed locally, including a disposable NFS browser replay. The production rollout and affected-run verification are pending.
