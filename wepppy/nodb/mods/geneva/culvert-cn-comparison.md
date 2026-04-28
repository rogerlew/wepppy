# Geneva vs Culvert CN Implementation Comparison

Status: Working comparison note  
Last Updated: 2026-04-28
Scope: Compare the current Geneva CN implementation in `wepppy`/`wepppyo3` against the CN implementation in `/workdir/Culvert_web_app`, and interpret the differences using guidance from `resources/Wildcat5/rmrs_gtr334.pdf`.

## 1. Bottom Line

Geneva is the more scientifically defensible implementation for the Geneva use case.

Reason:

- Geneva keeps spatial heterogeneity through HRUs instead of collapsing to one basin-scale CN.
- Geneva explicitly handles invalid or unresolved `hydgrpdcd` classes.
- Geneva includes burn-severity and hydrophobicity adjustments, which Wildcat5 treats as central to post-fire runoff response.
- Geneva supports both `Ia/S = 0.20` and `Ia/S = 0.05` and carries timestep excess into a unit hydrograph.

Culvert is simpler and more transparent in one narrow respect: it uses an explicit CN lookup table for `NLCD x HSG -> CN`. But it gives up too much scientific fidelity upstream and downstream:

- no HRU response,
- basin-scale CN collapse,
- weak `hydgrpdcd` governance,
- no burn severity adjustment,
- no hydrophobicity adjustment.

## 2. Evidence Basis

Geneva code reviewed:

- `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
- `wepppy/nodb/mods/geneva/collaborators/cn_table_service.py`
- `wepppy/nodb/mods/geneva/specification.md`
- `wepppyo3/geneva_core/src/hru.rs`
- `wepppyo3/geneva_core/src/cn.rs`
- `wepppyo3/geneva_core/src/hyetograph.rs`

Culvert code reviewed:

- `/workdir/Culvert_web_app/culvert_app/utils/subroutine_determine_WS_characteristics.py`
- `/workdir/Culvert_web_app/culvert_app/utils/subroutine_graphical_peak_discharge_Est.py`
- `/workdir/Culvert_web_app/culvert_app/utils/subroutine_back_calculating_runoff.py`

Wildcat5 guidance reviewed:

- `wepppy/nodb/mods/geneva/resources/Wildcat5/rmrs_gtr334.pdf`
- most relevant sections: 3.22, 3.4, 4.22, 4.24, 4.25

External HSG product reviewed:

- `https://github.com/rogerlew/us-conus-ssurgo-hydgrpdcd`
- most relevant artifacts: `README.md`, `build_hydgrpdcd.py`

## 3. Wildcat5 Guidance That Matters Here

Wildcat5 provides a useful comparison frame because Geneva is explicitly aligned to the RMRS-GTR-334 method family.

Key takeaways from `rmrs_gtr334.pdf`:

- storm distribution matters for peak flow, especially when CN is used to generate interval rainfall excess,
- distributed CN with unit hydrographs is the default conceptual structure,
- both `Ia/S = 0.20` and `Ia/S = 0.05` are supported,
- CN selection is extremely sensitive and often controls peaks and volumes more than storm depth or duration,
- post-fire CN adjustment is pragmatic and judgment-based, but fire severity and water repellency matter,
- post-fire rainfall-runoff models are most appropriate when direct runoff is driven by rainfall and hydrophobic conditions.

Implication for this comparison:

- an implementation that preserves spatial heterogeneity, supports post-fire modifiers, supports `0.05`, and respects storm distribution effects is closer to Wildcat5,
- an implementation that collapses to one basin CN and omits post-fire modifiers is farther from Wildcat5.

## 4. Comparison Matrix

