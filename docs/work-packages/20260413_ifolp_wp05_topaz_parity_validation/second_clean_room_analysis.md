# WP-05 Second Clean-Room TopAZ Investigation

**Date (UTC)**: 2026-04-13  
**Investigation mode**: analysis/specification only (no IFOLP implementation edits)

## Scope and hard constraints

1. Analysis/spec work only; IFOLP implementation code is unchanged.
2. No TopAZ code/symbol/control-flow porting into IFOLP code.
3. Findings are converted to behavior-level, implementation-neutral contracts.
4. No WP-06+ scope expansion.

## Evidence index

| Evidence ID | Evidence summary | Source (path:line) |
|---|---|---|
| E-001 | Fixture catalog defines three fixtures and current threshold provenance classes (authoritative only for anchor). | `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/fixture-catalog.md:25-37` |
| E-002 | Fixture preparation manifest encodes threshold source; blackwood/gatecreek are naming-convention inferred. | `/workdir/weppcloud-wbt/tools/ifolp_wp00_prepare_fixtures.py:40-85` |
| E-003 | Oracle capture is `snapshot_copy` from pinned raster files, not native TopAZ execution in WP-00 harness. | `/workdir/weppcloud-wbt/tools/ifolp_wp00_run_topaz_oracle.sh:12-15`, `/workdir/weppcloud-wbt/tools/ifolp_wp00_run_topaz_oracle.sh:128-139`, `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/topaz-oracle-manifest.md:5-7`, `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/topaz-oracle-manifest.md:23` |
| E-004 | TopAZ release/build variants and source-compile baseline are present and version-sensitive. | `/workdir/topaz/README.md:7-17`, `/workdir/topaz/src/Makefile:1-20`, `/workdir/topaz` git `HEAD` commit `2503f1f` (local repo metadata) |
| E-005 | TopAZ full run executes `INPCOD -> NETFUL -> PRUNE -> PRUNE1` for channel network stage. | `/workdir/topaz/src/dednm.f90:11905-12007` |
| E-006 | TopAZ D8 pointer model uses 1..9 neighborhood coding; zero is non-flow/indeterminate. | `/workdir/topaz/src/dednm.f90:193-210`, `/workdir/topaz/src/dednm.f90:6128-6135`, `/workdir/topaz/src/dednm.f90:8692-8698` |
| E-007 | Upstream area (`ICA`) is accumulated in contributing-cell counts. | `/workdir/topaz/src/dednm.f90:8183-8214` |
| E-008 | `csa_ha -> csa_cells` uses cell-size-derived hectares and nearest-integer conversion. | `/workdir/topaz/src/dednm.f90:9691-9692`, `/workdir/topaz/src/dednm.f90:9968-9969` |
| E-009 | `mscl` comparison is performed against path length scaled by cell size in meters. | `/workdir/topaz/src/dednm.f90:6808-6809` |
| E-010 | Terminal-head path length starts with half-cell initialization. | `/workdir/topaz/src/dednm.f90:6749-6751` |
| E-011 | Numeric epsilon is fixed to `1e-5`; shortest-link selection uses strict epsilon improvement. | `/workdir/topaz/src/dednm.f90:6723`, `/workdir/topaz/src/dednm.f90:6795-6804` |
| E-012 | Phase A behavior: provisional mask from minimum CSA, one row-major source scan, inline mutation with receiver transitions. | `/workdir/topaz/src/dednm.f90:5741-5765`, `/workdir/topaz/src/dednm.f90:5782-5854` |
| E-013 | Phase B behavior: row-major candidate discovery, receiver-group ordering by first encounter, immediate prune mutation, degeneration-triggered repass only. | `/workdir/topaz/src/dednm.f90:6727-6779`, `/workdir/topaz/src/dednm.f90:6792-6912` |
| E-014 | Only-channel guard is explicit when one receiver-group and one incoming candidate are present. | `/workdir/topaz/src/dednm.f90:6812-6822` |
| E-015 | TopAZ PRUNE loop behavior changed at `2503f1f` (`EXIT J2` vs `CYCLE J2`) and is therefore version-sensitive. | `/workdir/topaz/src/dednm.f90:6866`, `/workdir/topaz` commit `2503f1f` diff |
| E-016 | Parity harness metric definitions and pointer-offset handling are explicit in compare tool. | `/workdir/weppcloud-wbt/tools/ifolp_wp00_compare_outputs.py:23-43`, `/workdir/weppcloud-wbt/tools/ifolp_wp00_compare_outputs.py:99-106`, `/workdir/weppcloud-wbt/tools/ifolp_wp00_compare_outputs.py:257-307` |
| E-017 | Candidate pass counts on retained WP-05 state are deterministic and fixture-specific. | IFOLP CLI run output (2026-04-13): `blackwood PhaseA=1/PhaseB=2`, `anchor PhaseA=1/PhaseB=3`, `gatecreek PhaseA=1/PhaseB=2` |
| E-018 | First-divergence and FP/FN topology-context decomposition were computed from run1 retained outputs. | `/tmp/ifolp_wp05_second_investigation_context.json` |
| E-019 | CSA/MSCL/epsilon perturbation sensitivity around decision boundaries was computed for F-003/F-004 + anchor regression check. | `/tmp/ifolp_wp05_second_investigation_sensitivity.json` |
| E-020 | Anchor provenance is explicit and references WBT Topaz emulator channel build call. | `/wc1/runs/cl/clueless-aftertaste/watershed.log:4-14` |
| E-021 | Manual map QA + basin-mask diagnostics show full-extent candidate/oracle encoding-stage mismatch and basin-internal over-pruning by candidate. | `/tmp/ifolp_wp05_remediate/run1/{candidate,oracle}/**/stream.tif`, fixture `bound.tif` rasters |

