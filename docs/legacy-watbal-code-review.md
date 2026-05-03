# Legacy WEPP Water-Balance Code Review

Purpose: summarize why the legacy `watbal` implementation accumulated too many special conditions, identify concrete evidence in the Fortran sources, and set practical guardrails for the new `.f90` non-clean-room rewrite.

## Executive Summary

The core failure is not that water balance is hydrologically simple. It is not. The problem is that the legacy design mixes the water-balance kernel, routing feedback, timestep policy, mode/version compatibility, plant growth updates, file output, diagnostics, and input repair inside one mutable global-state procedure. That made each new domain requirement land as another branch in the same routine or in a nearby common-block consumer.

The hourly implementation shows the maintenance outcome explicitly: `watbal_hourly.for` says it was kept separate to isolate bugs, had not kept up with winter/subsurface changes, and that `watbal` "has too many special conditions and is too large" (`/workdir/wepp-forest/src/watbal_hourly.for:7`, `/workdir/wepp-forest/src/watbal_hourly.for:9`). The daily routine dispatches into this fork by global `ui_run` rather than by an explicit timestep strategy (`/workdir/wepp-forest/src/watbal.for:247`, `/workdir/wepp-forest/src/watbal.for:255`).

For the rewrite, keep the essential hydrology, but do not preserve the accidental architecture. The new implementation should have explicit inputs/outputs, one timestep-independent process sequence, separated output/diagnostics, documented mode contracts, and conservation/regression checks at every state boundary.

## Findings

### 1. Water balance is not a bounded component; it is a global-state orchestrator

Impact: highest. This makes correctness depend on call order and hidden common-block side effects.

Evidence:

- `watbal` includes a wide set of common blocks spanning canopy, drainage, climate, hydrology, irrigation, storage, structure, tillage, water, winter, contour, channel routing, hourly mode, and average parameters (`/workdir/wepp-forest/src/watbal.for:103`, `/workdir/wepp-forest/src/watbal.for:193`).
- The comments identify mutable outputs from unrelated domains: `roffon/rvolon`, `soilw/sep/ul/fin/ep/es/cv/fc`, `norun/watblf`, and `avsat/avbd` (`/workdir/wepp-forest/src/watbal.for:152`, `/workdir/wepp-forest/src/watbal.for:178`, `/workdir/wepp-forest/src/watbal.for:192`).
- `contin` calls `watbal` from inside the daily simulation flow (`/workdir/wepp-forest/src/contin.for:1064`, `/workdir/wepp-forest/src/contin.for:1068`), then immediately uses `norun`/`runoff` to decide whether to route sediment (`/workdir/wepp-forest/src/contin.for:1162`, `/workdir/wepp-forest/src/contin.for:1227`).
- `irs` documents the fragility directly: `watbal()` affects global variables, needs the whole `runoff` array current up to the current OFE, and a non-original sequence "may be effecting other global variables" (`/workdir/wepp-forest/src/irs.for:541`, `/workdir/wepp-forest/src/irs.for:553`).

Why this caused drift: new behavior could not be localized. A change for routing, irrigation, hourly lateral flow, frozen soil, output, or channel storage could all require edits inside `watbal` because the routine owns both physics and system integration state.

### 2. Daily and hourly behavior forked instead of sharing one process model

Impact: very high. The fork created two large routines with overlapping code and separate bug histories.

Evidence:

