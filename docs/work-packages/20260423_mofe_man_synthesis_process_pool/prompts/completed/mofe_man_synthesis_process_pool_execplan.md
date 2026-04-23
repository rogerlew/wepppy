# MOFE `.mofe.man` Synthesis Process-Pool Migration

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, multi-OFE management synthesis (`landuse/hill_<topaz_id>.mofe.man`) will run through the canonical NoDb process-pool pattern instead of a fully sequential per-hillslope loop. Operators should see lower end-to-end MOFE preparation time while preserving identical management-file outputs and explicit failure behavior.

## Progress

- [x] (2026-04-23 17:40 UTC) Package scaffold created with active ExecPlan and execution prompt.
- [x] (2026-04-23 18:08 UTC) Implemented canonical process-pool orchestration in `wepppy/nodb/core/landuse.py::_build_multiple_ofe`, including worker-safe segment plans, deterministic basename validation, and batched worker execution.
- [x] (2026-04-23 18:12 UTC) Added/extended regression tests for success path, spawn->fork retry, sequential fallback, non-pool exception propagation, and deterministic parity fixture behavior.
- [x] (2026-04-23 18:30 UTC) Ran required benchmark/parity matrix on isolated temp copies and published artifacts under `artifacts/`.
- [x] (2026-04-23 18:31 UTC) Completed code/QA/security review artifacts with no unresolved medium/high findings.
- [x] (2026-04-23 18:31 UTC) Closed package docs and prepared ExecPlan archival to `prompts/completed/` with outcome note.

## Surprises & Discoveries

- Observation: Spawn-first per-hillslope pool submission remained slower than sequential baseline even at low worker counts on the representative benchmark runs.
  Evidence: Scratch tuning on `ordained-incentive` and `cochlear-beriberi` showed positive deltas at 2-4 workers before final artifact capture.

- Observation: Batching hillslope tasks and bounding worker fan-out reduced worst-case pool overhead but did not flip the required five-run benchmark matrix to a speedup on this host.
  Evidence: Final benchmark artifact (`artifacts/benchmark_summary.md`, generated `2026-04-23T18:30:33+00:00`) still reported `+34.05%` to `+443.51%` versus forced sequential baseline.

- Observation: The local `wctl` test path was pointed at a different bind-mounted checkout, so changed-file validation had to run from the local `.venv` instead.
  Evidence: Containerized pytest did not see newly added local files until manually mirrored; direct local pytest ran successfully and became the reliable changed-file gate.

## Decision Log

- Decision: Keep this migration in WEPPpy `Landuse._build_multiple_ofe()` and do not move logic into `wepp_interchange`.
  Rationale: `.mofe.man` synthesis ownership and side effects are currently localized to WEPPpy NoDb landuse code; moving ownership would increase risk/scope.
  Date/Author: 2026-04-23 / Codex.

- Decision: Require dedicated security review artifact (`high` triage).
  Rationale: Process-pool and concurrent run-tree write behavior is a high-impact surface under package policy.
  Date/Author: 2026-04-23 / Codex.

- Decision: Batch hillslope synthesis work per spawned worker and cap this path to four workers.
  Rationale: Initial one-future-per-hillslope submission incurred excessive spawn/future overhead on the 48-core host; bounded batched fan-out preserves the requested pool contract while limiting worst-case overhead.
  Date/Author: 2026-04-23 / Codex.

- Decision: Close the package on contract/parity evidence rather than a benchmark-speedup claim.
  Rationale: The user requested the canonical process-pool migration plus explicit artifacts. The required five-run matrix remained slower than sequential baseline even after batching/capping, so the correct closeout is an explicit documented residual risk and follow-up note, not a fabricated optimization claim.
  Date/Author: 2026-04-23 / Codex.

## Outcomes & Retrospective

Implementation completed end-to-end for the requested scope:

- `Landuse._build_multiple_ofe()` now uses canonical `createProcessPoolExecutor` orchestration with spawn-first startup, `BrokenProcessPool` fork retry, bounded sequential fallback, deterministic per-hillslope output filename validation, and explicit non-pool exception propagation.
- Worker payloads preserve segment ordering and disturbed/RAP override semantics via worker-safe segment plans; test stubs still use preloaded management objects where needed.
- Batched worker execution (`max_workers <= 4`) bounds spawn/future overhead while keeping pool behavior canonical for this path.

Validation summary:

- Targeted changed-file regression suite passed locally:
  `env REDIS_HOST=localhost REDIS_PASSWORD_FILE=/workdir/wepppy/docker/secrets/redis_password .venv/bin/pytest tests/nodb/test_landuse_mofe_process_pool.py tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py tests/nodb/test_landuse_coverage_area_source.py --maxfail=1 -q`
  -> `10 passed`.
- Benchmark/parity artifact generation completed successfully at `2026-04-23T18:30:33+00:00`.
- Parity matched on all required runs (`0` mismatches across `moth-eaten-blackhead`, `objectionable-sublimate`, `cochlear-beriberi`, `ordained-incentive`, `uninsured-deformation`).
- Repo-wide changed-file broad-exception enforcement remained blocked by unrelated dirty worktree edits in `wepppy/rq/project_rq.py`; the changed `landuse.py` path itself remained clean.

Performance outcome:

- The required five-run benchmark matrix remained slower than forced sequential baseline on this host (`+34.05%` to `+443.51%`).
- This package therefore closes with explicit evidence that the contract migration/parity goal succeeded, while runtime reduction will require a broader offload than the final `.mofe.man` synthesis/write phase alone.

## Context and Orientation

Current synthesis path:
- `wepppy/nodb/core/landuse.py::_build_multiple_ofe` builds management stacks and writes one `.mofe.man` file per hillslope.
- The final write step is currently sequential:
  - single segment: direct write of one management object
  - multi-segment: `ManagementMultipleOfeSynth().write(mofe_lc_fn)`

Canonical NoDb process-pool references:
- `wepppy/nodb/base.py::createProcessPoolExecutor`
- `wepppy/nodb/core/watershed_mixins.py::_build_multiple_ofe` (spawn-first, retry fork, bounded sequential fallback)
- `wepppy/nodb/core/wepp.py::_prep_multi_ofe` (same pattern)
- `wepppy/nodb/mods/disturbed/disturbed.py::modify_mofe_soils` (same pattern + logging expectations)

Required behavior invariants:
- `.mofe.man` output paths remain `landuse/hill_<topaz_id>.mofe.man`.
- Segment ordering and disturbed/RAP override semantics must not change.
- `BrokenProcessPool` may trigger bounded fallback; non-`BrokenProcessPool` failures must remain explicit raised errors.
- No silent mismatch repair paths.

## Plan of Work

Milestone 1: Introduce worker contract and process-pool orchestration in `Landuse._build_multiple_ofe`.
- Extract synthesis payloads into a worker-safe task list.
- Add module-level task worker(s) so spawn mode can pickle callable + payload.
- Implement canonical orchestration:
  - run pool with `prefer_spawn=True`
  - retry once with `prefer_spawn=False` on `BrokenProcessPool`
  - fallback to sequential only when pool failures are `BrokenProcessPool`
  - raise non-pool failures

Milestone 2: Preserve behavior parity and explicit contracts.
- Ensure `.mofe.man` content ordering and path outputs match baseline.
- Add explicit assertions/guards where needed for malformed task payloads.

Milestone 3: Tests.
- Extend/add tests under `tests/nodb/` targeting:
  - successful process-pool execution path,
  - spawn failure then fork retry,
  - dual pool failure then sequential fallback,
  - non-`BrokenProcessPool` propagation,
  - parity of generated `.mofe.man` content for deterministic fixtures.

Milestone 4: Benchmark + parity artifacts.
- Benchmark old/new implementation on required run matrix using isolated temp directories only.
- Capture:
  - per-run timings,
  - aggregate mean/stddev,
  - percent delta,
  - parity verdicts.
- Save under:
  - `artifacts/benchmark_raw.json`
  - `artifacts/benchmark_summary.md`
  - `artifacts/parity_raw.json`
  - `artifacts/parity_notes.md`