| Topic | Geneva | Culvert | Comparison Result |
| --- | --- | --- | --- |
| Land cover input | Uses raster `landuse_tif`; current workflow expects NLCD-compatible land use | Uses NLCD raster directly | Roughly equivalent at source-input level |
| Soil-group source family | Uses raster `hydgrpdcd_tif`; current workflow expects SSURGO-compatible HSG source | Uses gSSURGO-derived `hydgrpdcd` raster/polygon workflow | Similar source family only |
| Soil-group product contract | Intended downstream contract matches a canonical coded product model: `0` unresolved, `1..4` valid, invalid codes governed explicitly | Does not preserve a strict coded-product contract once values are extracted and converted through polygons/strings | Geneva clearly stronger |
| `hydgrpdcd` governance | Explicitly treats only `1..4` as valid HSG classes; `0` unresolved, `5/6/7` invalid; routes through fallback or error policy | Handles `1..4` as `A..D`, but `0/5/6/7` fall through as raw strings and are not governed cleanly in downstream mapping | Geneva clearly stronger |
| Runtime CN source | Runtime HRU CN is persisted from Geneva's run-scoped `cn_table.csv` during `prepare_hrus` using exact `NLCD x HSG x burn severity x hydrophobicity` lookup; missing exact rows fall back explicitly to the kernel proxy estimator | Runtime CN comes from an explicit `NLCD x HSG -> CN` lookup CSV | Geneva stronger on configurability/auditability; both now use explicit table-backed runtime CN where Geneva has a matching row |
| Operator transparency and auditability | Run-scoped CN table is exposed through Geneva UI/task flows, with init/reset/modify/audit behavior and optimistic concurrency | No comparable run-scoped CN-table workflow, audit log, or operator-facing edit surface was identified | Geneva clearly stronger |
| Spatial representation during runoff | Keeps multiple HRUs and area-weights excess | Collapses to a single basin `CN_val` before runoff and peak-flow calculation | Geneva clearly stronger |
| Burn severity effect | Included in runtime CN assignment | Not included | Geneva clearly stronger |
| Hydrophobicity / water repellency | Included in runtime CN assignment | Not included | Geneva clearly stronger |
| `Ia/S` options | Supports `0.20` and `0.05` | Fixed at `0.20` | Geneva clearly stronger |
| Runoff generation | Timestep CN excess with closure checks | Lumped TR-55 style runoff depth from one CN | Geneva stronger |
| Hydrograph generation | Unit hydrograph convolution with explicit kernel outputs | TR-55 graphical peak discharge workflow | Geneva stronger for distributed event modeling; Culvert simpler for screening |
| Storm distribution handling | Closed storm-shape enum is wired end-to-end; batch runtime dispatches `uniform`, `neh4_type_b`, `type_i`, `type_ia`, `type_ii`, `type_iii` through Rust hyetograph kernels | Uses TR-55 rainfall-type peak-discharge routine rather than a distributed interval storm path | Geneva stronger |
| Validation and diagnostics | Strong schemas, warnings, closure checks, and dedicated tests | Much lighter contract/test posture | Geneva clearly stronger |

## 5. Confirmed Implementation Differences

### 5.0 `us-conus-ssurgo-hydgrpdcd` is not equivalent to the Culvert `hydgrpdcd` path

The `us-conus-ssurgo-hydgrpdcd` repository is a reproducible HSG product builder, not just another ad hoc consumer of SSURGO-family data.

What it provides:

- an explicit coded raster contract: `0 = unresolved`, `1 = A`, `2 = B`, `3 = C`, `4 = D`,
- an explicit statement that `5`, `6`, and `7` are not used in the product,
- staged fallback logic from `muaggatt.hydgrpdcd` to dominant `component.hydgrp` to `chorizon` texture fallback,
- configurable dual-group policy,
- audit outputs (`hydgrpdcd_lookup.csv`, `hydgrpdcd_metadata.json`),
- tests.

By contrast, Culvert:

- assumes a `hydgrpdcd` raster already exists,
- converts raster classes to polygon attributes in a lossy way,
- stringifies unexpected codes instead of governing them explicitly,
- then reduces soils further to a dominant watershed group.

So the correct comparison is not that Culvert and `us-conus-ssurgo-hydgrpdcd` are roughly equivalent. The correct comparison is:

- they come from the same general SSURGO/HSG problem domain,
- but `us-conus-ssurgo-hydgrpdcd` is a much stronger and more defensible product contract,
- and Geneva's intended HSG handling is much closer to that contract than Culvert's implementation is.

### 5.1 Geneva preserves HRUs; Culvert collapses to basin scale

Geneva prepares multiple HRUs from aligned raster inputs and carries per-HRU CN/excess through the batch kernel. Culvert computes a CN raster, but then reduces each watershed to one `CN_val` and uses that single value in runoff and peak-discharge calculations.

Scientific implication:

- Geneva can represent nonlinear runoff response across mixed land cover and mixed soil groups.
- Culvert discards that heterogeneity before hydrologic response is calculated.

This is a major difference, and it is one of the strongest reasons Geneva is closer to Wildcat5's distributed CN framing.

