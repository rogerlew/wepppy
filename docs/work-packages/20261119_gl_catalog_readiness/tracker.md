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

## Broad validation

The full-suite attempt passed 912 tests before the Browse native CSV fixture
reported a missing converter. A converter with matching source provenance was
borrowed from the existing local test image. The continuation passed the
Browse native CSV fixture and the API groups. It was stopped during the
unrelated Disturbed treatment-soil matrix after 2,374 passes and 124 skips.
The two runs overlap. This is partial broad coverage, alongside the completed
scoped validation. Local WCTL receipts are
`63eb1afe0e84406d9ce00d546cd2d04b` and `c6f8a69002a842dea6bca33493ab8d2c`.
