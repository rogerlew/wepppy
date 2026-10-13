# PUUX-01 tracker

Status: **Closed 2026-10-13 — Forest complete; production not deployed.**
Branch: master. Contract checkpoint: `2f9f94443`. Runtime: `ed80608fe`.
Final reviewed source/test candidate: `3df2ec482`.

## Task board

- [x] Static review and operator Runs-page/ordinary-dashboard decisions captured.
- [x] PUUX-01A: GL Dashboard moved to More for ordinary authorized viewers.
- [x] M0: canonical contracts, two independent reviews and ancestor checkpoint.
- [x] M1: discovery notice and immediate activation with real Profile refresh.
- [x] M2: internal details, panel orientation, report guard and registered guide.
- [x] M3: regression coverage, real Forest evidence, cleanup and final reviews.
- [x] Closeout and rollout/limitation handoff documented.

## Authority and decisions

The operator selected Runs discovery for viewers lacking PowerUser/Admin/Root;
Dev alone still sees it. The PowerUser Panel stays restricted. GL Dashboard is
ordinary authorized project navigation. Immediate activation, legacy access and
separate internal memberships retain the existing grant/statement contracts.

Durable authority and rationale: `docs/ui-docs/contracts/poweruser-onboarding-contract.md`
(Discovery and audience; Profile and completion; Delivery and recovery), and
`docs/schemas/feature-access-governance-contract.md`. New guide registration uses
Advanced and Operations; protected documentation navigation is unchanged.

## Validation and handoff

- Broad coverage: 10,723 distinct passed, 126 skipped across segments; not a
  clean single full-suite run. Two missing-viewer fixtures corrected; unchanged
  JWT and catalog timing failures pass module reruns.
- Frontend: 118 suites/980 tests passed. Existing climate-test lint remains.
- Forest: actual grant, duplicate idempotence, durable acceptance/role readback,
  Profile reload/focus, destination access, role matrix and internal denial pass.
- Final served guide returns 200; notice is 136px at desktop; Technical details
  opens; served JS matches source. Desktop/narrow screenshots retained.
- All 18 disposable accounts deactivated; sessions and project associations
  removed; acceptance history retained (3 before/3 after).

[Validation/rollout](artifacts/2026-10-13_validation.md),
[correctness review](artifacts/2026-10-13_correctness_review.md),
[security review](artifacts/2026-10-13_security_review.md), and
[source identity](artifacts/source-identity.json) provide the receipts.
Production rollout is separate and requires rebuilding the usersum index.
No push or production deployment was performed during PUUX execution.
