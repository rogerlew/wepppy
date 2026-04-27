# Peridot vs WEPPpy Python Abstraction Benchmark ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package is executed, WEPPpy and Peridot maintainers will have a reproducible, evidence-backed comparison between Peridot watershed abstraction and the legacy WEPPpy Python abstraction path. The Python path has not been used recently, so the first useful outcome is not a speed number; it is a clear answer to whether the Python comparator still runs, what it needs as input, and whether its outputs are comparable enough to support timing claims.

A maintainer can see the work succeed by running the recorded benchmark command or script on the selected fixture and observing two things: first, parity checks that compare required output files and core watershed tables; second, measured runtime/resource results labeled as `confirmed`, `inference`, or `hypothesis`.

## Progress

- [x] (2026-04-27 01:26 UTC) Package scaffold created with package brief, tracker, ExecPlan, benchmark scope artifact, and package validation artifact.
- [x] (2026-04-27 01:35 UTC) Package lifecycle moved from Backlog to In Progress in `package.md`, `tracker.md`, and `PROJECT_TRACKER.md`.
- [x] (2026-04-27 01:39 UTC) Rediscovered the exact WEPPpy Python abstraction entrypoint and invocation settings.
- [x] (2026-04-27 01:39 UTC) Selected safe benchmark fixture inputs and documented provenance.
- [x] (2026-04-27 01:39 UTC) Documented isolated command transcripts for Python and Peridot runs.
- [x] (2026-04-27 01:39 UTC) Ran smoke and parity checks before timing comparisons.
- [x] (2026-04-27 01:39 UTC) Closed timing collection as invalid because Python failed before parity; smoke resource measurements were recorded only as health evidence.
- [x] (2026-04-27 01:39 UTC) Updated package artifacts, tracker, and root `PROJECT_TRACKER.md` with outcomes.
- [x] (2026-04-27 02:21 UTC) Remediated the two stale Python comparator blockers needed for rough timing and recorded 5-rep smoke benchmark results with exact parity out of scope.

## Surprises & Discoveries

- Observation: The legacy Python comparator is expected to be TOPAZ-oriented rather than WBT-oriented.
  Evidence: `/workdir/wepppy/wepppy/nodb/core/watershed.py::_topaz_abstract_watershed` constructs `WatershedAbstraction(topaz_wd, wat_dir)` instances, while `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py::abstract_watershed` dispatches to this path only when `abstraction_backend` is not `peridot` and the delineation backend is TOPAZ.

- Observation: Peridot full-suite regressions are closed before benchmark package execution starts.
  Evidence: `/home/workdir/peridot` commit `e09f54c` is present locally and `cargo test` passes across library, CLI-wrapper, integration, and doctest suites.

- Observation: The lower-level Python comparator fails on the copied in-repo TOPAZ fixture before complete output generation.
  Evidence: `/usr/bin/time -v .venv/bin/python -` against `/tmp/peridot-python-benchmark-20260427-0138/python-smoke-fail` exited `1` with `numpy.core._exceptions._UFuncOutputCastingError` in `wepppy/topo/watershed_abstraction/support.py::cummnorm_distance()`.

- Observation: Peridot completes the same copied fixture and writes current watershed outputs.
  Evidence: `./wepppy/topo/peridot/bin/abstract_watershed /tmp/peridot-python-benchmark-20260427-0138/peridot-smoke-log --ncpu 4` exited `0` and produced `hillslopes.parquet`, `channels.parquet`, `flowpaths.parquet`, `network.txt`, and slope bundles.

- Observation: After narrow Python comparator remediation, both command paths complete the copied smoke fixture.
  Evidence: `artifacts/2026-04-27_rough_benchmark_after_cummnorm_remediation.md` records 5 Python repetitions and 5 Peridot repetitions, all exit `0`, on fresh copied fixtures.

- Observation: The smoke timing gap is large on the selected fixture.
  Evidence: The rough benchmark artifact records Python mean wall time `2.368s` and Peridot mean wall time `0.162s`, about `14.6x` faster for Peridot on this command path.

## Decision Log

- Decision: Treat the WEPPpy Python abstraction as a stale comparator that must pass health checks before timing.
  Rationale: A stale comparator can produce failures or incompatible outputs. Benchmark numbers would be misleading until the package verifies the comparator path and output parity.
  Date/Author: 2026-04-27 / Codex.

- Decision: Start with TOPAZ-derived abstraction for the first benchmark attempt.
  Rationale: The legacy Python implementation is exposed through `_topaz_abstract_watershed()`, and no WBT Python comparator has been identified. Comparing WBT Peridot directly against a TOPAZ-only Python path would mix backend and implementation differences.
  Date/Author: 2026-04-27 / Codex.

- Decision: Require isolated copies of benchmark inputs.
  Rationale: The abstraction paths write files into working directories. Running them in live run roots would risk mutating historical or operator-owned data.
  Date/Author: 2026-04-27 / Codex.

