# Schema-2 calendar selection tracker

**Status**: Closed 2026-10-21; development fix implemented and validated.

## Completion

M1–M4 complete. The production bridge supplies requested year/day; the reader
loads the matching record without consuming schema-2 padding as another date.
The writer, file format and calendar policy are unchanged. Schema1 compatibility,
ordinary/leap/final-day delivery, invalid requests, cursor recovery and legacy
1900-366 are covered by the fresh reader regression suite.

Two 44-year controlled cases and the 28-hillslope, 43-year real project complete.
Every requested day passes volume readback. All 196 real hillslope products match
baseline; all 388 real ordinary files match corrected observations off/on.
Independent correctness and secondary source QA pass.

## Evidence and limitations

See [validation and commands](artifacts/validation.md),
[review](artifacts/correctness_review.md), [provenance](artifacts/provenance.json)
and per-case `artifacts/*-validation.json`. Native pytest: 193 passed, one missing
external fixture failure. Full FPM has documented preexisting storage-test/API
and cached-build limitations; fresh baseline/candidate dispositions are retained.
Full physical-domain conservation is not established.

Authority, compatibility rationale and acceptance are recorded in the completed
[ExecPlan](prompts/completed/hbp_calendar_execplan.md#decision-log). The prior closed
investigation remains immutable. No release, vendoring, deployment or live-run
mutation. Jackson's ASCII `wepp_261010` century issue is the separate next topic.
