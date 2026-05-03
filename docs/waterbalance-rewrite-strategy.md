# Water Balance Rewrite Strategy

## Status
- Draft strategy for specification-driven rewrite of WEPP water-balance routines.
- Scope includes `watbal.for` and `watbal_hourly.for` behavior, with contract lock-in for WEPPpy downstream consumers.
- Rewrite target is **`.f90` free-form Fortran** (not further fixed-form expansion).
- Rewrite classification is **non-clean-room** (contract-preserving modernization of existing WEPP behavior).

## Rewrite Classification and Licensing
- This effort is **not** a clean-room rewrite. It is a specification-driven rewrite against existing WEPP behavior/contracts and existing incident evidence.
- This classification is methodological (how rewrite evidence is gathered), not an IP-isolation requirement.
- Legacy `watbal.for` + `watbal_hourly.for` runtime behavior is the **evidence baseline** for spec authoring; once frozen, the normative spec is the contract.
- Legacy-observed quirks are not automatically normative. When legacy behavior conflicts with physics or approved downstream contract intent, classify as `BUG_FIXED` candidate and adjudicate explicitly.
- New rewrite source units are intended to be licensed **CC0-1.0** with SPDX headers, using the header convention in `wepp-forest/docs/contracts/f90-migration-header-schema.md`.

## Problem Statement
Current WEPP water-balance logic is split between:
- `watbal.for` (daily path), and
- `watbal_hourly.for` (hourly path selected via `ui_run`).

The two routines are no longer cleanly synchronized. `watbal_hourly.for` explicitly warns it has not kept up with later `watbal` changes and needs rewrite. At runtime, `ui_run` is activated by `wepp_ui.txt`, so production behavior may route through the hourly fork even when users reason about daily closure semantics.

This makes bug fixing by incremental ablation high-risk and low-confidence. We need a specification-first rewrite with explicit invariants and compatibility gates.

## Strategy Decision
### 0) Rewrite target format: `.f90` (free-form)
Recommendation: rewrite the water-balance implementation as `.f90` units and retire legacy `.for` implementations only after parity proof.

Rationale:
- We want a specification-driven rewrite, not another fixed-form patch cycle.
- `.f90` supports clearer structure, safer refactors, and better long-term maintainability.
- Existing `wepp-forest` build already supports mixed `.for`/`.f90` compilation.
- Format migration and behavior migration must be separately gated:
  - first pass: `.f90` translation with no intended logic deltas,
  - later pass: behavior changes only with replay-manifest adjudication.

### 1) Rewrite both, but do not maintain two independent implementations
Recommendation: implement one shared water-balance core with two thin schedulers/adapters:
- daily scheduler (current `watbal` behavior),
- hourly scheduler (current `watbal_hourly` behavior and timestep loop).

Rationale:
- The current dual-file divergence is the root maintenance failure mode.
- Keeping separate copies preserves the same drift risk.
- A shared core allows one set of invariants, one observability surface, and one contract test suite.

### 2) Daily-first bring-up, then hourly extension
Recommendation: bring up rewrite in two compatibility phases:
1. daily parity first (`ui_run=0` path),
2. hourly parity second (`ui_run=1` path), reusing the same core flux/state transitions.

Rationale:
- Daily path is simpler and better constrained for first specification lock.
- Hourly path has additional gates/caps/diagnostic behavior and should be implemented after core invariants are stabilized.
- This sequencing limits blast radius while still converging to a unified architecture.

### 3) Shared-core boundary (explicit)
Recommendation: define shared vs scheduler-specific behavior up front.

Boundary:
- Shared core:
  - state update primitives, conserved-term accounting, storage/flux bookkeeping, invariant checks, and shared output mapping.
- Scheduler-specific adapters:
  - timestep loop/control flow (`daily` vs `hourly`),
  - hourly-only q-cap/diagnostic controls and any hourly-only gating surfaces,
  - adapter-local observability tags.

## Internal Routine Contracts
These are the internal contracts that the rewrite must preserve (or change explicitly with coordinated downstream updates).

### A. Call interface and entry contract
- Current public routine signatures are:
  - `subroutine watbal(lunp,luns,lunw,nowcrp,elevm)`
  - `subroutine watbal_hourly(lunp,luns,lunw,nowcrp,elevm)`
- Active `watbal(...)` call sites include `contin.for`, `irs.for`, and `wshdrv.for`; `watbal` dispatches to `watbal_hourly(...)` when `ui_run == 1`.
- Rewrite contract:
  - preserve callable interface at integration boundary during migration,
  - preserve `ui_run` behavior compatibility until explicit mode-contract change is approved.

