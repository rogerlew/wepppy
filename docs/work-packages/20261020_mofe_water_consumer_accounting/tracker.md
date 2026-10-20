# Tracker: MOFE Water Consumer Accounting

## Status
- Started: 2026-10-20 20:15 UTC.
- Phase: M1 source decision preparation; implementation not started.
- Authority: operator requested execution on 2026-10-20, superseding scaffold-only scope.
- Plan: [Active ExecPlan](prompts/active/mofe_water_consumer_accounting_execplan.md).
- Highest claim: paired-source investigation; physical WAT selected; checkpoint review pending.
## Task board

- [x] Inspect workbook formulas, dates, area basis and missing records.
- [x] Audit direct reducers, downstream models, pass controls and legacy paths.
- [x] Retain workbook hash and actual native counterexample receipt.
- [x] Scaffold package and executable plan; register on project board.
- [x] Validate scaffold docs, links, spelling and whitespace before handoff.
- [ ] M1: resolve runoff provenance/field matrix, current contract amendments,
  ADR, independent reviews and standalone ancestor checkpoint.
- [ ] M2: native report and daily-loader fixes with failing boundary tests.
- [ ] M3: dashboard selected/base and Features Export corrections.
- [ ] M4: Ash/AshPost reconciliation, legacy/diagnostic/tool dispositions.
- [ ] M5: release pairing, actual-project artifact readback, gates and closeout.

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
