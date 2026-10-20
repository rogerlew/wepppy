# Tracker: MOFE Water Consumer Accounting

## Status
- Started: 2026-10-20 20:15 UTC.
- Phase: M1–M5 complete; development acceptance validated.
- Authority: operator requested execution on 2026-10-20, superseding scaffold-only scope.
- Plan: [Completed ExecPlan](prompts/completed/mofe_water_consumer_accounting_execplan.md).
- Highest claim: physical WAT contract ratified at checkpoint `6e689a902`; implementation, artifact, performance and combined regression gates pass.
## Task board

- [x] Inspect workbook formulas, dates, area basis and missing records.
- [x] Audit direct reducers, downstream models, pass controls and legacy paths.
- [x] Retain workbook hash and actual native counterexample receipt.
- [x] Scaffold package and executable plan; register on project board.
- [x] Validate scaffold docs, links, spelling and whitespace before handoff.
- [x] M1: resolve runoff provenance/field matrix, current contract amendments,
  ADR, independent reviews and standalone ancestor checkpoint.
- [x] M2: native report and daily-loader fixes with failing boundary tests.
- [x] M3: dashboard selected/base and Features Export corrections.
- [x] M4: Ash/AshPost reconciliation, legacy/diagnostic/tool dispositions.
- [x] M5: release pairing, actual-project artifact readback, gates and closeout.

## Findings and dependencies

WCA-01 through WCA-05 cover report, dashboard, daily loader, export and AshPost
reducers. WCA-06 through WCA-08 cover TotalWatSed diagnostic columns, legacy raw R
and audit-tool assumptions. Full touch points and classifications are in the
[consumer audit](notes/consumer-audit.md).

Source-version/geometry semantics are an M1 gate: current QOFE aliases Q in the
inspected ordinary model writers, while the workbook uses local QOFE. Obtain
paired artifacts/provenance before adopting a universal conversion. Do not
silently promote an upstream OFE to the outlet on incomplete days.

The workbook remains external; its retained digest, formula text, summaries and
pre-fix native probe are in [readback](artifacts/20261020_audit_readback.json).
Original project repair, model physics, production deployment and unrelated
GeoJSON envelope work are excluded.

## Decisions

2026-10-20: Latest operator instruction narrows this turn to audit and scaffold.
Do not amend canonical contracts or implementation in this scaffold. The closed
ET/Dp package remains immutable; this package describes successor work.

2026-10-20: WAT raw rows, named outlet quantities and internal-transfer diagnostic
sums are different products. Preserve labels/API compatibility and version any
changed persisted results; never apply one area reducer to every numeric field.

2026-10-20: No additional review agents were invoked for this scaffold. The two
independent canonical-contract reviews and final correctness review remain
required execution milestones, not completed review claims.
2026-10-20 execution: Execution authorized. Paired WAT/PASS source evidence
reveals threshold-filtered versus physical runoff; an operator question is
pending before source ratification. See
[contract preparation](artifacts/20261020_contract_decision.md). Preliminary
independent reviews are not final contract approval. No checkpoint commit or
production implementation exists yet.
## Validation

Readback script executed using existing `.venv` dependencies and explicit
installed native library. It confirms P20/Q12.666667/lateral10 vs intended
10/8/4.5, with already corrected ET5/Dp7. No application test suite is warranted
for this documentation-only scaffold; production regression gates are planned.

2026-10-20 20:21 UTC: Scoped lint passes five Markdown files with zero errors
or warnings. Package links resolve; spelling previews have no changes. Retained
receipt checks and whitespace checks pass. Scaffold complete; execution pending.
2026-10-20 execution: Paired-source readback completed with no duplicate daily
identities or unmatched PASS days across 328,800 MOFE terminal days. Package and
both new review/decision documents pass scoped lint; project-board lint,
spelling previews and whitespace checks pass. Preliminary independent reviews
are retained in artifacts/20261020_preliminary_reviews.md. No production code
changed; application/native regression gates remain pending implementation.

2026-10-20: Operator selected physical WAT runoff. ADR-0099 and current contracts
prepared; independent review findings addressed, final approval pending.

2026-10-20 20:45 UTC: Both independent reviewers approve current amendments;
all medium/high checkpoint findings resolved. Standalone commit follows.

2026-10-20 execution update: checkpoint `6e689a902` follows both independent
approvals; upstream schema exception is `wepp-forest` commit `04f1c4d26`.
Native/report, daily loader, dashboard, export and Ash changes are implemented.
Targeted Python suites passed (46 consumer tests, 21 Ash tests, 8 emitted-SQL
tests); frontend passed 987 tests. Correctness review identified duplicate
observation, unavailable PASS reconciliation, historical preservation and
mapping/source provenance gaps; fixes are under regression validation.
The isolated unequal-length H5 six-year replay failed in evap.for in 2025;
five-year bounded daily and hourly-presence replays completed. No original run
or production deployment was modified. Artifact readback, native release pairing,
performance and broad gates remain pending; completion is not claimed.

2026-10-20 21:15 UTC: Both final independent reviews close all high/medium
findings. Native 163, crate 107+17, expanded Python 230, paired/cache/archive 79,
Ash/tool follow-up 32 and frontend 987 tests passed. Live report/CSV/browse and
five artifact downloads pass; selected/base P/Q/ET agree with raw replay oracle.
Actual export service passed four formats on a nonzero wet day. The actual Ash
model/post check uses an explicitly constructed one-hill PASS baseline, not
routed watershed acceptance. Broad gate and complete cold-report target remain
active. Development web workers were gracefully reloaded after paired preflight;
no production process was changed.

2026-10-20 final release validation: native `54d0867` and SHA256
`60b8da3c77aa8465e262b8978ac173ba681d14745de7aec74392db9308c5c5eb`
are paired in startup/image pins. Complete report rebuild meets the single-OFE
budget at 1.88s, with settled means 12.67ms (single)/14.23ms (MOFE). Actual
`AshPost.run_post` facade persistence/catalog/documentation checks pass.
The broad gate's first run stopped on its old SHA assertion after 506 passes;
the assertion was updated and the repeated gate has cleared that test.

Final provenance correction: the full gate exposed same-tick metadata drift.
WAT hashes now precede daily queries and are memoized only inside an Ash batch;
fresh runs rehash. Independent review verified fail-closed replacement and
successful fresh regeneration under deliberately identical source metadata.
Focused boundary/orchestration regressions: 33 passed. Broad resume remains active.

Closeout: resumed broad suite passed 10,703 tests with 126 skips in 1,201.09s.
The two omitted disturbed matrices passed in the preceding full run; final
provenance corrections passed 33 focused tests. Stubtest, stub completeness,
changed exception enforcement, frontend lint/tests and scoped docs checks pass.
All independent high/medium findings are closed. M1–M5 are complete; plan archived.
No push, production deployment or original-project repair. Six-year evap.for
SIGFPE, contour runtime coverage and large-MOFE cold timing remain disclosed
limits in artifacts/20261020_validation.md, not unresolved consumer defects.