- Decision: Use the lower-level `WatershedAbstraction(topaz_wd, wat_dir)` comparator for smoke discovery.
  Rationale: This exercises the stale Python abstraction implementation directly without relying on deprecated NoDb state mutation, and the package allowed either NoDb-level or lower-level invocation discovery.
  Date/Author: 2026-04-27 / Codex.

- Decision: Close the benchmark package without timing claims after the Python comparator failure.
  Rationale: Output parity is a gate before timing claims. The Python comparator produced only partial slope output, so Peridot smoke timing cannot be compared to Python as a benchmark result.
  Date/Author: 2026-04-27 / Codex.

- Decision: Add a post-close rough benchmark after the user relaxed exact parity requirements.
  Rationale: The benchmark target is unused Python code versus the Rust hot path. For this purpose, rough completion timing on the same copied fixture is useful even though the output formats are not exact parity.
  Date/Author: 2026-04-27 / Codex.

## Outcomes & Retrospective

Closed on 2026-04-27. The package rediscovered the Python comparator path, selected an in-repo TOPAZ fixture, copied inputs into isolated scratch directories, and ran both smoke commands. The initial Python comparator failed with a NumPy casting error in `support.py::cummnorm_distance()`, while Peridot completed and produced current watershed table and slope outputs. A post-close addendum remediated that Python failure plus a channel GeoJSON serialization blocker, then collected rough 5-rep timing on fresh copied fixtures. The rough result was Python mean `2.368s` versus Peridot mean `0.162s`, about `14.6x` faster for Peridot on this tiny fixture and command path. Exact parity remains out of scope for this package.

## Context and Orientation

There are two repositories in scope. WEPPpy lives at `/workdir/wepppy`; Peridot lives at `/home/workdir/peridot`.

Peridot is the Rust watershed abstraction implementation. WEPPpy invokes it through wrapper code in `/workdir/wepppy/wepppy/topo/peridot/peridot_runner.py`. The likely CLI binaries are `abstract_watershed` for TOPAZ-derived inputs and `wbt_abstract_watershed` for WBT-derived inputs. The previous runtime-hardening package confirmed these CLI wrappers propagate errors and the Peridot full test suite is clean.

The legacy Python abstraction is in `/workdir/wepppy/wepppy/topo/watershed_abstraction/watershed_abstraction.py`. It is exposed to NoDb watershed orchestration through `/workdir/wepppy/wepppy/nodb/core/watershed.py::_topaz_abstract_watershed`. In normal orchestration, `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py::abstract_watershed` chooses Peridot when `self.abstraction_backend == "peridot"`; otherwise it calls `_topaz_abstract_watershed()` for TOPAZ delineation. This means the benchmark must either configure a copied run to use the non-Peridot Python path or call the lower-level Python abstraction class directly with an isolated `topaz_wd` and `wat_dir`.

A benchmark fixture is a directory of input files copied into a temporary workspace so abstraction commands can write outputs without changing canonical run directories. Prefer in-repo fixtures. If production-derived run data is needed, copy the smallest safe subset and record the source path, but do not run either abstraction path directly in `/wc1/runs`, `/geodata/weppcloud_runs`, or `/geodata/wc1`.

## Plan of Work

Milestone 1 is comparator discovery. Read `wepppy/topo/watershed_abstraction/watershed_abstraction.py`, `wepppy/nodb/core/watershed.py::_topaz_abstract_watershed`, and `wepppy/nodb/core/watershed_mixins.py::abstract_watershed`. Identify whether the best benchmark invocation is a NoDb-level run with `abstraction_backend` set away from `peridot`, or a lower-level call to `WatershedAbstraction(topaz_wd, wat_dir)`. Record imports, required files, and expected outputs in an artifact.

Milestone 2 is fixture selection. Search for in-repo fixtures first. If they are insufficient, identify candidate run directories but copy only the required inputs into a temporary benchmark workspace. Record a size summary, including raster dimensions or file sizes, hillslope count, channel count, and any missing inputs.

Milestone 3 is harness design. Create a minimal script or command transcript that runs the Python comparator and Peridot comparator on separate copies of the same fixture. Capture wall-clock runtime with a consistent tool such as `/usr/bin/time -v` when available. Record thread/process settings such as `NCPU`, Rayon thread count, and any environment variables.

Milestone 4 is parity validation. Before comparing performance, verify required output file presence and core schema compatibility. At minimum compare `hillslopes.parquet`, `channels.parquet`, `flowpaths.parquet` when generated, slope files under `watershed/`, network/structure files, row counts, unique IDs, and topaz/wepp ID coverage. If outputs differ, classify whether the difference is expected, blocking, or a follow-up.

Milestone 5 is benchmark execution. Run at least three repetitions per comparator for smoke-sized fixtures if runtime is short enough. For larger fixtures, record the repetition count and rationale. Summarize mean, min, max, standard deviation where meaningful, and include raw measurements in an artifact. Do not hide failures or outliers; explain them.

Milestone 6 is documentation and handoff. Update `tracker.md`, add validation and benchmark result artifacts, update this ExecPlan's living sections, and update `PROJECT_TRACKER.md` lifecycle state if the package moves from Backlog to In Progress or Done.

## Concrete Steps

