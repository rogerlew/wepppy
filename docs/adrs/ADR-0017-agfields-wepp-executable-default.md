# ADR-0017: AgFields WEPP Executable Default

Status: Accepted
Date: 2026-07-10

## Context

The repaired `sacral-self-discipline` AgFields sub-field 3733 input contains 17
years of imported agricultural managements. The exact normalized replay
completes with `wepp_dcc52a6`, while `wepp_260430` and `wepp_260606` both reach
simulation year 2 and terminate with SIGFPE at `frcfac.for:184`. AgFields
previously inherited the parent watershed's WEPP executable and offered only a
Maximum workers control in its Stage 4 run options.

## Decision

Give AgFields an independent persisted WEPP executable setting. New projects
created from `ag-fields.cfg` default to `wepp_dcc52a6`. Stage 4 exposes a WEPP
Exec select populated from installed binaries and submits its selected value
when starting sub-field runs. The server validates and pins the selection in
the queued job; the worker persists it in `ag_fields.nodb` before execution and
propagates it to every sub-field hillslope process.

Historical `ag_fields.nodb` payloads without the new setting remain compatible:
they use the parent Wepp NoDb executable until a user submits an AgFields
selection. The browser no longer exposes Maximum workers; server-side automatic
sizing remains unchanged, and the optional backend argument remains accepted
for existing API clients.

## Decision Provenance

Decision Venue: Codex API conversation, 2026-07-10 14:43 PDT
Participants Present: Roger Lew, Codex
Decision Owner(s): Roger Lew, WEPPpy maintainer
Implementer(s): Codex

## Change Summary

Old behavior: AgFields always used `Wepp.wepp_bin`, which defaults to
`wepp_250915` in `ag-fields.cfg`; Stage 4 allowed users to tune `max_workers`
but not choose the executable.

New behavior: a newly initialized AgFields controller reads
`[ag_fields] bin=wepp_dcc52a6`, persists that value, shows it in Stage 4, and
uses it for all sub-field simulations. Historical controllers without the
field retain their parent executable until explicitly changed.

## Rationale

`wepp_dcc52a6` is the only compared executable that completes the exact repaired
acceptance fixture. Making the choice AgFields-specific avoids changing parent
watershed simulation behavior and makes the compatibility boundary visible to
the user. Automatic worker sizing removes a low-value tuning decision from the
workflow without changing backend concurrency behavior.

## Alternatives Considered

1. Change the global `[wepp] bin` default - rejected because it would alter the
   parent watershed and unrelated workflows.
2. Patch or suppress the `frcfac` arithmetic failure immediately - rejected
   because the failure needs a separate scientific and binary review; the
   legacy executable already provides a demonstrated AgFields-compatible path.
3. Rewrite historical AgFields state to the new default - rejected because an
   additive fallback preserves prior project behavior and avoids migration.
4. Keep Maximum workers alongside WEPP Exec - rejected because the maintainer
   requested automatic sizing and a simpler Stage 4 decision surface.

## Consequences

New AgFields projects use the legacy executable even when their parent
watershed uses a newer release. Users can deliberately choose another installed
binary, and that choice survives reload. Results from different selections may
differ, so the selected value is part of persisted project provenance.

## Evidence

- `docs/work-packages/20260709_ag_fields_runs_page_ui/`
- `docs/work-packages/20260710_management_rotation_synth_hardening/`
- Run `/wc1/runs/sa/sacral-self-discipline`, sub-field 3733.
- Exact normalized replay: `wepp_dcc52a6` completed 17 years and produced all
  expected outputs; `wepp_260430` and `wepp_260606` terminated at
  `frcfac.for:184`.

## Risk and Rollback Notes

The main risk is output divergence between the legacy and current WEPP
executables. Retain the visible selector and executable identity logs so runs
are attributable. Roll back by removing `[ag_fields] bin`, the AgFields-owned
field, and the selector, restoring parent-Wepp inheritance; existing additive
NoDb fields can remain unread without migration.

## Implementation Notes

Regression coverage must prove the new-project default, historical fallback,
state hydration, installed-binary validation, persistence before enqueue, and
propagation into `run_wepp_subfield`.
