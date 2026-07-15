# Require WEPPpyo3 for all production WEPP interchange

This ExecPlan is a living document. Maintain `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, WEPPcloud workers have one implementation for interpreting
WEPP text outputs: the owned Rust extension distributed by `wepppyo3`. A stale,
missing, or faulting native release fails immediately with an actionable error
instead of continuing for hours through a legacy Python parser. Users retain the
same WEPPpy entrypoints, paths, schemas, and downstream reports.

The goal is faithful wired retirement, not a surrogate. Implementation is not
complete until the rebuilt installed release runs generated conversion through
the restarted stack and a missing required symbol is proven to fail before
publication.

## Progress

- [x] (2026-07-15 17:05 UTC) Decision owner authorized native-only retirement,
  dual reviews, subagent dispatch, and local stack restart.
- [x] (2026-07-15 17:05 UTC) Opened work package, tracker, ADR-0020, and ExecPlan.
- [x] (2026-07-15 17:15 UTC) Completed exhaustive Python fallback and native API
  inventory; strict ownership requires six new native writers.
- [ ] Add five hillslope bulk writers and one watershed TC_OUT writer to
  wepppyo3 with schema/value/ordering/empty-input coverage.
- [ ] Implement the required-native dependency/error boundary.
- [ ] Remove watershed production Python parsers and fallbacks.
- [ ] Remove hillslope production Python parsers and fallbacks.
- [ ] Refresh documentation, tests, and the native release artifact as required.
- [ ] Restart the local stack and pass fixture/generated native-only evidence.
- [ ] Complete independent code and QA reviews and disposition findings.
- [ ] Pass broad gates, archive this plan, and close the package.

## Surprises & Discoveries

- Observation: WAT already has a direct multi-file native writer, while the other
  hillslope converters call native per-file column APIs and assemble canonical
  Arrow tables in Python.
  Evidence: `hill_wat_interchange.py` calls
  `hillslope_wat_files_to_parquet`; PASS/EBE/ELEMENT/LOSS/SOIL call
  `hillslope_*_to_columns`.
- Observation: all seven watershed report converters already expose direct
  native-to-Parquet APIs, so their legacy Python implementations are removable
  without a new public Rust surface.
  Evidence: `wepp_interchange/src/lib.rs` registers PASS, SOIL, LOSS,
  CHAN_PEAK, EBE, CHANWB, and CHNWB functions.
- Observation: strict native writer ownership is not deletion-only. Hillslope
  PASS, EBE, ELEMENT, LOSS, and SOIL return column dictionaries to WEPPpy's
  `write_parquet_with_pool()`, while TC_OUT is entirely Python-only.
  Evidence: `concurrency.py` has six production callers;
  `watershed_tc_out_interchange.py` has no wepppyo3 dispatch.
- Observation: watershed EBE still parses raw `chan.out` in Python after its
  native writer to infer the outlet and audit peak counts.
  Evidence: `watershed_ebe_interchange.py` helpers between the schema and public
  runner parse the raw channel report.

Add discoveries with exact paths, commands, or concise test output. Do not erase
historical observations that changed the design.

## Decision Log

- Decision: Require native import and operation symbols; do not catch native
  execution failures at the wrapper boundary.
  Rationale: compatibility fallback masked deployment drift and reentered the
  high-memory implementation that this owned native substrate replaced.
  Date/Author: 2026-07-15, Roger Lew and Codex.
- Decision: Keep the `wepppy.wepp.interchange` public facade for orchestration,
  calendar/version arguments, aggregation, and exports.
  Rationale: retiring duplicate WEPP text parsing does not require an unrelated
  API or query-layer migration.
  Date/Author: 2026-07-15, Codex.
- Decision: Native ownership includes ordered primary Parquet writing for every
  report format, not only tokenization into Python columns.
  Rationale: retaining the Python process-pool/PyArrow fan-in would preserve the
  same high-memory handoff class that triggered this retirement.
  Date/Author: 2026-07-15, Codex.
- Decision: Treat an absent climate directory as the established Gregorian mode,
  but treat an existing unreadable CLI Parquet as an explicit input failure.
  Rationale: absence and corruption are different contracts; corruption must not
  be hidden by another fallback.
  Date/Author: 2026-07-15, Codex.

## Outcomes & Retrospective

Open. Update after each milestone and at closure.

## Context and Orientation

WEPPpy public callers import functions from `wepppy/wepp/interchange/`. The
modules currently contain both legacy Python report parsers and a native-first
dispatcher. `_rust_interchange.load_rust_interchange()` returns either a module
or an import error; each converter then catches native errors and calls its Python
implementation. That is the compatibility callus being removed.

The owned native implementation lives in
`/home/workdir/wepppyo3/wepp_interchange/src/`. Its Python 3.12 release tree is
`/home/workdir/wepppyo3/release/linux/py312/`. WEPPpy's development container
must import that installed release after the authorized restart. The public
facade, version manifest, and downstream `totalwatsed3`/DSS/query behavior remain
in WEPPpy because they do not provide a second WEPP report parser.

The covered hillslope formats are PASS/HBP, EBE, ELEMENT, LOSS, SOIL, and WAT.
The covered watershed formats are PASS, SOIL, LOSS, channel peak, EBE, CHANWB,
CHNWB, and TC_OUT. “Native-only” means record tokenization, interpretation,
record-batch construction, and primary Parquet writing occur in wepppyo3 and
cannot switch to a WEPPpy implementation after any native failure.

## Plan of Work

Milestone 1 freezes the dependency contract. Inventory every `load_rust_interchange`
call, every `falling back to Python` message, all `_run_*_python` functions, and
fallback-oriented tests. Inventory the installed native symbols. Add one required
loader that imports the native module, verifies an operation-specific symbol set,
and raises a stable WEPP interchange exception with the import/missing-symbol
cause. Add tests for primary import, legacy extension import if still supported,
missing module, and missing symbols. The loader must not hide a module that
imports but lacks the current API.

Milestone 2 expands the native data plane before WEPPpy deletion. Add ordered
multi-file direct-to-Parquet APIs for hillslope PASS, EBE, ELEMENT, LOSS, and
SOIL using the established WAT writer contract. Add a watershed TC_OUT writer.
Preserve canonical schema field metadata, file ordering, row groups, empty-input
behavior, version metadata, calendar mapping, temporary publication, and public
return paths. Add Rust and release-Python tests before installing the artifact.

Milestone 3 removes the watershed duplicate implementations. Each public wrapper
keeps source validation, output naming, version/calendar arguments, native call,
post-write audit/enrichment that is not report parsing, and return type. Delete
the legacy tokenizers/writers and `_run_*_python` branches once no production or
test caller depends on them. Let native I/O, parse, and runtime exceptions cross
the stable WEPPpy boundary with operation context and chained cause. Preserve
temporary/atomic output guarantees and verify partial targets do not publish.

Milestone 4 removes hillslope duplicate parsers and the shared Python Parquet
fan-in. The wrappers require direct native writers before creating target paths.
WAT must require its direct writer and cannot fall back to per-file table
conversion. HBP remains native-only and rejects invalid mixed families as
before. Remove stale-native optional-column normalization rather than patching
release skew in Python.

Milestone 5 updates ownership and release contracts. Update the interchange
README, historical native plan/spec status, test fixture README, operator error
guidance, and ADR index. If Rust changes are needed, add focused Rust and release
API tests, rebuild the Python 3.12 artifact, install it atomically, and record its
source/artifact hash. Even if no Rust source change is required, freeze the
complete symbol set in release tests and provenance.

Milestone 6 performs wired acceptance. Run focused tests, restart the authorized
local stack using canonical `wctl` commands, verify every relevant service imports
the expected artifact/symbols, then run an existing generated WEPP output through
the public aggregate entrypoint. Capture logs proving native execution and no
fallback. Run a negative smoke with a deliberately incomplete fake module in a
test boundary and prove no final artifact is published.

Milestone 7 runs the full repository/native gates. Then dispatch two independent
agents: one reviews code/API/error/atomicity and one reviews QA/runtime/docs and
tries the documented commands. Resolve all medium/high findings, rerun affected
gates, update the package/tracker/ADR/root board, move this plan to
`prompts/completed/`, and close the package. Scientific/model output values must
not change.

## Concrete Steps

From `/home/workdir/wepppy`, inventory and test with:

    rg -n "load_rust_interchange|falling back|_run_.*_python|_parse_.*file" \
      wepppy/wepp/interchange tests/wepp/interchange
    wctl run-pytest tests/wepp/interchange

From `/home/workdir/wepppyo3`, validate source and release with:

    cargo test -p wepp_interchange
    release/linux/py312/.venv/bin/python -m pytest \
      release/linux/py312/tests/wepp_interchange

Use the runtime audit's canonical stack commands after code/test readiness. Do
not overwrite an imported shared object in place; build to a temporary path and
atomically rename or restart all importing processes before replacement.

Before closure, from `/home/workdir/wepppy`, run:

    python /home/roger/.codex/skills/wepppy-tester/scripts/wepppy_tester.py --all
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl check-rq-graph

## Validation and Acceptance

Acceptance requires all of the following observable behaviors:

1. Importing the installed native module reports the full required symbol set.
2. Every public converter produces the same documented paths and compatible
   schemas/metadata on fixtures.
3. A missing native module or symbol raises the stable required-native exception;
   no warning says conversion will continue in Python.
4. A native parse/write error leaves no final partial output and retains its
   original cause.
5. The restarted stack completes generated conversion and logs native provenance
   without fallback telemetry.
6. Full WEPPpy and wepppyo3 gates pass, and both independent reviews have zero
   unresolved medium/high findings.

## Idempotence and Recovery

Tests and generated conversions write temporary outputs before atomic rename and
may be repeated. Stack restarts use canonical compose wrappers and do not delete
run data. If the native release is invalid, stop before worker restart, restore
the prior paired WEPPpy/wepppyo3 commit/artifact, and rerun the symbol smoke. Do
not restore availability by reintroducing a Python parser fallback.

## Artifacts and Notes

Review artifacts will live under
`docs/work-packages/20260715_wepppyo3_only_interchange/artifacts/`. Generated
large output stays under `/wc1` or temporary test roots and is summarized rather
than committed.

## Interfaces and Dependencies

The stable WEPPpy public converter signatures remain unchanged. Worker-count
arguments may be accepted as compatibility inputs even when native writers own
their internal parallelism. The private
required-native loader will expose a module-or-raise contract and accept an
operation name plus required symbols. The installed
`wepppyo3.wepp_interchange` package is required and must export direct writer
symbols used by production wrappers. PyArrow, DuckDB, DSS, and query/export
dependencies remain only for their existing non-parser responsibilities.

## Plan Revision Note

2026-07-15 17:05 UTC: Created the plan after the AgFields routing-suite incident
showed that logged Python compatibility fallback materially increased time and
memory while hiding native deployment defects. Scope is faithful native-only
parser retirement with stable public orchestration and generated wired evidence.

2026-07-15 17:15 UTC: Expanded the implementation after inventory showed five
hillslope formats still wrote primary Parquet through Python and TC_OUT had no
native API. Native-only now explicitly includes direct primary writers and
removal of the shared Python fan-in.
