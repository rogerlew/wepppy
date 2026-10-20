# Tracker: MOFE ET and Deep-Percolation Area Weighting

## Status

- **Started**: 2026-10-20 18:45 UTC; **updated**: 2026-10-20 18:50 UTC.
- **Phase**: M1 contracts reviewed; checkpoint ready; implementation pending.
- **Next milestone**: M1 contract/ADR checkpoint and regression specification.
- **Security impact**: none at scoped numerical boundary; re-triage expansion.
- **Plan**: [Active ExecPlan](prompts/active/mofe_et_dp_area_weighting_execplan.md).

## Task Board

### Done

- [x] Capture operator scope and confirmed consumer evidence.
- [x] Scaffold package, tracker, execution plan, and project-board entry.
- [x] Remove disabled raw balance and map chunks from `new_report.Rmd`.

### Ready

- [ ] M1: canonical contract, ADR, state/input matrices, independent reviews,
  contract checkpoint, and failing heterogeneous-OFE regression cases.
- [ ] M2: native hillslope report ET/Dp aggregation and cache migration.
- [ ] M3: selected-run and comparison-baseline dashboard ET queries.
- [ ] M4: Features Export field-specific ET/Dp spatial reduction and cache identity.
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
sequence. No aggregate fixes, native rebuild, deployment, or project data
mutations have been performed in the scaffold turn.

## Contract checkpoint

Two independent read-only reviews approved the amended contract. See
[decision](artifacts/20261020_contract_decision.md) and
[review disposition](artifacts/20261020_contract_reviews.md). Native API
unavailability retains guarded historical access; callable obsolete writers fail
marker verification. Commit revision will be recorded immediately after commit.