Start in WEPPpy:

    cd /workdir/wepppy
    git status --short --untracked-files=all
    rg -n 'WatershedAbstraction|_topaz_abstract_watershed|abstraction_backend|run_peridot_abstract_watershed' wepppy tests docs

Inspect comparator implementation:

    sed -n '1,260p' wepppy/topo/watershed_abstraction/watershed_abstraction.py
    sed -n '1240,1325p' wepppy/nodb/core/watershed.py
    sed -n '588,620p' wepppy/nodb/core/watershed_mixins.py

Search for safe fixtures:

    find tests docs wepppy -maxdepth 5 -type f \( -iname '*SUBWTA*' -o -iname '*NETW*' -o -iname '*FLOPAT*' -o -iname '*FLOVEC*' -o -iname '*RELIEF*' \) | sort
    find /home/workdir/peridot/tests -maxdepth 5 -type f | sort

If no in-repo benchmark fixture exists, record that as `confirmed` and create a follow-up fixture-curation recommendation before using production-derived data.

When running benchmark commands, use isolated output directories. A safe pattern is:

    mkdir -p /tmp/peridot-python-benchmark
    cp -a <source-fixture> /tmp/peridot-python-benchmark/python-run
    cp -a <source-fixture> /tmp/peridot-python-benchmark/peridot-run

Do not run abstraction commands directly against source run directories.

## Validation and Acceptance

Acceptance for Milestone 1 is a discovery artifact that names the Python comparator path, its required inputs, and a smoke command or the exact blocker preventing a smoke command.

Acceptance for Milestone 2 is a fixture artifact that records source path, copied benchmark path, input size summary, and mutation-safety statement.

Acceptance for Milestone 3 is a benchmark harness or command transcript that can be re-run by another agent from a clean checkout with the same fixture.

Acceptance for Milestone 4 is an output parity artifact. Timing claims are not accepted until this exists. If parity fails, the package can still close with a documented blocker and follow-up remediation package.

Acceptance for Milestone 5 is a benchmark results artifact with raw timings, summarized statistics, environment context, and claim labels.

Documentation validation must run from `/workdir/wepppy`:

    wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_python_abstraction_benchmark
    git diff --check

If helper scripts or tests are added, run targeted `wctl run-pytest` or direct script validation and record the command results.

## Idempotence and Recovery

All benchmark execution must be repeatable. Input directories must be copied before each comparator run or reset from a clean fixture copy. Generated outputs should live under `/tmp`, package artifacts, or another explicitly named scratch directory, not inside canonical run roots.

If the Python comparator fails, do not patch production behavior inside the benchmark package unless the fix is small, clearly scoped, and documented as benchmark harness support. Prefer closing the benchmark attempt with a failure artifact and creating a separate remediation work package.

If Peridot binaries are dirty or have unclear provenance, do not stage them. Record the binary path, source commit, and dirty status in the benchmark artifact. If provenance is necessary for publication-quality claims, create a separate binary provenance package.

## Artifacts and Notes

Required artifacts during execution:

- `artifacts/<date>_python_comparator_discovery.md`
- `artifacts/<date>_fixture_selection.md`
- `artifacts/<date>_output_parity.md`
- `artifacts/<date>_benchmark_results.md` only if timing is valid; this package did not create one during initial closure because parity failed.
- `artifacts/2026-04-27_rough_benchmark_after_cummnorm_remediation.md` records the post-close rough timing addendum.
- `artifacts/<date>_validation_summary.md`

The initial scope and hypotheses are recorded in `artifacts/2026-04-27_benchmark_scope_and_hypotheses.md`.

## Interfaces and Dependencies

WEPPpy interfaces:

- `wepppy.topo.watershed_abstraction.watershed_abstraction.WatershedAbstraction`
- `wepppy.nodb.core.watershed.Watershed._topaz_abstract_watershed`
- `wepppy.nodb.core.watershed_mixins.WatershedOperationsMixin.abstract_watershed`
- `wepppy.topo.peridot.peridot_runner.run_peridot_abstract_watershed`

Peridot interfaces:

- `/home/workdir/peridot/src/bin/abstract_watershed.rs`
- `/home/workdir/peridot/src/bin/wbt_abstract_watershed.rs`
- `/home/workdir/peridot/docs/contracts/watershed-output-contract.md`

Benchmark artifacts must preserve claim discipline. Use `confirmed` only for measured commands and generated files, `inference` for conclusions with stated assumptions, and `hypothesis` for plausible but unmeasured performance or scalability statements.

## Revision Notes

- 2026-04-27 / Codex: Initial ExecPlan authored for benchmarking Peridot against the stale WEPPpy Python abstraction comparator.
- 2026-04-27 / Codex: Began execution and recorded lifecycle transition before comparator rediscovery.
- 2026-04-27 / Codex: Closed execution with comparator-failure evidence, smoke artifacts, and no timing claim because parity was not adequate.
- 2026-04-27 / Codex: Archived the completed ExecPlan under `prompts/completed/` per package closure policy.
- 2026-04-27 / Codex: Added post-close remediation and rough timing outcome after the user clarified that exact parity is unnecessary for this comparison.
