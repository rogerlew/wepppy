# Rainfall/results tracker

Status: **Closed 2026-09-09 Pacific** (2026-09-10 06:50 UTC). Local stage 4 complete.
Execution baseline `2238fc2ce55e91841c6b9795ee58081547726bdd`; original scaffold
baseline `264b54845`. Unrelated dirty quality-report files remain untouched.

- [x] Inventory genuine Wallow sources and verify predecessor/project overlap.
- [x] Freeze local contract and additive compatibility; record ADR-0062.
- [x] Implement bounded predictors/Climate loading and stable event identity.
- [x] Generate event/design/inverse tables and bounded local queries.
- [x] Exercise genuine CLI/NOAA supported catalogs and historical unknown T.
- [x] Focused regression tests: 62 passed; stub checker passed.
- [x] Correctness review: all six medium findings closed for implemented paths.
- [x] Final QA/security reviews pass implemented paths, no medium/high findings.
- [x] Final-policy broad suite: 8,273 passed, 77 skipped, 3,110 warnings (15:12).
- [x] R02 explicitly approved; unavailable sparse ranks implemented and validated.
- [x] Final acceptance, specification/roadmap closeout and plan archival.

## Decisions and evidence

See [decision register](artifacts/decision_register.md),
[compatibility plan](artifacts/compatibility_plan.md),
[source inventory](artifacts/source_inventory.json),
[acceptance summary](artifacts/acceptance_summary.json), and
[validation](artifacts/validation.md). Genuine catalogs produce 30,936 events,
12 selected-source design scenarios and six inverse thresholds. Stored event
rows include three durations for each of 10,312 wet events.

## Outcomes and follow-up

The approved R02 policy retains unsupported positive ranks as unavailable rows
with insufficient_positive_samples, requested rank and sample count. The
unchanged Climate CSV exporter still clamps for parity evidence. Controlled
sparse bundle publication/reopen/query and genuine source hash parity pass.
The completed ExecPlan is archived under `prompts/completed/`.

Production publication, live invalidation, NoDb/RQ integration and UI/dashboard
work remain stages 5–7. Low QA follow-ups concern splitting the long row
validator and adding row context to errors; neither blocks this local delivery.
