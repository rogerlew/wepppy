# Tracker: MOFE ET and Deep-Percolation Area Weighting

## Status

- **Started**: 2026-10-20 18:45 UTC; **updated**: 2026-10-20 (implementation validation).
- **Phase**: M1-M4 implemented; M5 release and runtime validation in progress.
- **Next milestone**: M5 final quality gates, native release pairing and live development acceptance.
- **Security impact**: none at scoped numerical boundary; re-triage expansion.
- **Plan**: [Active ExecPlan](prompts/active/mofe_et_dp_area_weighting_execplan.md).

## Task Board

### Done

- [x] Capture operator scope and confirmed consumer evidence.
- [x] Scaffold package, tracker, execution plan, and project-board entry.
- [x] Remove disabled raw balance and map chunks from `new_report.Rmd`.

### Ready

- [x] M1: canonical contract, ADR, state/input matrices, independent reviews,
  contract checkpoint, and failing heterogeneous-OFE regression cases.
- [x] M2: native hillslope report ET/Dp aggregation and cache migration.
- [x] M3: selected-run and comparison-baseline dashboard ET queries.
- [x] M4: Features Export field-specific ET/Dp spatial reduction and cache identity.
- [ ] M5: native release/facade verification, fresh MOFE project outputs,
  correctness review, required quality gates, and documented recovery handoff.

### Validation of This Scaffold

- [x] Scoped documentation lint: four package files and project tracker,
  zero errors/warnings; package relative links resolve; spelling previews checked.
- [x] Diff and extracted executable-R comparison prove only disabled R
  code/comments/chunk wrappers were removed; target raw-balance references absent.
- [x] `git diff --check` passes. No R render or broad suite run because executable
  statements are unchanged and aggregation implementation remains pending.

## Decisions

- **2026-10-20 18:45 UTC**: Operator requested scaffolding fixes 1-3 from the
  audit, not their immediate execution. Complete only the explicitly requested
  disabled R cleanup now.
- **2026-10-20 18:45 UTC**: Preserve TotalWatSed and the daily loader as reference
  paths; both correctly use local OFE areas. Avoid a generic reducer for routed
  runoff/lateral flow.
- **2026-10-20 18:45 UTC**: Keep the shared R helper and older template; removal
  authorization names `new_report.Rmd` only. This is not a formal deprecation
  or deletion of every legacy R workflow.

## Risks and Verification

Existing native/Python report tests assert the defective sums. Replace those
expectations with independently calculated physics-based area results, not
another frozen parity oracle. Features Export terminal selection is shared
across layers and measures; preserve other contracts. Distinguish report
spatial weighting from the existing annual divisor.

Corrected outputs can be hidden by existing caches or an old loaded native
module. Record native path/hash, force only the relevant fixture/project cache
generation, read fresh bytes, then check warm reuse and historical-source
absence. Do not claim production repair from a local rebuild.

## Handoff

Execution was explicitly requested on 2026-10-20; continue with M1-M5. Read the ExecPlan
and applicable subsystem guidance; it names the required checkpoint and review
sequence. M1-M4 fixes and native rebuild are implemented. Isolated project copies carry
validation artifacts; original projects and production remain untouched.

## Contract checkpoint

Two independent read-only reviews approved the amended contract. See
[decision](artifacts/20261020_contract_decision.md) and
[review disposition](artifacts/20261020_contract_reviews.md). Native API
unavailability retains guarded historical access; callable obsolete writers fail
marker verification. Standalone ancestor checkpoint: `9651d7af6`.
Implementation started only after that commit; independent oracle failures were
reproduced against the original native and export boundaries.

## Execution discoveries

- Real MOFE copy: 8,557,275 H.wat rows, 455 hills, 10,465 hill-year rows;
  every native ET/Dp result matches an independent daily volume/area SQL oracle.
- Independent review identified joined-source column collisions, absent WAT
  observations, and missing selected event dates; all have targeted regressions.
- Normal report HTML renders, but CSV raised inherited `NotImplementedError`.
  M5 requires CSV readback; a bounded report adapter now uses the existing annual
  iterator/header without changing the annual divisor or formulas. This is a
  conformance repair of the advertised report CSV path, not a broader exporter
  redesign. Independent review includes this acceptance fix.

## Development acceptance

Final native commit `5e42716230dd6f02d218bfbe10509d501edb93a8` and startup pin
`669579b0e95bc035ce318b1ea49e288b10c20fcbf3e9e7e78739f46931a5be02`
pass fresh-process import. Graceful reload replaced only development Gunicorn
workers, preserving the running pytest process. Live HTML/CSV and selected/base
event results match independent source SQL for all 455 hills. Normal scoped
browse/download access returns four byte-identical artifacts. Production export
service readback covers one real MOFE hill across CSV/Parquet/GeoJSON; geospatial
output retains all 455 geometries with null water metrics for absent observations.

Independent correctness review closes COR-01 through COR-05. Focused export
regressions pass 107 tests after the final joined-date fix; paired startup,
report/cache, SQL and export checks passed 99 before that final fix. Native
release tests pass 72; Rust passes 107 unit and 17 writer tests; Jest passes
119 suites/987 tests. Full Python suite remains running. See retained artifacts.