### B. Runtime mode-switch contract (`ui_run`)
- `ui_run` is set by runtime detection of `wepp_ui.txt` and shared via `wathour.inc`.
- `ui_run` influences more than water balance; it is referenced in:
  - `watbal.for`, `contin.for`, `input.for`, `perc.for`, `purk.for`, `tilage.for`, `outfil.for`, `main.for`.
- Rewrite contract:
  - treat `ui_run` as a cross-routine execution-mode contract, not a local flag.
  - any changes require coordinated edits/tests across all consumers.

### C. Shared-state contract (common blocks/includes)
- `watbal*` consume and mutate large shared state via include/common-block contracts (`c*.inc`, `p*.inc`, `wathour.inc`).
- High-coupling state includes hydrology fluxes, soil water state, ET components, routing terms, and output terms.
- Rewrite contract:
  - Phase 1/2 rewrite stays inside the existing common-block/include contract (no include-surface refactor),
  - preserve numeric/state semantics of shared variables during transition,
  - avoid hidden re-interpretation of units or sign conventions.
  - module-based replacement of include surfaces, if pursued later, is a separate scoped work item after parity.

### D. Upstream/downstream routine coupling contract
- `watbal*` behavior is coupled to:
  - upstream/adjacent process routines (`perc`, `purk`, `tilage`, climate/melt/infiltration paths),
  - downstream output writers and report ingestion.
- Rewrite contract:
  - preserve process ordering and consumption/production expectations,
  - document any sequencing changes as explicit contract deltas.

### E. Water-output writer contract (`lunw`, formats, columns)
- `outfil.for` opens water-balance output and writes headers keyed in part by `ui_run` (`1400/1401`).
- For hillslope `H.wat` contract, `watbal*` rows align with the non-channel water-balance layout (`1500` family semantics).
- Channel/watershed water-balance layout (`1510`, including `Surf`/`Base`) is a separate contract consumed via `chnwb` pathways (`watbalprint` path), not the hillslope `H.wat` interchange contract.
- Rewrite contract:
  - preserve required hillslope `H.wat` column meanings and units,
  - preserve separate channel/watershed `chnwb` semantics independently,
  - keep optional enriched storage/profile terms contract-stable,
  - treat header/field ordering as compatibility-critical unless versioned intentionally.

### F. Observability/diagnostic contract
- Current daily and hourly paths emit observability tags (`WB_*` and `WBH_*` families).
- Hourly path also contains q-cap diagnostics (`qcap_diagnostic.csv`) used during incident analysis.
- Rewrite contract:
  - maintain equivalent or better observability coverage,
  - define a single documented tag vocabulary for unified core behavior.

## Specification Definability
The specification is definable, but not from `watbal*` alone. It must be layered and include dependent routines.

### Layer A: Physics and state-transition invariants (normative)
For each OFE/day (and hourly substep where applicable), define:
- inputs/outputs/storage terms with units,
- conservation residual equation,
- admissible numeric tolerances,
- clipping/saturation rules and precedence,
- edge-case behavior (first OFE runon, zero/near-zero geometry, frozen state, no-rain days).

### Layer B: Runtime interface contract (normative)
Define exact expectations for interacting routines and shared state:
- `ui_run` switch semantics and when hourly path is active,
- inputs from climate/infiltration/subsurface processes,
- interactions with `perc.for`, `purk.for`, `tilage.for`, `contin.for`, `input.for`,
- required common-block fields read/write discipline.

### Layer C: Output contract (normative)
Define `H.wat` column contract and semantics:
- required columns and units,
- optional producer-authoritative storage/profile columns (`SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore`),
- ordering/layout compatibility expectations.

### Layer D: Downstream interpretation contract (normative in WEPPpy)
Define how WEPPpy consumes outputs, especially:
- interchange parsing strictness for `H.wat`,
- `totalwatsed3` aggregation semantics (including MOFE `latqcc` last-OFE rule),
- daily closure audit meaning (precipitation-basis vs rain+melt diagnostic),
- roads vs baseline scoped output behavior.

## Downstream Contracts That Must Not Drift Unintentionally
1. `H.wat` parser compatibility in `wepppy/wepp/interchange/hill_wat_interchange.py`:
   - known layouts accepted,
   - unexpected **header** layout drift rejected,
   - row-shape anomalies are currently filtered/skipped by parser behavior and should be tracked explicitly in parity audits,
   - optional enriched terms nullable for legacy producers.
