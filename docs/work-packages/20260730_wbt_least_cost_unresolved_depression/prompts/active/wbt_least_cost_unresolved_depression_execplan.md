# Fail Fast on Unresolved WBT Least-Cost Depressions

This ExecPlan is a living document. Maintain `Progress`,
`Surprises & Discoveries`, `Decision Log`, and
`Outcomes & Retrospective` as work proceeds. Execute it together with
`docs/work-packages/20260730_wbt_least_cost_unresolved_depression/tracker.md`.

## Purpose

After this work, a WEPPcloud user who selects **Breach (Least Cost)** will not
receive a channel network derived from an extreme automatic fill when the
configured search distance cannot resolve a depression. Delineation will stop,
the channel delineation status summary will explain the problem in plain
language, and the user will be told how to retry safely.

The motivating DEM is
`/wc1/runs/sr/srivas42-reconciled-turf/dem/dem.tif`. The recorded run used a
1,000 m least-cost distance and enabled the fill fallback. The reported impact
is an outlet-area waterbody raised by roughly 450 m; measure the exact value
during Milestone 1.

## Progress

- [x] (2026-07-30 17:11 UTC) Verified current run parameters, upstream
  documentation, fork source behavior, and WEPPpy call path.
- [x] (2026-07-30 17:11 UTC) Scaffolded package, tracker, and ExecPlan.
- [x] (2026-07-30 17:37 UTC) Reproduced `fill=true`, `fill=false`, and native
  fail-fast behavior with exact incident diagnostics.
- [x] (2026-07-30 17:37 UTC) Ratified ownership, user error contract, and
  parameterization ADR.
- [x] (2026-07-30 17:37 UTC) Implemented WBT/WEPPpy fail-fast behavior and
  artifact cleanup.
- [x] (2026-07-30 17:37 UTC) Implemented the instructional channel
  delineation summary.
- [x] (2026-07-30 17:59 UTC) Completed broad pytest, documentation gates, and
  deployment handoff.

## Surprises & Discoveries

- WhiteboxTools does not document `--fill=false` as an error mode. In the
  checked fork source, the tool tracks `num_unsolved`, performs a fill only
  when `fill_deps` is true, writes its output, and returns success otherwise.
  Therefore changing the flag alone cannot satisfy the requested contract.
- WEPPpy currently passes `fill=True` from
  `WhiteBoxToolsTopazEmulator._create_relief`.
- The same incident family motivated a completed Topaz conditioning parity
  package, and `disturbed9002_wbt` now defaults to Topaz. Explicit/persisted
  least-cost behavior still requires safe handling.
- The incident DEM is byte-identical to the tracked WBT
  `test_fixtures/topaz_condition_dem/dem.tif`.
- At 1,000 m (33 cells), the old tool solved 904 pits and left 377 unresolved.
  `fill=true` raised cells by as much as 379.16178369142 m; `fill=false`
  returned success and wrote output. The new fail-fast mode returns nonzero
  and writes no output.

## Decision Log

- **2026-07-30 17:11 UTC**: Treat fail-fast behavior as the invariant and
  `fill=false` as an implementation input, not as proof that an error occurs.
- **2026-07-30 17:11 UTC**: Prohibit automatic algorithm or threshold fallback.
  Recovery remains an explicit user choice.
- **2026-07-30 17:30 UTC**: `weppcloud-wbt` owns an opt-in
  `--fail_on_unresolved` error before output write; ordinary no-fill semantics
  remain compatible. Pushed fork commit
  `17ebe99d92210679f120e83033920109eb99a767`.
- **2026-07-30 17:30 UTC**: Ratified controlled public code
  `wbt_unresolved_depressions`, numeric count/distance details, exact
  instructional message, and traceback suppression in
  `docs/schemas/rq-response-contract.md` and ADR-0035.
- **2026-07-30 17:37 UTC**: Installed and pushed the tracked runtime binary in
  `b4d8774e3375ffd86a487c172f84e0d3f8a6cc50`; WEPPpy must deploy this commit
  together with its wrapper call.

## Context and Orientation

`BreachDepressionsLeastCost` searches for a lower target within a bounded
distance. A depression that has no accepted breach route is *unresolved*.
Whitebox's `--fill` flag raises remaining unresolved depressions to an outlet;
it is a fallback, not part of the least-cost trench search.

Important files:

- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/breach_depressions_least_cost.rs`
  owns the algorithm, `num_unsolved`, optional fill, metadata, and process
  result.
- `/workdir/weppcloud-wbt/whitebox_tools.py` and
  `/workdir/weppcloud-wbt/WBT/whitebox_tools.py` are the paired Python wrappers.
- `wepppy/topo/wbt/wbt_topaz_emulator.py` passes `fill=True` and verifies only
  that `relief.tif` exists.
- `wepppy/nodb/core/watershed.py` stores conditioning method and distance and
  orchestrates channel products.
- `wepppy/rq/project_rq.py::build_channels_rq` publishes channel delineation
  status and timestamps successful completion.
- `wepppy/weppcloud/controllers_js/channel_delineation.js` and `channel_gl.js`
  present status for the classic and GL paths; generated
  `wepppy/weppcloud/static/js/controllers-gl.js` must not be hand-edited.
- `wepppy/weppcloud/routes/usersum/weppcloud/wbt-channel-delineation.md`
  documents current behavior.

Before implementation, read the nearest `AGENTS.md` for every touched path and
the complete current versions of:

- `docs/standards/contract-first-change-standard.md`
- `docs/standards/parameterization-adr-standard.md`
- `docs/standards/hardening-lifecycle-standard.md`
- `docs/schemas/rq-response-contract.md`
- the active decision artifacts in
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`

## Milestone 1: Reproduce and Define the Failure Signal

Use the exact incident DEM and the same distance conversion used by WEPPpy.
Preserve the source DEM. Run the forked CLI in a temporary working directory
with identical arguments except for `--fill`. Capture:

- binary version/commit and complete commands;
- process exit status and stdout/stderr;
- `Num. solved pits` and `Num. unsolved pits`;
- whether output is written and its metadata;
- cell counts and minimum/maximum signed elevation deltas from the source DEM;
- outlet-area maximum fill and coordinates;
- whether D8 pointer and flow accumulation accept each output;
- wall time and peak memory if readily available.

Do not parse human-oriented stdout as the permanent contract until stability is
proved. Inspect whether the fork can emit a small structured diagnostic
sidecar or a stable nonzero error with fields such as:

```text
code = "wbt_unresolved_depressions"
tool = "BreachDepressionsLeastCost"
unresolved_count = <positive integer>
distance_cells = <integer>
distance_m = <number>
fill_applied = false
```

Derive a compact regression fixture if licensing, size, and test runtime permit.
Otherwise document a deterministic fixture-generation recipe plus a small
synthetic case that exercises the same unresolved condition.

Milestone acceptance: the tracker contains exact evidence proving where and how
the unresolved condition can be detected, and confirms that no-fill alone
either succeeds or fails on the checked binary.

## Milestone 2: Ratify Contract and ADR

Identify the finite canonical authority set before changing behavior. Amend
canonical contracts in an accepted ancestor checkpoint before implementation.
At minimum decide:

- whether all `BreachDepressionsLeastCost` callers should fail when unresolved,
  or only the WEPPcloud channel delineation mode;
- whether a partial output is deleted, quarantined for diagnostics, or written
  under a non-canonical name;
- exact public code/message/details and internal log fields;
- success/readiness/timestamp state after failure and after retry;
- exact channel delineation summary copy;
- behavior for zero unresolved depressions;
- rollback criteria.

Create the required ADR in `docs/adrs/`. Record old/new behavior, decision
venue/date/timezone, participants present, named decision owner, implementer,
alternatives, evidence, risks, and rollback. Explicitly reject relying on chat
history as provenance.

Suggested public summary content, subject to contract approval:

> Channel delineation stopped because Breach (Least Cost) could not drain one
> or more depressions within the selected search distance. WEPPcloud did not
> fill them because that could substantially raise terrain and reroute flow.
> Increase the breach distance, enlarge or reposition the DEM so the expected
> outlet is within the Breach (Least Cost) distance, inspect DEM/NoData
> boundaries, or choose
> another conditioning method, then build channels again.

Include the selected distance and unresolved count only if they are reliable
and safe to expose. Do not show a Python/Rust stack trace as primary guidance.

Milestone acceptance: accepted contract checkpoint and ADR exist; tracker
records the ownership and exact error/presentation decision.

## Milestone 3: Implement the Narrow Fail-Fast Boundary

If ownership is in `weppcloud-wbt`, implement the smallest scoped CLI contract
that exposes unresolved status without breaking unrelated callers. Update both
Python wrappers and `CHANGELOG.md`. Prefer a stable typed/nonzero failure or
machine-readable diagnostic over matching prose.

If ownership is in WEPPpy, invoke least-cost breaching with fill disabled and
evaluate the stable diagnostic immediately. Raise a narrow typed exception
before D8, flow accumulation, stream extraction, or successful relief
acceptance. Do not add a broad fallback handler.

