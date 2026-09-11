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

Contract ancestor: f59d18942. Both independent reviews passed before runtime edits.
Implementation begun: resolver dependency, source-compatible registry mappings,
and narrow historical config-update compatibility.

## SBS timeout and result rendering

The Wallow upload exposed a 55-second Python export path. Native-required
processing and the owner's explicit HTML-in-Details contract are implemented
and validated in the separate `20260910_sbs_native_upload` work package.
Summary contains results; hints contain no error bodies.

## Validation

178 combined Builder tests passed, plus the earlier 15 focused compatibility
cases. Authenticated creation/upload/removal/reload passed on self-imposed-nave;
fair-division exposes the SBS upload. No-SBS landuse and normal Disturbed soil
events produced `wepp/runs/p1.sol`. Named-run repair passed twice and preserved
config/manifest bytes. See artifacts/validation.md for retained evidence.

## Outcome

Completed; plan archived under prompts/completed/. Independent correctness
review passed. Runtime changes are uncommitted; no push or fleet deployment.