2. `totalwatsed3` water accounting in `wepppy/wepp/interchange/totalwatsed3.py`:
   - runoff depth from `runvol / Area`,
   - MOFE lateral-flow volume aggregation from last OFE when OFE column exists.
3. Audit contracts in:
   - `tools/totalwatsed3_daily_closure_audit.py`
   - `tools/hillslope_daily_closure_audit.py`
   - `tools/hillslope_mofe_daily_closure_audit.py`
4. Report consumers expecting stable water-balance fields (yearly/average annual summaries, streamflow, GL dashboards).

## Validation Plan: Metrics, Benchmarks, Observables
Validation should be multi-layered; not a single residual number.

### 0. Parity objective and acceptance bands (must define before implementation)
- Bitwise parity is **not** the default target for this rewrite.
- Target is contract-level numerical parity with case-class-specific acceptance bands.
- Required parity bands are defined in benchmark manifest before logic migration:
  - per-metric `max_abs`, `p95_abs`, and sign-consistency requirements,
  - separate thresholds per case class and execution mode (`ui_run=0` vs `ui_run=1`),
  - explicit non-goals where exact bitwise equality is infeasible.

### 0b. Baseline characterization first
- Before spec freeze, run legacy binary across benchmark corpus and record observed behavior/invariants.
- Use observed invariants + source evidence to finalize normative spec.
- No rewrite logic decisions are accepted without baseline characterization artifacts.

### 0c. Divergence (bug) disposition policy
- Every legacy-vs-rewrite divergence is tagged in replay manifest as one of:
  - `BUG_PRESERVED`: legacy behavior intentionally retained for compatibility,
  - `BUG_FIXED`: approved behavior change with rationale and downstream impact note,
  - `UNRESOLVED`: pending adjudication; cannot pass parity gate.
- `BUG_PRESERVED` is not the default for all observed legacy quirks; physics/spec conflicts must be adjudicated and may be promoted to `BUG_FIXED`.
- Parity summary must separate expected (`BUG_FIXED`) from unexpected divergence.

### A. Contract tests (must pass)
- `tests/wepp/interchange/test_hill_wat_interchange.py`
- `tests/wepp/interchange/test_totalwatsed3.py`
- `tests/tools/test_totalwatsed3_daily_closure_audit.py`
- `tests/tools/test_hillslope_daily_closure_audit.py`
- `tests/tools/test_hillslope_mofe_daily_closure_audit.py`
- `tests/wepp/reports/test_hillslope_watbal.py`

### B. Replay parity matrix (must be generated and versioned as artifact)
Run legacy vs rewrite on a fixed corpus spanning:
- single-OFE and MOFE hillslopes,
- low/medium/high event intensity,
- known anomaly cases from prior campaign evidence,
- both `ui_run=0` and `ui_run=1` execution modes.

Capture at least:
- per-day `H.wat` term deltas,
- closure residual deltas,
- MOFE chain transfer residual deltas,
- PASS↔WAT runoff reconciliation deltas.

### C. Numeric quality gates (recommended defaults)
Track and gate on:
- `max_abs` and `p95` of daily closure residual (reported + reconstructed),
- `max_abs` MOFE adjacent subsurface transfer residual (`SubRIn` vs upstream `latqcc` volume),
- `max_abs` runoff consistency residual (reported runoff vs reconstructed runoff),
- count of profile-capacity ordering violations (`FC > porosity`, `WP > FC`, `SoilWaterTotal` outside physical bounds).

Thresholds should be case-class-specific and recorded in a benchmark manifest rather than globally hardcoded up front.

### D. Performance benchmark gates
For identical input corpus, compare legacy vs rewrite:
- total runtime,
- per-sim-day runtime,
- memory footprint (peak RSS if available),
- overhead from observability enabled/disabled.

Target: no material regression for production-scale MOFE workloads unless explicitly accepted with rationale.

### E. Observability expansion
Preserve existing observability signals and rationalize naming across daily/hourly paths:
- current `WB_*` and `WBH_*` families,
- hourly q-cap diagnostics (`qcap_diagnostic.csv`) where still relevant.

Rewrite should emit a unified, documented observability vocabulary so diagnostics do not depend on which scheduler is active.
Compatibility policy:
- keep `WBH_*` aliases during migration window,
- publish retirement/deprecation plan only after dashboards/queries are updated.

## Execution Phases
0. **Baseline characterization (legacy binary, no source changes):**
   - run replay corpus with instrumentation,
   - capture observed invariants, edge-case signatures, and current output behavior.