## Requirement coverage (1-12)

| Requirement | Finding summary | Evidence |
|---|---|---|
| 1. Fixture threshold provenance | Anchor is authoritative; blackwood/gatecreek remain inferred-only and cannot close root-cause attribution risk. | E-001, E-002, E-020 |
| 2. Oracle runtime contract | Current WP-00/05 oracle is snapshot-copy parity against pinned rasters; native runtime build/options contract is not captured. | E-003, E-004, E-005 |
| 3. Area-unit conversion contract | TopAZ uses upstream area in contributing-cell counts and converts `csa_ha` to integer cell threshold from cell area. | E-007, E-008 |
| 4. MSCL measurement contract | Link distance is step-based, half-cell for terminal-head starts, and compared in meters after cell-size scaling. | E-009, E-010 |
| 5. Numeric decision contract | Epsilon is fixed (`1e-5`); shortest-link selection uses strict epsilon improvement; prune predicate is strict with epsilon. | E-011, E-009 |
| 6. Phase A pass-level contract | One row-major source scan with inline mutation and receiver transitions; no separate global rescan is present in `NETFUL`. | E-012 |
| 7. Phase B pass-level contract | Candidate generation is per-pass snapshot; receiver groups follow encounter order; prune is immediate; repass only on degeneration. | E-013, E-014 |
| 8. Deterministic tie/ordering contract | Determinism is driven by row-major discovery, receiver encounter order, strict epsilon tie handling, and version-specific PRUNE loop control. | E-011, E-013, E-015 |
| 9. First-divergence localization | First mismatches are deterministic FP cells at early row-major positions for all fixtures; context is terminal-dominated. | E-018 |
| 10. Topology-context mismatch decomposition | F-003/F-004 are dominated by terminal-context FP/FN mismatches with large-component concentration. | E-018 |
| 11. Threshold sensitivity analysis | Epsilon perturbations had zero effect; CSA/MSCL perturbations caused only small shifts for F-003/F-004 and no anchor regression. | E-019 |
| 12. Acceptance-metric contract | Exact-binary parity should remain normative; count/component/junction/reachability/context metrics are diagnostic for attribution. | E-016 |

## Basin-Masked Interpretation Addendum

Discovery from manual QA:

1. Oracle stream rasters in WP-05 fixtures are channel-only rasters (`1` on channels, `NoData` elsewhere).
2. Candidate stream rasters are full-extent binary (`0/1`) over the valid domain.
3. Full-extent visual and metric interpretation can therefore conflate basin behavior with background-encoding stage differences.

Basin-masked check (`bound.tif > 0`) on run1:

| Fixture | Candidate (basin) | Oracle (basin) | Delta | FP (basin) | FN (basin) |
|---|---:|---:|---:|---:|---:|
| `gatecreek_10m_30_2` | 12048 | 47810 | -35762 | 0 | 35762 |
| `clueless_aftertaste_anchor_10_100` | 124 | 341 | -217 | 0 | 217 |

Implication:
- Within basin, candidate is a strict subset of oracle for these fixtures (over-pruned relative to oracle), even though unmasked summaries may appear mixed due to stage/encoding differences.

## Spec deficiency report (ordered by severity)