- `watbal` dispatches to `watbal_hourly` when `ui_run.eq.1` (`/workdir/wepp-forest/src/watbal.for:247`, `/workdir/wepp-forest/src/watbal.for:255`).
- `watbal_hourly` states that it has not kept up with newer winter/subsurface changes (`/workdir/wepp-forest/src/watbal_hourly.for:7`, `/workdir/wepp-forest/src/watbal_hourly.for:8`).
- Both files duplicate the same include surface, initialization, infiltration, percolation, lateral-flow, surface-drainage, plant-growth, and output structure (`/workdir/wepp-forest/src/watbal.for:75`, `/workdir/wepp-forest/src/watbal.for:189`; `/workdir/wepp-forest/src/watbal_hourly.for:78`, `/workdir/wepp-forest/src/watbal_hourly.for:190`).
- The hourly routine hard-codes `ui_LFtstp = 24` inside the routine (`/workdir/wepp-forest/src/watbal_hourly.for:457`, `/workdir/wepp-forest/src/watbal_hourly.for:459`) and then loops over the timestep (`/workdir/wepp-forest/src/watbal_hourly.for:481`, `/workdir/wepp-forest/src/watbal_hourly.for:483`).
- Shared lower-level routines were patched with `ui_run` branches too: `purk` divides seepage and layer updates by `ui_LFtstp` when hourly mode is enabled (`/workdir/wepp-forest/src/purk.for:167`, `/workdir/wepp-forest/src/purk.for:185`), and `perc` changes saturation/percolation behavior under `ui_run` (`/workdir/wepp-forest/src/perc.for:157`, `/workdir/wepp-forest/src/perc.for:178`).

Why this caused drift: the fork was not only in one file. Hourly behavior leaked into input, tillage, percolation, output, and global common blocks. That made parity between daily and hourly modes a manual audit problem.

### 3. Water balance and routing form a circular dependency

Impact: very high. Runoff is both an input to water balance and a value mutated by water balance.

Evidence:

- Infiltration subtracts or recomputes runoff/runon depending on channel and OFE context (`/workdir/wepp-forest/src/watbal.for:352`, `/workdir/wepp-forest/src/watbal.for:383`).
- Channel and upstream subsurface flow are added directly from routing/channel topology state (`/workdir/wepp-forest/src/watbal.for:404`, `/workdir/wepp-forest/src/watbal.for:424`).
- Surface drainage is computed after routing concerns are already known, with the legacy comment admitting it should really be added back to current-day runoff but routing and erosion have already happened (`/workdir/wepp-forest/src/watbal.for:797`, `/workdir/wepp-forest/src/watbal.for:815`; same comment in `/workdir/wepp-forest/src/watbal_hourly.for:864`, `/workdir/wepp-forest/src/watbal_hourly.for:882`).
- The routine then mutates `runoff` and `norun` directly (`/workdir/wepp-forest/src/watbal.for:828`, `/workdir/wepp-forest/src/watbal.for:844`; `/workdir/wepp-forest/src/watbal_hourly.for:912`, `/workdir/wepp-forest/src/watbal_hourly.for:927`).

Why this caused drift: late-discovered water terms had no clean event boundary. The code patched routing state after the fact, then added flags and call-order exceptions to avoid rerunning the larger hydrology/erosion sequence.

### 4. Mode, version, and feature switches are distributed and implicit

Impact: high. Behavior is controlled by hidden files, global flags, data-version numbers, and simulation-mode flags scattered through the call graph.

Evidence:

- Hourly mode is enabled by the existence of `wepp_ui.txt` in `main` (`/workdir/wepp-forest/src/main.for:161`, `/workdir/wepp-forest/src/main.for:170`).
- The hourly common block has no real description and exposes control plus state arrays globally (`/workdir/wepp-forest/src/wathour.inc:4`, `/workdir/wepp-forest/src/wathour.inc:9`, `/workdir/wepp-forest/src/wathour.inc:26`, `/workdir/wepp-forest/src/wathour.inc:48`).
- Input behavior changes under `ui_run`, including saturation caps (`/workdir/wepp-forest/src/input.for:532`, `/workdir/wepp-forest/src/input.for:536`) and hourly conductivity state (`/workdir/wepp-forest/src/input.for:927`, `/workdir/wepp-forest/src/input.for:929`).
- Lateral-flow behavior branches on `solwpv` inside `watbal` (`/workdir/wepp-forest/src/watbal.for:575`, `/workdir/wepp-forest/src/watbal.for:590`, `/workdir/wepp-forest/src/watbal.for:621`, `/workdir/wepp-forest/src/watbal.for:734`).
- Output headers branch on `ui_run` and `ivers` in `outfil` (`/workdir/wepp-forest/src/outfil.for:199`, `/workdir/wepp-forest/src/outfil.for:209`; `/workdir/wepp-forest/src/outfil.for:430`, `/workdir/wepp-forest/src/outfil.for:440`).