### 5.2 Culvert mishandles `hydgrpdcd` classes `0`, `5`, `6`, and `7`

Geneva explicitly defines and governs unresolved and invalid `hydgrpdcd` codes. Culvert does not. In Culvert, non-`1..4` values survive as strings in the intermediate polygon layer, but the downstream HSG-to-CN mapping only understands `A`, `B`, `C`, `D`, `A/D`, `B/D`, and `C/D`.

Scientific implication:

- Geneva has a defensible contract for noisy or unexpected HSG input.
- Culvert has silent or weakly governed behavior at exactly the place where Wildcat5 says CN selection is highly sensitive.

### 5.3 Geneva includes post-fire modifiers that Culvert omits

Geneva's current CN-resolution path includes burn severity and hydrophobicity:

- burn severity,
- hydrophobicity / water repellency.

Culvert does not include either modifier.

Wildcat5 relevance:

- RMRS-GTR-334 Section 4.25 explicitly treats post-fire CN adjustment as a practical necessity.
- The manual includes severity-based and water-repellency-based post-fire CN guidance.

Even though part of Geneva's current path still relies on a proxy fallback rather than a fully Wildcat-derived empirical table set, it is directionally much closer to Wildcat5 than Culvert's omission.

### 5.3a Geneva now combines stronger CN-table transparency with active runtime table consumption

Geneva already exposes a run-scoped CN-table workflow through the NoDb/UI/task surface, with initialization, snapshot, modification, reset, and audit logging. That is a stronger operator transparency story than Culvert has.

Geneva now also uses that run-scoped table as the persisted runtime CN source at the `prepare_hrus` boundary:

- exact `NLCD x HSG x burn severity x hydrophobicity` matches in `geneva/data/cn_table.csv` overwrite the provisional kernel CN before `hru_table.parquet` is written,
- downstream batch execution reads those persisted CN values from `hru_table.parquet`,
- missing exact CN-table rows fall back explicitly to the kernel proxy estimator and are marked in persisted artifacts.

So Culvert is no longer stronger on the narrow “active runtime lookup explicitness” point either. Culvert is still simpler because its lookup space is only `NLCD x HSG`, but Geneva now provides the active runtime table path plus richer post-fire dimensions and stronger operator controls.

This should not be read as saying Geneva is generally more hard-coded than Culvert. In several important respects Geneva is less hard-coded and more configurable:

- the user can select NLCD year through the Geneva workflow,
- Geneva can optionally consume a burn severity raster,
- Geneva exposes hydrophobicity-related configuration controls,
- Geneva carries those post-fire modifiers into runtime CN assignment.

The narrower point is now about lookup breadth and fallback policy:

- in Geneva today, the final persisted CN value comes from the run-scoped CN table when an exact row exists, with explicit estimator fallback only for missing rows,
- in Culvert today, the final CN value comes from a simpler direct lookup table.

That is a difference in runtime CN-resolution mechanism, not a statement that Geneva is less configurable overall.

### 5.4 Geneva storm distribution wiring is now implemented end-to-end

Wildcat5 explicitly says storm distribution affects flood peak, especially with CN-based interval excess. Geneva now executes selected storm shape in runtime batch orchestration via Rust hyetograph dispatch (`uniform`, `neh4_type_b`, `type_i`, `type_ia`, `type_ii`, `type_iii`), including embedded-window extraction for legacy Type I/IA/II/III short-duration events.

Scientific implication:

- Geneva no longer forces uniform rainfall in Python batch orchestration.
- Peak-flow sensitivity now follows the selected storm-shape assumption at run time.

Culvert still uses a simpler TR-55 style graphical peak-discharge path rather than a timestep-distributed storm-excess-hydrograph workflow.

### 5.5 Culvert's CN aggregation is weaker than it looks

Culvert's watershed `CN_val` is derived from the CN raster after spatial reduction. The implementation averages unique CN values and rounds upward, rather than performing a proper area-weighted pixel-count mean.

Scientific implication:

- this can bias basin CN upward,
- it further weakens an already basin-collapsed representation,
- it is less defensible than a proper area-weighted aggregation.

## 6. Strengths and Shortcomings

### 6.1 Geneva strengths