In either design:

- preserve the source DEM;
- ensure canonical `relief.tif` and derived channel artifacts are not mistaken
  for successful output;
- preserve useful internal diagnostics;
- leave Redis/NoDb readiness and timestamps in the canonical failed state;
- allow a corrected retry under the existing directory-root lock;
- keep persisted conditioning keys backward compatible;
- do not modify the default distance in this package.

Milestone acceptance: targeted WBT/Python tests and a WEPPpy failure-path test
prove the exact unresolved condition stops the build and a corrected retry
succeeds.

## Milestone 4: Propagate Instructional User Guidance

Reuse the canonical controlled RQ error contract and the WBT boundary-policy
precedent. Update the authoritative Pure UI/status contract before controllers.
Render one concise summary with:

- what failed: unresolved depression after bounded least-cost search;
- why WEPPcloud stopped: filling could cause implausible elevation/drainage
  change;
- what the user can do next;
- selected breach distance and unresolved count when contractually available;
- correlation/error identifier when supplied by the canonical error payload.

The classic and GL paths must present equivalent meaning. The status console
may retain technical diagnostics behind an appropriate detail surface, but the
primary summary must be instructional. Rebuild generated controller assets
using the repository script.

Milestone acceptance: controller tests prove both paths render the controlled
guidance, escape dynamic values, omit raw stack traces from the primary
summary, and retain ordinary error behavior for unrelated failures.

## Milestone 5: Validate, Review, and Document

Required cases:

1. Exact incident DEM with 1,000 m distance: controlled failure, no extreme
   canonical fill, no successful downstream artifacts/timestamp.
2. Synthetic unresolved depression: deterministic typed failure.
3. Solvable least-cost depression: normal success and equivalent output.
4. Increased distance or alternate explicit conditioning: corrected retry
   succeeds.
5. Failed build followed by retry: stale partial output is not reused.
6. Persisted legacy least-cost selection: compatible load and controlled
   behavior.
7. Classic and GL status summaries: equivalent instructional guidance.

Run proportionate gates:

```bash
cd /workdir/weppcloud-wbt
cargo check -p whitebox-tools-app
cargo test -p whitebox-tools-app
python -m py_compile whitebox_tools.py WBT/whitebox_tools.py

cd /home/workdir/wepppy
wctl run-pytest <targeted topo/nodb/rq tests>
wctl run-npm lint
wctl run-npm test
python3 wepppy/weppcloud/controllers_js/build_controllers_js.py
wctl doc-lint --path docs/work-packages/20260730_wbt_least_cost_unresolved_depression
wctl doc-lint --path wepppy/weppcloud/routes/usersum/weppcloud/wbt-channel-delineation.md
wctl run-pytest tests --maxfail=1
```

If queue edges change, update `wepppy/rq/job-dependencies-catalog.md`, run
`wctl check-rq-graph`, and inspect a live job tree. Do not regenerate the graph
for an error-message-only change.

Create code-review and QA-review artifacts and disposition every finding.
Deploy to Forest for a canary before production. Record rollback steps and
observe controlled failures, corrected retries, and unaffected success rates
for 30 days.

Milestone acceptance: all success criteria in `package.md` are checked with
linked evidence, documentation matches runtime behavior, and package/tracker/
`PROJECT_TRACKER.md` are updated.

## Validation Evidence

Record commands, versions, exit codes, test counts, raster statistics, artifact
paths, review findings, Forest run IDs, and production observation results
here as they become available. Do not replace evidence with “tests pass.”

## Idempotence and Recovery

All experiments use temporary output directories and never overwrite the
source DEM. Re-running a failed channel build must first resolve or remove
non-canonical partial artifacts under the existing lock. A controlled failure
must be safe to repeat and must not advance completion timestamps. Rollback
restores the previous binary/application version and the prior documented
`fill=true` behavior; the ADR must state the scientific risk of that rollback.

## Outcomes & Retrospective

Implementation is complete locally. Least-cost channel delineation opts into a
native pre-write unresolved-depression failure, translates only the stable
native diagnostic into a typed application error, removes stale canonical
channel artifacts, records a controlled RQ payload, and presents instructional
guidance without using a traceback as the primary summary.

The WBT source and runtime commits are pushed. WEPPpy deployment and the
post-deployment observation window remain operator handoff items; this
execution did not mutate Forest or production.

A live controlled failure subsequently revealed that the instructional text
was duplicated in the normal summary and the preformatted stacktrace body.
Controlled failures now render once in the normal summary and leave the
details panel empty; unexpected failures retain preformatted tracebacks.
