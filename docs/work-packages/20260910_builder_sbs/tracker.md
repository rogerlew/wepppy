# Tracker

## Progress

Contract prepared; independent review pending. Runtime edits have not started.
Starting revision: 595816476. Preserve ongoing M1/timeout and quality-report edits.

## Decisions

2026-09-10 UTC: user requests SBS support on all Builder-created projects and
stops full-suite testing. Required dependency at new creation; explicit repair
of named existing project, no silent fleet-wide mutation.

## Validation

Pending targeted builder snapshot/update/initialization tests and external
authenticated upload/removal on a disposable Builder project; verify control
presence on fair-division without publishing a synthetic map there.

Owner clarification: always enable normal Disturbed behavior, including soil
adjustments without an SBS map. No SBS-only runtime flag. ADR-0064.

Correctness review identified missing burn classes in plain management mappings.
Contract and ADR now require the existing source-compatible Disturbed mappings;
normal landuse/soil events remain unchanged. No new SBS-only guard is introduced.