Why this caused drift: the effective contract of "water balance mode" is not declared in one place. Each consumer discovers a flag and locally interprets it.

### 5. Output and diagnostics are embedded in the physics routine

Impact: high. This makes a model-process change also risk output contracts, file units, diagnostics, and hard-coded investigation cases.

Evidence:

- `watbal` writes plant output, soil output, and water-balance output directly (`/workdir/wepp-forest/src/watbal.for:909`, `/workdir/wepp-forest/src/watbal.for:916`; `/workdir/wepp-forest/src/watbal.for:1043`, `/workdir/wepp-forest/src/watbal.for:1055`; `/workdir/wepp-forest/src/watbal.for:1073`, `/workdir/wepp-forest/src/watbal.for:1125`).
- `watbal_hourly` does the same, plus a hard-coded opt-in diagnostic file and hard-coded year/day windows (`/workdir/wepp-forest/src/watbal_hourly.for:274`, `/workdir/wepp-forest/src/watbal_hourly.for:278`; `/workdir/wepp-forest/src/watbal_hourly.for:934`, `/workdir/wepp-forest/src/watbal_hourly.for:1022`).
- `watbal` contains hard-coded observation tags for a specific 1987 date/OFE window (`/workdir/wepp-forest/src/watbal.for:1074`, `/workdir/wepp-forest/src/watbal.for:1092`).
- `watbalPrint` was split out only for watershed/channel water output after channel routing added surface storage (`/workdir/wepp-forest/src/watbalprint.for:5`, `/workdir/wepp-forest/src/watbalprint.for:7`), but it still recomputes water-balance terms from global state and writes unit 35 directly (`/workdir/wepp-forest/src/watbalprint.for:56`, `/workdir/wepp-forest/src/watbalprint.for:134`).

Why this caused drift: output compatibility became a reason to keep process code entangled. Diagnostics added for one failure mode remained in the core routine and increased branch surface.

### 6. Unit, geometry, and runoff-scaling conversions are repeated at multiple boundaries

Impact: medium-high. These conversions are required, but the repetition makes them easy to apply inconsistently.

Evidence:

- `watbal` computes runon/subsurface runon with `fwidth`, `slplen`, `efflen`, and `totlen` scaling inline (`/workdir/wepp-forest/src/watbal.for:356`, `/workdir/wepp-forest/src/watbal.for:366`).
- The water-balance output uses one runoff expression for contour cases and another for ordinary OFEs (`/workdir/wepp-forest/src/watbal.for:1094`, `/workdir/wepp-forest/src/watbal.for:1123`).
- `contin` has its own runoff-volume scaling for contour and non-contour cases (`/workdir/wepp-forest/src/contin.for:1245`, `/workdir/wepp-forest/src/contin.for:1254`).
- `watbalPrint` recomputes channel subsurface runon from topology and area terms (`/workdir/wepp-forest/src/watbalprint.for:72`, `/workdir/wepp-forest/src/watbalprint.for:82`).
- Output documentation labels `Q`, `QOFE`, `Area`, and profile stores in `outfil`, separate from the writes that must match them (`/workdir/wepp-forest/src/outfil.for:620`, `/workdir/wepp-forest/src/outfil.for:654`).

Why this caused drift: each new output or mode could choose a slightly different depth/area basis. The legacy comments show this explicitly with the change from `slplen` to `totlen` to match event output (`/workdir/wepp-forest/src/watbal.for:1108`, `/workdir/wepp-forest/src/watbal.for:1110`).

### 7. Inline repair/clamping logic hides data-contract decisions inside model flow

Impact: medium. Some clamps are valid physical bounds, but many are mixed into process code without a contract boundary.

Evidence:

- Input clamps soil saturation differently for hourly vs daily mode (`/workdir/wepp-forest/src/input.for:532`, `/workdir/wepp-forest/src/input.for:536`).
- Input imposes conductivity floors with version-specific units/thresholds (`/workdir/wepp-forest/src/input.for:596`, `/workdir/wepp-forest/src/input.for:604`) and bedrock thickness limits (`/workdir/wepp-forest/src/input.for:655`, `/workdir/wepp-forest/src/input.for:666`).
- `watbal` repeatedly clamps frozen-adjusted capacity values to zero (`/workdir/wepp-forest/src/watbal.for:505`, `/workdir/wepp-forest/src/watbal.for:525`; `/workdir/wepp-forest/src/watbal.for:569`, `/workdir/wepp-forest/src/watbal.for:590`).
- `watbal` silently repairs `efflen` when zero (`/workdir/wepp-forest/src/watbal.for:836`, `/workdir/wepp-forest/src/watbal.for:840`).

Why this caused drift: repair behavior became path-dependent. The caller cannot tell whether an input was accepted, normalized, capped for physics, or patched to avoid a divide-by-zero.

### 8. Historical comments preserve uncertainty but not executable checks

Impact: medium. The comments are valuable evidence, but they are not a safety net.

Evidence:

- `watbal` asks whether field capacity is constant (`/workdir/wepp-forest/src/watbal.for:287`, `/workdir/wepp-forest/src/watbal.for:290`), whether a residue calculation should use another routine (`/workdir/wepp-forest/src/watbal.for:477`, `/workdir/wepp-forest/src/watbal.for:480`), and whether hemispheric day-length assumptions apply (`/workdir/wepp-forest/src/watbal.for:848`, `/workdir/wepp-forest/src/watbal.for:872`).
- The old water-balance check is commented out rather than enforced (`/workdir/wepp-forest/src/watbal.for:977`, `/workdir/wepp-forest/src/watbal.for:999`; duplicated in `/workdir/wepp-forest/src/watbal_hourly.for:1152`, `/workdir/wepp-forest/src/watbal_hourly.for:1174`).
- `purk` and `perc` comments document several output-changing algorithm choices and known index/common-block concerns (`/workdir/wepp-forest/src/purk.for:27`, `/workdir/wepp-forest/src/purk.for:88`; `/workdir/wepp-forest/src/perc.for:9`, `/workdir/wepp-forest/src/perc.for:13`).

Why this caused drift: future maintainers inherited warnings but not invariants. The same uncertainty then reappeared as local special cases.

## Accidental vs Essential Complexity

Essential complexity to preserve:

- Layered soil storage, field capacity, wilting point, porosity, saturated conductivity, and bottom/restrictive-layer behavior (`/workdir/wepp-forest/src/perc.for:131`, `/workdir/wepp-forest/src/perc.for:190`).
- Frozen-soil water accounting and frozen-adjusted capacity limits (`/workdir/wepp-forest/src/watbal.for:505`, `/workdir/wepp-forest/src/watbal.for:525`; `/workdir/wepp-forest/src/watbal.for:1026`, `/workdir/wepp-forest/src/watbal.for:1039`).
- Infiltration, percolation, ET, tile drainage, lateral subsurface flow, surface drainage, and plant-water-use sequencing (`/workdir/wepp-forest/src/watbal.for:331`, `/workdir/wepp-forest/src/watbal.for:552`, `/workdir/wepp-forest/src/watbal.for:598`, `/workdir/wepp-forest/src/watbal.for:921`).
- Hillslope/OFE/channel topology, runon/runoff transfer, and watershed surface-storage/baseflow reporting (`/workdir/wepp-forest/src/watbal.for:352`, `/workdir/wepp-forest/src/watbal.for:424`; `/workdir/wepp-forest/src/watbalprint.for:87`, `/workdir/wepp-forest/src/watbalprint.for:96`).
- Compatibility with existing daily water-balance output columns, units, and meaning (`/workdir/wepp-forest/src/outfil.for:620`, `/workdir/wepp-forest/src/outfil.for:654`).

Accidental complexity to remove:

- Forked daily/hourly routines with duplicated physics (`/workdir/wepp-forest/src/watbal.for:247`, `/workdir/wepp-forest/src/watbal_hourly.for:9`).
- Hidden file-triggered behavior (`/workdir/wepp-forest/src/main.for:161`, `/workdir/wepp-forest/src/main.for:170`).
- Global common-block state as the primary data contract (`/workdir/wepp-forest/src/watbal.for:103`, `/workdir/wepp-forest/src/watbal.for:193`; `/workdir/wepp-forest/src/wathour.inc:26`, `/workdir/wepp-forest/src/wathour.inc:48`).
- Late mutation of routing outputs inside water balance (`/workdir/wepp-forest/src/watbal.for:797`, `/workdir/wepp-forest/src/watbal.for:844`).
- Embedded output and hard-coded diagnostics in the process routine (`/workdir/wepp-forest/src/watbal_hourly.for:934`, `/workdir/wepp-forest/src/watbal_hourly.for:1022`).
- Scattered version/mode conditionals instead of named compatibility policies (`/workdir/wepp-forest/src/watbal.for:575`, `/workdir/wepp-forest/src/watbal.for:734`; `/workdir/wepp-forest/src/input.for:638`, `/workdir/wepp-forest/src/input.for:667`).

## Rewrite Guardrails

Use these as a checklist for the `.f90` rewrite.

### Structural directives (incorporated from follow-up architecture review)

1. Decompose by physical process, not by daily-vs-hourly routine boundary.
   - Shared code is acceptable only if it is a pipeline of small kernels (for example infiltration, percolation, lateral flow, ET, drainage, storage update), not one large "shared core" monolith with new conditionals.
   - If a decomposition does not reduce branch/coupling surface at the kernel boundary, reject it.

2. Make data flow compiler-checkable.
   - Treat this as higher priority than syntax conversion alone.
   - Convert read-only shared state to explicit `intent(in)` inputs at routine boundaries as early as practical.
   - Convert read/write effects into explicit return/update structures so compilers and tests can detect unintended mutation.
   - Keep a mutation inventory: every legacy common-block write must map to one explicit output field.

3. Replace `ui_run` integer fan-out with one scheduler dispatch boundary.
   - `ui_run` should select a typed scheduler policy once near the top-level control flow.
   - Lower-level process kernels must not branch on global mode flags.
   - Remove mode interpretation from multi-file consumers by pushing mode-specific behavior into scheduler adapters and parameter sets.

4. Stage sequencing to protect parity signal.
   - Do not combine broad dataflow refactors and physics behavior changes in the same step.
   - Preferred order: characterize baseline -> isolate scheduler boundary -> process-kernel extraction -> common-block surface reduction.
   - This remains a non-clean-room rewrite: preserve/justify behavior against legacy evidence while removing accidental architecture.

1. Define a narrow water-balance state contract.
   - Inputs: weather water terms, current OFE/channel geometry, soil-layer state, frozen state, vegetation/ET inputs, drainage parameters, upstream water terms, and mode/timestep policy.
   - Outputs: updated soil-layer state, seepage, lateral flow, tile drainage, surface drainage, ET components, water stress, runoff delta/request, and diagnostic balance terms.
   - Do not read feature flags or hidden files inside the kernel.

2. Keep one process implementation with timestep as data.
   - Daily mode should be a timestep policy, not a separate routine.
   - Hourly mode should reuse the same infiltration, percolation, drainage, lateral-flow, and surface-drainage steps with explicit `dt`.
   - No `ui_run` branches in lower-level process routines. Pass the timestep and mode-specific parameters explicitly.

3. Separate physics from orchestration.
   - The kernel may compute surface drainage and runoff deltas, but the caller should own routing reentry or runoff application.
   - Do not mutate global `runoff`, `norun`, `watblf`, `roffon`, or channel storage from inside the kernel.
   - Make circular dependencies explicit: pre-routing inputs, water-balance results, and post-routing updates should be separate phases.

4. Centralize compatibility policies.
   - Replace scattered `solwpv`, `ivers`, `contrs`, and hourly special cases with named policy objects or small pure functions.
   - Each policy should document its legacy line evidence, output impact, and regression cases.
   - Do not silently change user-visible columns, units, or meanings.

