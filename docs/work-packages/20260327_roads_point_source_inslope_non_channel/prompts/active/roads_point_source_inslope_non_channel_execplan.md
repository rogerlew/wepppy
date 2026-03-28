# Roads Step-2: Inslope Non-Channel Point-Source Routing

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, inslope roads (`inslope_bd`, `inslope_rd`) with low points that are not channel-adjacent can still contribute routed point-source loads. The Roads pipeline will trace those low points to channel and model each routed contributor as `road OFE + flowpath buffer OFE`, then merge into receiving hillslope pass files. Channel-associated inslope behavior remains unchanged.

## Progress

- [x] (2026-03-27 00:00Z) Authored package/tracker/ExecPlan scaffold for step-2 scope.
- [x] (2026-03-27) Milestone 1: Locked step-1 tracer contract usage and implemented prepare-stage non-channel routable classification metadata.
- [x] (2026-03-27) Milestone 2: Integrated run-stage per-segment trace calls for eligible non-channel inslope segments.
- [x] (2026-03-27) Milestone 3: Added routed contributor assembly for `road OFE + buffer OFE` with trace-derived buffer geometry.
- [x] (2026-03-27) Milestone 4: Routed contributor pass files merge through existing combine flow; run summaries now include routed/trace diagnostics.
- [x] (2026-03-27) Milestone 5: Expanded regression tests for prepare classification, routed execution, and trace-failure skip behavior.
- [x] (2026-03-27) Milestone 6: Completed code-review artifact with no unresolved medium/high findings.
- [x] (2026-03-27) Milestone 7: Completed QA-review artifact with no unresolved medium/high findings.
- [x] (2026-03-27) Milestone 8: Ran validation gates and synchronized package docs/tracker/ExecPlan.
- [x] (2026-03-27) Post-handoff hotfix: fixed routed two-OFE management transform to remap yearly `itype` (`3 -> 2`) after fill OFE removal; added regression test and reran validation gates.
- [x] (2026-03-27) Post-hotfix docs hardening: codified canonical controller job-tracking guidance (bootstrap `jobIds` as hints only + stale local latch reconciliation) in shared controller contract/foundation docs.

## Surprises & Discoveries

- Observation: Current low-point decisioning marks non-channel points as not routable in phase 1.
  Evidence: `monotonic_segments.py` decisions include `no_channel_pixel_near_lowpoint`.

- Observation: Current run path skips segments without mapped channel/hillslope IDs.
  Evidence: Roads run loop gating in `wepppy/nodb/mods/roads/roads.py`.

- Observation: Existing segment execution assumes single-OFE road profiles in phase 1.
  Evidence: Roads run assembly writes one-OFE slope/soil/man for segment runs.

- Observation: Full `tests --maxfail=1` currently fails on an unrelated baseline issue in `tests/nodb/test_soils_gridded_root_creation.py` (`wepppy.wepp.soils` monkeypatch path).
  Evidence: Validation run reached 49% and failed outside Roads step-2 touched files.

- Observation: Routed two-OFE management transform left FOREST yearly `itype` as `3` after reducing to two scenarios, causing WEPP parser failure (`ntype read as 3; must be between 1 and 2`) for real runs.
  Evidence: `/wc1/runs/cl/clogging-starch/wepp/roads/runs/p900025.err` and generated `p900025.man` from failed job `ed22a800-e4d1-452a-b09e-cf8cd031060f`.

- Observation: UI-level active-task latches can become stale when initialized from bootstrap last-known `jobIds`, even when backend Roads status is terminal/idle.
  Evidence: Run UI blocked queue actions with local conflict text while backend status was `idle` and locks were absent.

## Decision Log

- Decision: Step-2 routing only applies to inslope designs (`inslope_bd`, `inslope_rd`).
  Rationale: Keeps package scope aligned with user-requested sequence and avoids outslope coupling.
  Date/Author: 2026-03-27 / Codex.

- Decision: Inslope routed contributors use `road -> buffer` only.
  Rationale: Inslope assumes culvert bypass of fill dynamics.
  Date/Author: 2026-03-27 / User + Codex.

- Decision: Non-channel routing is allowed only for low points on hillslope pixel classes (`subwta` suffix `1|2|3`).
  Rationale: Explicit user requirement to avoid out-of-contract routing.
  Date/Author: 2026-03-27 / User + Codex.