| Deficiency ID | Severity | Evidence source | Why it blocks root-cause attribution | Proposed neutral spec text |
|---|---|---|---|---|
| SD-01 | high | E-001, E-002, E-020 | F-003/F-004 cannot be separated into algorithm drift vs wrong thresholds while provenance is inferred. | Require fixture threshold provenance class (`authoritative`/`inferred`) and disallow closure of high/medium parity findings with inferred thresholds. |
| SD-02 | high | E-003, E-004, E-005 | Snapshot-copy oracle does not encode executable/runtime contract; parity may target a moving or mixed oracle behavior. | Add mandatory oracle runtime manifest: mode, executable identity, build/revision, preprocessing, pointer/no-data assumptions. |
| SD-03 | medium | E-007, E-008 | Ambiguous area units and conversion rounding can shift source qualification boundaries by whole cells. | Specify upstream-area units as contributing-cell counts and define `csa_cells = max(1, nearest_integer(csa_ha / cell_area_ha))`. |
| SD-04 | medium | E-009, E-010 | MSCL semantics were underspecified around half-cell terminal starts and cell-size scaling, affecting prune boundaries. | Define link-length contract for normal and terminal-head starts, and compare in meters after cell-size scaling. |
| SD-05 | medium | E-011, E-009 | Epsilon and strict/weak inequality semantics were partially implicit, enabling silent behavior drift. | Define default epsilon, strict shortest-link improvement rule, and strict prune predicate with epsilon. |
| SD-06 | medium | E-012 | Existing wording allowed Phase A global stabilization interpretation that is not aligned with observed one-pass inline behavior. | Specify Phase A as a single row-major pass with inline topology mutation and no extra full-grid rescan before Phase B. |
| SD-07 | medium | E-013, E-014 | Receiver-group ordering and only-channel guard details were not fully explicit, reducing reproducibility of branch decisions. | Specify receiver-group ordering by first encounter and the exact only-channel guard trigger condition. |
| SD-08 | medium | E-013, E-015 | Candidate validity behavior in-pass was not explicit; silent stale handling vs explicit failure changes parity and diagnostics. | Specify strict candidate validity contract and explicit failure behavior for invalid non-self-receiver selections. |
| SD-09 | medium | E-016 | Acceptance vs diagnostic metrics were conflated, obscuring what constitutes parity pass/fail vs triage telemetry. | Define normative acceptance (exact binary + deterministic rerun hash) and diagnostic metrics (counts/components/junctions/reachability/context). |
| SD-10 | low | E-018, E-019 | No required mismatch-localization protocol existed for first-divergence and sensitivity, slowing root-cause convergence. | Add mandatory divergence-localization and sensitivity sections to parity investigation artifacts. |

All high/medium ambiguities are now classified by `SD-01` through `SD-09`.

## First-divergence localization method and findings

### Method

1. Load retained run1 candidate and oracle stream rasters from `/tmp/ifolp_wp05_remediate/run1`.
2. Build binary stream masks (`value > 0`, valid finite and not NoData).
3. Compute XOR mismatch mask and record first mismatch in row-major order.
4. Attach local context: FP/FN type, upstream-area value, D8 code, topology context, component size. (E-018)

### Findings

| Fixture | First mismatch (row,col; 1-based) | Type | Upstream area (cells) | D8 code | Local context |
|---|---|---:|---:|---:|---|
| `blackwood_60_5` | `(13,31)` | FP | `669` | `16` | terminal, component size `178` |
| `clueless_aftertaste_anchor_10_100` | `(2,122)` | FP | `13974` | `128` | terminal, component size `180` |
| `gatecreek_10m_30_2` | `(1,53)` | FP | `10814` | `2` | terminal, component size `94` |

Pass-level localization note:
- Candidate retained state shows deterministic pass counts (`Phase A=1` for all fixtures; `Phase B=2/3/2` for blackwood/anchor/gatecreek). (E-017)
- Oracle pass-level traces are not captured in current WP-00/05 snapshot-copy workflow, so direct oracle-pass first-divergence localization remains open. (E-003)

## Topology-context mismatch decomposition (FP/FN)

| Fixture | FP total | FN total | FP head/mid/junction/terminal | FN head/mid/junction/terminal | Dominant component pattern |
|---|---:|---:|---|---|---|
| `blackwood_60_5` | 2294 | 2173 | `96 / 74 / 0 / 2124` | `346 / 135 / 11 / 1681` | FN concentrated in one large oracle component (`2173` cells); FP split across several large candidate components |
| `clueless_aftertaste_anchor_10_100` | 175 | 217 | `6 / 5 / 0 / 164` | `20 / 15 / 0 / 182` | Both FP/FN concentrated in the primary large component |
| `gatecreek_10m_30_2` | 30187 | 35762 | `2121 / 2256 / 17 / 25793` | `2842 / 2405 / 59 / 30456` | FP dominated by one very large candidate component (`20549` mismatch cells); FN concentrated in main oracle component (`35762`) |