5. Move output and diagnostics out of the model kernel.
   - The kernel should return values; writers should format unit 35/36/39 output.
   - Hard-coded investigation windows and files such as `qcap_diagnostic.csv` should become external diagnostics, not core model behavior.
   - Preserve legacy output compatibility with explicit mapping tests from returned fields to columns.

6. Make units and geometry bases explicit.
   - Name values by basis: `depth_m`, `depth_mm`, `volume_m3`, `ofe_area_m2`, `slplen_basis`, `efflen_basis`, `totlen_basis`.
   - Put `runoff over eff length`, `single-OFE scaled runoff`, and channel `runoff over area` conversions in one module.
   - Add tests for contour, non-contour, single-OFE, multi-OFE, and channel cases.

7. Treat clamps as contracts, not incidental repairs.
   - Distinguish input normalization, physical bounds, numerical guards, and legacy-compatibility caps.
   - Each clamp should have a named reason and be observable in diagnostics or validation results.
   - Avoid silent fallbacks such as `efflen = slplen` inside process code; validate before entry or return an explicit error/status.

8. Restore executable conservation checks.
   - Replace the commented water-balance check with a regressionable balance report: initial storage + inputs - outputs - final storage.
   - Track liquid and frozen water separately, then provide total profile storage.
   - Validate daily and hourly aggregation against selected legacy scenarios before changing tolerances.

9. Keep lower-level routines pure where practical.
   - `percolation`, `lateral_flow`, `tile_drainage`, `surface_drainage`, and `storage_limits` should take explicit layer arrays and return explicit deltas.
   - No routine should both compute a flux and write unrelated output.
   - No routine should patch shared arrays because a caller might need them current.

10. Preserve legacy behavior intentionally.
    - For every behavior retained only for compatibility, cite the legacy source line and add a focused regression.
    - For every behavior changed, document the old behavior, the new behavior, the expected output impact, and the acceptance evidence.
    - Avoid speculative abstractions; only introduce structure that removes confirmed coupling or duplication.

Anti-patterns to avoid:

- Copying the daily routine and patching an hourly variant.
- Adding a new mode flag to common blocks and branching across many files.
- Reading sentinel files from model code to enable features.
- Writing output, diagnostics, or CSV files from the water-balance kernel.
- Applying unit conversions inline at every call site.
- Repairing invalid state silently inside hydrologic process code.
- Treating `.f90` conversion as success without reducing mutation/coupling surfaces.
- Building a tidier monolith that preserves cross-domain branch accumulation.
- Leaving "need to look at this" comments without an invariant, test, or issue.
- Recomputing upstream/channel topology terms independently in output writers.

## Review Scope and Evidence Index

Primary files reviewed:

- `/workdir/wepp-forest/src/watbal.for`
- `/workdir/wepp-forest/src/watbal_hourly.for`

Coupling context reviewed:

- `/workdir/wepp-forest/src/main.for`: mode selection and hourly aggregate initialization.
- `/workdir/wepp-forest/src/contin.for`: daily control loop, `watbal` call, routing after water-balance mutation, hourly aggregate accumulation.
- `/workdir/wepp-forest/src/irs.for`: alternate call ordering and explicit comments about `watbal` global side effects.
- `/workdir/wepp-forest/src/wshdrv.for`: watershed initialization call and split channel water-balance printing.
- `/workdir/wepp-forest/src/outfil.for`: water-balance output headers and mode-specific header selection.
- `/workdir/wepp-forest/src/wathour.inc`: hourly-mode common blocks and global state contract.
- `/workdir/wepp-forest/src/perc.for`: percolation behavior and hourly-specific branches.
- `/workdir/wepp-forest/src/purk.for`: percolation routing and hourly-specific seepage scaling.
- `/workdir/wepp-forest/src/tilage.for`: drainage setup and hourly conductivity state propagation.
- `/workdir/wepp-forest/src/input.for`: mode/version-specific input parsing, normalization, and hydraulic-property setup.
- `/workdir/wepp-forest/src/watbalprint.for`: channel/watershed water-balance output extraction from global state.