- Decision: Receiving hillslope for traced non-channel contributors is taken from the traced pre-channel `subwta` cell (must end with `1|2|3`), with explicit skip diagnostics when unavailable.
  Rationale: Uses traced flowpath outcome directly while avoiding hidden fallback mapping.
  Date/Author: 2026-03-27 / Codex.

- Decision: Routed two-OFE management generation must remap yearly FOREST `itype` from `3` to `2` when fill scenario is stripped.
  Rationale: WEPP requires `itype` to match the reduced two-scenario management cardinality; leaving `3` causes runtime parse failure.
  Date/Author: 2026-03-27 / Codex.

- Decision: Canonical controller guidance must treat bootstrap `jobIds` as last-known hints only; controllers with custom active-task latches must reconcile against authoritative status before rejecting queue actions.
  Rationale: Prevents stale client-side lockouts after canceled/failed/terminal jobs while preserving server-authoritative concurrency control.
  Date/Author: 2026-03-27 / Codex.

## Outcomes & Retrospective

Completed implementation delivers:

- Prepare-stage classification now distinguishes channel-associated vs non-channel-routable inslope segments and persists routing metadata.
- Run-stage tracing now calls the step-1 Rust tracer contract for non-channel-routable segments and records deterministic trace diagnostics.
- Routed non-channel contributors now execute with `road OFE + buffer OFE` assembly and merge through existing pass-combine flow.
- Regression coverage was expanded for new prepare/run behavior and routed trace failure handling.
- Post-handoff hotfix now guarantees routed two-OFE management files are WEPP-parseable by remapping yearly `itype` values to two-scenario cardinality.
- Shared controller docs now explicitly codify canonical job-tracking behavior (bootstrap hint semantics + stale-latch reconciliation) for future controller implementations.

Validation snapshot:

- Targeted Roads pytest suites: pass.
- Roads route/API pytest suite: pass.
- Roads frontend Jest (`wctl run-npm test -- roads`): pass.
- Frontend lint (`wctl run-npm lint`): pass.
- Full `wctl run-pytest tests --maxfail=1`: fail on unrelated baseline test outside Roads scope.
- Repro validation on failed run inputs (`p900025`): pass-file generated; no `ntype read as 3` parser error after hotfix transform.

## Context and Orientation

This package runs primarily in `/workdir/wepppy`.

Key files:
- `wepppy/nodb/mods/roads/monotonic_segments.py` (prepare-stage low-point classification).
- `wepppy/nodb/mods/roads/roads.py` (run-stage routing, segment WEPP assembly, pass merge).
- `wepppy/nodb/mods/roads/specification.md` (contract updates).
- `tests/nodb/mods/test_roads_monotonic_segments.py` and `test_roads_controller.py` (core regression harness).

Dependency:
- Step-1 package (`20260327_roads_peridot_trace_core`) provides Rust trace API via `wepppyo3`.

Working-tree rule:
- `/workdir/wepppy` may contain unrelated dirty files; do not revert or modify unrelated changes.
- Restrict edits to Roads step-2 implementation/test/docs files.

## Plan of Work

Milestone 1 - Prepare-stage routing eligibility:

- Extend low-point diagnostics to distinguish:
  - channel-associated points (existing path),
  - non-channel hillslope-routable points (`subwta` suffix `1|2|3`),
  - non-routable points.
- Persist routing eligibility metadata per segment in monotonic output properties and prepare summary.
- Keep current channel-associated fields intact.

Milestone 2 - Run-stage trace integration:

- For eligible non-channel inslope segments, call step-1 tracer from run loop.
- Capture trace outputs in execution records:
  - `reaches_channel`,
  - `termination_reason`,
  - `path_length_m`,
  - profile array stats.
- Skip contributor generation when trace does not reach channel, with explicit diagnostics.

Milestone 3 - MOFE contributor build (`road -> buffer`):

- Build routed contributor inputs:
  - road OFE from existing segment road properties,
  - buffer OFE derived from trace path length/slope profile.
- Ensure routing uses receiving hillslope management context for buffer OFE.
- Generate pass outputs for routed contributors and map to receiving hillslope WEPP IDs.

