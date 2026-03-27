# Roads Step-2: Inslope Non-Channel Point-Source Routing

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, inslope roads (`inslope_bd`, `inslope_rd`) with low points that are not channel-adjacent can still contribute routed point-source loads. The Roads pipeline will trace those low points to channel and model each routed contributor as `road OFE + flowpath buffer OFE`, then merge into receiving hillslope pass files. Channel-associated inslope behavior remains unchanged.

## Progress

- [x] (2026-03-27 00:00Z) Authored package/tracker/ExecPlan scaffold for step-2 scope.
- [ ] Milestone 1: Lock trace-API assumptions from step-1 package and implement prepare-stage routable low-point classification.
- [ ] Milestone 2: Integrate run-stage per-point tracing for eligible inslope non-channel segments.
- [ ] Milestone 3: Build inslope routed MOFE contributors (`road -> buffer`) and generate pass outputs.
- [ ] Milestone 4: Merge routed contributors into receiving hillslopes and update run/prepare summaries.
- [ ] Milestone 5: Add regression tests and fixture-backed validation.
- [ ] Milestone 6: Complete code-review artifact and resolve medium/high findings.
- [ ] Milestone 7: Complete QA-review artifact and resolve medium/high findings.
- [ ] Milestone 8: Run final validation gates and update package handoff docs.

## Surprises & Discoveries

- Observation: Current low-point decisioning marks non-channel points as not routable in phase 1.
  Evidence: `monotonic_segments.py` decisions include `no_channel_pixel_near_lowpoint`.

- Observation: Current run path skips segments without mapped channel/hillslope IDs.
  Evidence: Roads run loop gating in `wepppy/nodb/mods/roads/roads.py`.

- Observation: Existing segment execution assumes single-OFE road profiles in phase 1.
  Evidence: Roads run assembly writes one-OFE slope/soil/man for segment runs.

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

## Outcomes & Retrospective

Not complete yet. Fill as milestones close and at final handoff.

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