1. **Spec freeze (no behavior change):**
   - author normative spec docs (physics, interfaces, output, downstream interpretation),
   - freeze benchmark corpus, acceptance bands, and divergence-disposition policy.
2. **`.f90` translation pass (no intended logic deltas):**
   - introduce `.f90` routine structure/adapters while preserving existing common-block contract,
   - verify parity against baseline characterization artifacts.
3. **Core implementation (daily parity):**
   - introduce shared core and daily adapter,
   - hit contract-test parity and replay parity for `ui_run=0`.
4. **Hourly adapter implementation:**
   - port hourly scheduling semantics onto same core,
   - hit replay parity for `ui_run=1`.
5. **Hardening and simplification:**
   - remove duplicated legacy branches after parity proof,
   - lock observability and benchmark automation,
   - update operator docs and troubleshooting playbooks.

## Risks and Controls
- Risk: hidden dependency in non-water routines (`perc/purk/tilage/input/contin`).
  - Control: explicit co-spec and integration tests for those touchpoints.
- Risk: output-layout drift breaks interchange.
  - Control: strict parser/layout tests and artifact diff checks.
- Risk: overfitting to one incident class.
  - Control: stratified replay corpus and separate acceptance bands by case class.
- Risk: performance regressions from instrumentation.
  - Control: benchmark with observability toggled both ways.
- Risk: benchmark corpus drift or unclear ownership.
  - Control: assign corpus owner, sourcing policy, and refresh cadence before spec freeze.
- Risk: build-pipeline drift during `.f90` adoption.
  - Control: coordinate make/build-script changes with `wepp-forest` build workflow owners as part of phase-2 gate.

## Immediate Next Steps
1. Create a dedicated rewrite work package with this strategy as its architecture section.
2. Assign benchmark corpus owner and publish sourcing/refresh policy.
3. Run Phase-0 baseline characterization and publish artifact manifest.
4. Author normative spec docs for:
   - water-balance core invariants,
   - `ui_run` execution-mode contract,
   - `H.wat` producer contract and compatibility matrix.
5. Build benchmark manifest (cases, expected artifacts, acceptance metrics, and divergence tags).
6. Start phase-2 `.f90` translation pass with no intended logic deltas.

## Review Disposition (2026-05-03)
### Independent accuracy review
- **Accepted and patched**: broadened `watbal` call-site contract (`contin` + `irs` + `wshdrv`), clarified `H.wat` vs `chnwb` output-contract boundary, and narrowed “layout drift rejected” to header-level claim with row-shape note.

### Claude review disposition
1. **Parity proof undefined**: **accepted**.
   - Added explicit parity objective and acceptance-band requirements.
2. **No behavior-characterization phase**: **accepted**.
   - Added Phase 0 baseline characterization.
3. **Bug-discovery policy missing**: **accepted**.
   - Added mandatory divergence tags: `BUG_PRESERVED`, `BUG_FIXED`, `UNRESOLVED`.
4. **`.f90` conversion mixed with logic rewrite**: **accepted with adjustment**.
   - Kept `.f90` as target, but split into translation pass (no logic deltas) before behavior migration.
5. **Shared-core boundary hazard**: **accepted**.
   - Added explicit shared-core vs scheduler-specific boundary.
6. **Common-block vs module migration tension**: **accepted**.
   - Phase 1/2 kept inside existing include/common-block contract; module migration deferred.
7. **Phase ordering inconsistency**: **accepted**.
   - Reordered execution phases and immediate next steps around new Phase 0/2 gates.
8. **Corpus ownership unassigned**: **accepted**.
   - Added explicit ownership assignment and sourcing/refresh policy as next-step gate.
9. **Observability aliasing (`WBH_*`)**: **accepted**.
   - Added alias/deprecation policy.
10. **Build-pipeline coordination note**: **accepted**.
   - Added risk/control entry for `.f90` build pipeline coordination.
11. **Untrusted producer-output hardening note**: **partially accepted**.
   - Kept this out of primary rewrite scope; parser-hardening work can be tracked as separate follow-on if needed.

### Claude follow-up disposition
1. **Non-clean-room phrasing could imply “legacy is spec”**: **accepted and patched**.
   - Reworded rewrite-classification section: legacy behavior is evidence baseline; frozen spec is normative contract.
2. **Need explicit legacy-vs-physics adjudication rule**: **accepted and patched**.
   - Added explicit statement that legacy quirks are not auto-authority and may be `BUG_FIXED`.
3. **SPDX/header convention should be pinned**: **accepted and patched**.
   - Added explicit reference to `wepp-forest/docs/contracts/f90-migration-header-schema.md`.
