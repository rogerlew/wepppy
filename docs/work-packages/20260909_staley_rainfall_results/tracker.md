# Rainfall/results tracker

Status: scaffolded, not executing; 2026-09-10 05:15 UTC.
Baseline `264b54845`. Existing dirty `code-quality-report.json` and
`code-quality-summary.md` are unrelated and must be preserved.

- [x] Review completed M1 interface, validation and authentic Wallow acceptance.
- [x] Inspect Climate parquet/frequency export and Weibull rank precedent.
- [x] Scaffold package, canonical proposal and decision gates.
- [ ] Inventory real Climate fixtures and settle rainfall/results contract/ADR.
- [ ] Implement bounded input adapters and event/scenario identity.
- [ ] Generate event/design/threshold results and local query interface.
- [ ] Validate real outputs, performance, focused/full tests and independent reviews.
- [ ] Synchronize specification/roadmap and archive plan with actual outcomes.

## Decisions and discoveries

2026-09-10 05:15 UTC: M1 local composition is complete; T/F/S can be unavailable
independently. The existing scenario helper consumes an in-memory bundle and
explicit accumulations; it is not a safe persisted-bundle loader or event adapter.
Climate frequency output rounds to two decimals, emits missing-column zeros and
clamps out-of-range rank indices. Year count uses distinct wet-event years.
These must be explicit in the new contract, not quietly changed by an adapter.

## Next handoff

Start with the [review](artifacts/predecessor_review.md) and
[decisions](artifacts/decision_register.md), then the active ExecPlan. No runtime
changes or new test results exist for this scaffold. Do not reopen completed
predictor or slope packages; promote any new durable decisions into current docs.