- Preserves HRU-scale heterogeneity through runoff and hydrograph computation.
- Closer to the `us-conus-ssurgo-hydgrpdcd` coded-raster contract than Culvert is.
- Explicitly governs invalid and unresolved HSG input.
- Stronger operator transparency around CN editing and auditability.
- More configurable post-fire inputs than Culvert, including optional burn severity and hydrophobicity controls.
- Includes burn severity and hydrophobicity effects.
- Supports both `lambda=0.20` and `lambda=0.05`.
- Selected storm-shape runtime dispatch is implemented and persisted in run artifacts/report assumptions.
- Provides stronger diagnostics, closure checks, and regression coverage.
- Better matches Wildcat5's post-fire modeling structure.

### 6.2 Geneva shortcomings

- The seed CN table does not yet contain exact rows for every possible `NLCD x HSG x burn severity x hydrophobicity` combination, so some persisted HRUs still use explicit estimator fallback.
- Existing legacy Geneva artifacts created before storm-shape runtime dispatch can still show `neh4_type_b` assumptions with uniform-interim hyetograph behavior and should be regenerated before scientific comparison.
- Post-fire CN adjustments are not yet expressed as an explicit Wildcat-style empirical table set.

### 6.3 Culvert strengths

- Explicit `NLCD x HSG -> CN` lookup table is easy to inspect.
- Straightforward screening-scale workflow.
- Familiar TR-55 style runoff and graphical peak-discharge framing.

### 6.4 Culvert shortcomings

- No HRUs; response collapses to one basin CN.
- Much weaker `hydgrpdcd` contract than `us-conus-ssurgo-hydgrpdcd`.
- Mishandles `hydgrpdcd` classes `0`, `5`, `6`, `7`.
- No burn severity adjustment.
- No hydrophobicity / water repellency adjustment.
- Fixed at `Ia/S = 0.20`.
- CN aggregation is not properly area-weighted.
- Weaker contract enforcement and test coverage.

## 7. Scientific Defensibility Rating

### 7.1 Geneva

Rating: `Moderate to Moderately High` (`7.0 to 7.5 / 10`)

Rationale:

- Stronger spatial representation,
- stronger treatment of post-fire controls,
- stronger runoff kernel,
- better match to Wildcat5's modeling philosophy.

Main reasons it is not higher:

- runtime CN mapping is still proxy-based,
- some legacy outputs predate selected storm-shape runtime dispatch and require explicit stale-artifact handling/regeneration before like-for-like comparisons.

### 7.2 Culvert

Rating: `Low to Moderate` (`3.5 to 4.0 / 10`)

Rationale:

- acceptable as a coarse screening workflow,
- explicit lookup table is a positive,
- but the basin-scale collapse, HSG governance issues, and omission of post-fire modifiers make it weak for Geneva's intended post-fire use case.

## 8. Overall Judgment

If the target use case is BAER-style post-fire event runoff modeling, Geneva is the better scientific foundation.

The most important reasons are:

- HRU-based response instead of basin-scale CN collapse,
- explicit invalid/unresolved HSG handling,
- burn severity and hydrophobicity sensitivity,
- support for both standard and reduced initial-abstraction CN variants,
- better alignment with Wildcat5's post-fire guidance.

The most important remaining Geneva follow-on work is:

1. replace or calibrate the current proxy CN estimator with an explicit, documented post-fire CN mapping source,
2. strengthen operator-facing stale-artifact detection/regeneration workflows for legacy uniform-interim outputs,
3. retain the current HRU-based distributed response and diagnostics as non-negotiable strengths.

## 9. Implementation Pointers

Geneva implementation points:

- HRU preparation and HSG handling: `wepppyo3/geneva_core/src/hru.rs`
- CN runoff kernel: `wepppyo3/geneva_core/src/cn.rs`
- storm-shape hyetograph dispatch: `wepppyo3/geneva_core/src/hyetograph.rs`, `wepppyo3/geneva_core/src/storm_shape.rs`
- Python storm orchestration: `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`
- run-scoped CN table lifecycle: `wepppy/nodb/mods/geneva/collaborators/cn_table_service.py`

Culvert implementation points:

- HSG extraction and CN raster generation: `/workdir/Culvert_web_app/culvert_app/utils/subroutine_determine_WS_characteristics.py`
- runoff and graphical peak discharge: `/workdir/Culvert_web_app/culvert_app/utils/subroutine_graphical_peak_discharge_Est.py`

Wildcat5 reference:

- `wepppy/nodb/mods/geneva/resources/Wildcat5/rmrs_gtr334.pdf`