Evidence: E-018.

## Threshold sensitivity around decision boundaries

### Method

For each fixture, rerun IFOLP around CSA/MSCL boundary perturbations and epsilon perturbations:
- CSA perturbation near one-cell conversion boundaries,
- MSCL perturbation around baseline threshold,
- epsilon sweep `1e-6`, `1e-5`, `1e-4`.

Evidence: E-019.

### Results summary

| Fixture | CSA perturbation effect | MSCL perturbation effect | Epsilon perturbation effect | Regression note |
|---|---|---|---|---|
| `blackwood_60_5` | `59.98` and `60.08` produced no change vs baseline (`diff=4467`) | `4.0` worsened (`4479`), `6.0` near-baseline (`4470`) | no change (`4467`) | none |
| `gatecreek_10m_30_2` | small movement only (`65950` at `29.99`, `65947` at `30.01`) | small movement only (`65951` at `1.0` and `3.0`) | no change (`65949`) | none |
| `clueless_aftertaste_anchor_10_100` | no change (`392`) | no change (`392`) | no change (`392`) | confirms no F-002 regression under tested perturbations |

Interpretation:
- Residual F-003/F-004 drift is weakly sensitive to small threshold perturbations and insensitive to epsilon perturbation in tested range.
- F-002 retained-state behavior is stable across tested CSA/MSCL/epsilon perturbations.

## Known / Unknown / Open questions

| Category | Item | Status |
|---|---|---|
| known | TopAZ source contracts for area conversion, length scaling, epsilon, and pass cadence are identifiable and now spec-addressable. | closed |
| known | Current WP-00/05 oracle staging is checksum-pinned snapshot copy, not native-runtime execution. | closed |
| known | F-003/F-004 mismatch topology is terminal-heavy and concentrated in large components. | closed |
| unknown | Authoritative CSA/MSCL provenance artifact for blackwood fixture. | open |
| unknown | Authoritative CSA/MSCL provenance artifact for gatecreek fixture. | open |
| unknown | Oracle native-runtime build/options used to generate fixture `netw0.tif` for non-anchor fixtures. | open |
| open question | Do non-anchor oracle rasters originate from the same runtime contract as anchor (`WhiteBoxToolsTopazEmulator`) or from a distinct TopAZ-native pipeline? | open |
| open question | Are remaining F-003/F-004 deltas dominated by fixture provenance or by still-missing pass-level behavioral clauses after this spec patch? | open |

## Next hypotheses (H-005+)

| Hypothesis ID | Fingerprint | Target finding(s) | Proposed bounded action | Expected signal |
|---|---|---|---|---|
| H-005 | `provenance.authoritative_threshold_backfill.non_anchor.v1` | F-003, F-004 | Backfill authoritative blackwood/gatecreek threshold artifacts and rebuild fixture manifest provenance fields. | If provenance was wrong, parity moves materially without algorithm edits. |
| H-006 | `oracle.runtime_contract.native_vs_snapshot.v1` | F-003, F-004 | Add native-runtime oracle capture mode with executable/build/options manifest, then compare to snapshot-copy oracle outputs. | If runtime mismatch exists, snapshot/native oracle deltas appear before IFOLP comparison. |
| H-007 | `phase_a.single_pass_contract.trace_localization.v1` | F-003 | Add non-invasive harness trace export (pass-level source/receiver decisions) and localize first algorithmic divergence pass/cell. | First divergence can be attributed to a specific pass-level rule, reducing ambiguity. |
| H-008 | `phase_b.candidate_validity_contract.strictness.v1` | F-003, F-004 | Validate strict invalid-candidate failure semantics vs permissive stale-skip behavior under parity harness. | Material parity movement would indicate candidate-validity contract mismatch. |

## Root-cause confidence update

| Finding ID | Confidence | Rationale |
|---|---|---|
| F-002 | medium-high | Anchor mismatch remains low and stable under CSA/MSCL/epsilon perturbation sweep; no regression signal detected. |
| F-003 | medium | Behavioral contracts now clearer, but blackwood threshold provenance remains inferred and prevents high-confidence closure. |
| F-004 | low-medium | Gatecreek drift remains very large and weakly sensitive to perturbation; provenance/runtime uncertainty is still dominant. |