Milestone 5: Review gates + closeout.
- Publish artifacts:
  - `artifacts/2026-04-23_code_review.md`
  - `artifacts/2026-04-23_qa_review.md`
  - `artifacts/2026-04-23_security_review.md`
- Resolve all medium/high findings.
- Update `package.md`, `tracker.md`, `PROJECT_TRACKER.md` and archive ExecPlan with outcome note.

## Concrete Steps

Working directory: `/home/workdir/wepppy`

1. Inspect and patch synthesis path.

    cd /home/workdir/wepppy
    rg -n "def _build_multiple_ofe|ManagementMultipleOfeSynth|hill_\{topaz_id\}\.mofe\.man" wepppy/nodb/core/landuse.py

2. Reuse canonical pool pattern.

    rg -n "createProcessPoolExecutor|BrokenProcessPool|prefer_spawn" \
      wepppy/nodb/core/watershed_mixins.py \
      wepppy/nodb/core/wepp.py \
      wepppy/nodb/mods/disturbed/disturbed.py

3. Implement and run targeted tests.

    wctl run-pytest tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py --maxfail=1
    wctl run-pytest tests/nodb/test_landuse_coverage_area_source.py --maxfail=1

    Add additional targeted test module(s) as needed and run them explicitly.

4. Benchmark/parity collection (isolated temp dirs).

    python tools/.../benchmark_script.py ...

    Publish artifacts in this package `artifacts/` directory.

5. Review and close.

    wctl doc-lint --path docs/work-packages/20260423_mofe_man_synthesis_process_pool/package.md \
      --path docs/work-packages/20260423_mofe_man_synthesis_process_pool/tracker.md \
      --path docs/work-packages/20260423_mofe_man_synthesis_process_pool/prompts/active/mofe_man_synthesis_process_pool_execplan.md \
      --path docs/work-packages/20260423_mofe_man_synthesis_process_pool/prompts/active/execute_mofe_man_synthesis_process_pool_prompt.md \
      --path PROJECT_TRACKER.md

## Validation and Acceptance

Acceptance requires all of the following:
- Production path for `.mofe.man` synthesis uses canonical `createProcessPoolExecutor` orchestration.
- Output parity is demonstrated for benchmark matrix runs.
- Non-pool failures are still explicit raised errors.
- Targeted tests pass for concurrency and failure contracts.
- Review artifacts (code/QA/security) exist and report no unresolved medium/high findings.
- Package lifecycle docs are closed and archived correctly.

## Idempotence and Recovery

- Benchmark/parity execution must use isolated temp copies; source run directories under `/wc1/runs/*` are read-only inputs.
- Re-running tests and benchmark collectors should overwrite artifacts deterministically.
- If process-pool regression appears, preserve failing artifacts and retry with deterministic task subsets before broad rerun.

## Artifacts and Notes

Required artifacts at completion:
- `artifacts/benchmark_raw.json`
- `artifacts/benchmark_summary.md`
- `artifacts/parity_raw.json`
- `artifacts/parity_notes.md`
- `artifacts/2026-04-23_code_review.md`
- `artifacts/2026-04-23_qa_review.md`
- `artifacts/2026-04-23_security_review.md`

## Interfaces and Dependencies

Interfaces touched:
- `wepppy.nodb.core.landuse.Landuse._build_multiple_ofe`
- `wepppy.nodb.base.createProcessPoolExecutor`

Potential helper additions:
- module-level worker entrypoint(s) under `wepppy/nodb/core/landuse.py` for process-pool task execution.

Dependencies:
- Existing disturbed/RAP management override behavior in landuse build path.
- Existing canonical pool-fallback semantics established in NoDb.

## Revision Notes

- 2026-04-23 / Codex: Initial ExecPlan authored for `.mofe.man` synthesis migration to canonical `createProcessPoolExecutor` pattern with tests, benchmarks, and mandatory code/QA/security review gates.
- 2026-04-23 / Codex: Completed implementation, tests, benchmark/parity artifact capture, review closure, and package-closeout updates.
