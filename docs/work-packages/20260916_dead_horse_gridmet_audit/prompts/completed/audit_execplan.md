# Audit the GridMET rerun

This ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

## Purpose / Big Picture


Explain what changed in the new M3 report and whether calendar-dated GridMET
improves the comparison with the paper's observed Dead Horse Creek response.

## Progress


- [x] Identify new and prior attempts, 2026-09-17 UTC.
- [x] Check all probabilities, rainfall linkage, predictor identity and report.
- [x] Extract August 5–12, 2021 and compare with prior design values.
- [x] Retain findings, verify preservation, lint and close.

## Context and Orientation


Run root: /wc1/runs/th/thespian-cleanness. New attempt is
f493a714df9d4fbfbfd4370c46ad54f8. Prior attempt is
0a34c96cd0dc4e6bb7bb7780d8f8915b. Saved tables and manifests live in
postfire_debris_flow/attempts/<id>/results. New climate is GridMetPRISM,
calendar labels 1980–2025; previously PRISM, simulation labels 1–100.
M3 uses fixed terrain T, burn fraction F and thickness S. P50 is the rainfall
intensity yielding 50% conditional probability and is independent of the
frequency/rainfall record if these predictors do not change.

## Plan of Work


Use retained scripts in artifacts with wctl exec -T weppcloud python. Hash
accepted inputs/results before reads; independently evaluate published M3
coefficients and check rainfall rows/ranks. Extract every wet day in the stated
historical window, retaining dry-day daily data too. Compare original GridMET
daily values with CLIGEN daily rainfall without equating generated peaks with
gauge measurements. Use normal authenticated browser GET for saved report.

## Validation and Acceptance


All rows match independent arithmetic and accepted source rainfall or produce
explicit findings. Capture predictor and design deltas, report current identity,
event-window table and preservation checks. No production tests needed for
read-only evidence. Lint the package and update tracker before handoff.

## Surprises & Discoveries


Initial read: 46 calendar years and 8,381 wet events; T/F/S and coverage unchanged.

## Decision Log


Preserve the closed first audit; create this follow-up for the owner's new run.
Daily observed-mode data does not prove observed 15-minute rainfall.

## Outcomes & Retrospective


Complete: all saved numerical checks pass, authenticated report and downloads
agree, 266 protected files unchanged. August 5–12 precipitation is zero in both
source and CLI. Currentness is false solely due to active CLI ctime mismatch;
cause and acceptance-time content equality are not established. Findings retain
these limitations; no production change or rerun.

## Idempotence and Recovery


Never write to the run. Retain failed diagnostics. If the accepted identity
changes concurrently, record it and evaluate the captured immutable attempt.

## Artifacts and Interfaces


Existing raster/parquet readers and Python arithmetic only. Artifacts are local
to this package; no production interface changes. Credential values are never
retained. Current-source preservation is separate from changes made by the user.

Completed 2026-09-17 UTC: follow-up audit evidence and limitations retained.