Milestone 4 - Pass merge and summaries:

- Merge routed inslope contributor pass files using existing combine pipeline.
- Update `last_run_summary` and logs with routed counts and termination breakdowns.
- Preserve baseline channel-associated segment behavior and summaries.

Milestone 5 - Tests and validation:

- Add unit/integration tests for:
  - prepare-stage routable classification,
  - run-stage trace invocation and failure handling,
  - routed pass-merge behavior.
- Run fixture-backed verification to confirm at least one routed non-channel inslope segment reaches channel and contributes merged pass output.

Milestones 6 and 7 - Mandatory reviews:

- Milestone 6: independent code review artifact at `artifacts/20260327_code_review.md`; resolve all medium/high findings.
- Milestone 7: independent QA review artifact at `artifacts/20260327_qa_review.md`; resolve all medium/high findings.

Milestone 8 - Final gates and docs synchronization.

## Concrete Steps

Run from `/workdir/wepppy` unless noted.

1. Preconditions:

    - confirm step-1 API module is available in environment.
    - record API version/contract used in tracker notes.

2. Implement Milestones 1-2 and run focused tests:

    wctl run-pytest tests/nodb/mods/test_roads_monotonic_segments.py --maxfail=1
    wctl run-pytest tests/nodb/mods/test_roads_controller.py --maxfail=1

3. Implement Milestones 3-4 and run targeted route/UI checks:

    wctl run-pytest tests/weppcloud/routes/test_roads_bp.py --maxfail=1
    wctl run-npm test -- roads

4. Milestone 5 broader regression:

    wctl run-npm lint
    wctl run-pytest tests --maxfail=1

5. Docs and review artifacts:

    wctl doc-lint --path wepppy/nodb/mods/roads/specification.md
    wctl doc-lint --path docs/work-packages/20260327_roads_point_source_inslope_non_channel/package.md
    wctl doc-lint --path docs/work-packages/20260327_roads_point_source_inslope_non_channel/tracker.md
    wctl doc-lint --path docs/work-packages/20260327_roads_point_source_inslope_non_channel/prompts/active/roads_point_source_inslope_non_channel_execplan.md

## Validation and Acceptance

Acceptance requires:

- Routed non-channel inslope segments are explicitly identifiable in prepare outputs.
- Run path calls tracer for eligible segments and records deterministic outcomes.
- Routed contributors are modeled as `road -> buffer` and merged into receiving hillslopes.
- Channel-associated inslope behavior remains regression-stable.
- Required test suites pass.
- Code and QA review artifacts exist with no unresolved medium/high findings.

## Idempotence and Recovery

- Re-running prepare/run should regenerate Roads-scoped artifacts idempotently under `wepp/roads/*`.
- If trace integration fails for some segments, segment-level diagnostics must persist and avoid silent fallback.
- Do not mutate unrelated run outputs outside Roads scope.

## Artifacts and Notes

Required artifacts:
- `docs/work-packages/20260327_roads_point_source_inslope_non_channel/artifacts/20260327_code_review.md`
- `docs/work-packages/20260327_roads_point_source_inslope_non_channel/artifacts/20260327_qa_review.md`

Also capture:
- routed vs non-routed segment counts,
- termination-reason histogram from trace outcomes.

## Interfaces and Dependencies

End-state requirements:

- Roads prepare path emits routable non-channel metadata for inslope segments.
- Roads run path consumes step-1 trace API and exposes routing diagnostics in summaries/logs.
- Point-source MOFE assembly for step 2 is `road OFE + buffer OFE` only.

Dependency requirement:
- Step-1 trace package interface must be treated as stable contract; if mismatch is discovered, document exact gap and resolve with minimal adapter changes.

---

Revision note (2026-03-27 00:00Z): Initial step-2 ExecPlan authored with scoped inslope non-channel routing milestones and mandatory code/QA review gates.
Revision note (2026-03-27): Milestones 1-8 completed; living sections updated with implementation, validation outcomes, and review closure.
Revision note (2026-03-27): Post-handoff hotfix applied for routed two-OFE management `itype` remap; regression validated against failing `p900025` input set and tests.
Revision note (2026-03-27): Follow-up docs hardening added canonical controller job-tracking guidance to prevent stale client-side active-job latches in future controls.
