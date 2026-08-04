# Forest and Post-Fire Evapotranspiration Model Options

## Decision Context

The existing Penman-Monteith implementation uses an agricultural dual crop
coefficient partition:

    K_Ep = Kcb_adjusted * (1 - exp(-0.45 * LAI))
    K_Es = Kcb_adjusted * exp(-0.45 * LAI)

Before water stress and residue limitations, the two coefficients sum to the
adjusted basal crop coefficient. Reducing forest LAI therefore transfers most
potential canopy demand into potential soil-evaporation demand. It does not
represent the physically expected disappearance of a large portion of total ET
after canopy loss.

The 924-run `kcb`/`rawp` calibration empirically rejects those two parameters as
sufficient controls. Low severity only approaches both targets at the lower
`kcb` boundary; moderate severity retains excessive total ET; and high severity
retains excessive `Es/ET` over the entire grid. `rawp` is weakly identifiable
because it changes plant water-stress timing but does not directly control the
soil-evaporation coefficient.

## Required Behavior

A replacement or extension should be able to express all of the following
without obtaining one target through a compensating error:

- canopy loss materially reduces total ET;
- absolute soil evaporation can increase after fire;
- lost plant-side ET is not automatically reassigned to soil evaporation;
- soil evaporation is pulse-responsive after rain or melt and then becomes
  moisture-limited;
- litter, residue, exposed mineral soil, and shallow water availability affect
  soil evaporation;
- low-, moderate-, and high-severity behavior can be represented without
  changing agricultural calibration;
- recovery through time can eventually be represented explicitly.

## Option 1: Decouple Soil Evaporation from `kcb`

Retain the current plant-side coefficient but calculate soil demand from an
independent coefficient:

    K_Ep = Kcb_adjusted * f_canopy(LAI)
    K_Es = Ksoil * f_exposure(LAI, residue, litter)

`Ksoil` would set maximum exposed-soil demand, while the exposure function
would describe how canopy and forest-floor cover attenuate it. Lost canopy
demand would no longer be forced into `Es`.

Advantages:

- directly addresses the demonstrated failure mechanism;
- small enough for an isolated experimental implementation;
- preserves most existing PMET and water-stress machinery;
- allows separate calibration of total plant demand and soil exposure.

Risks:

- `Ksoil` can become another empirical knob unless tied to measurable cover or
  resistance;
- a static coefficient may not reproduce wetting pulses and dry-down;
- management data must distinguish canopy, litter, and mineral-soil exposure.

Disposition: **recommended first experiment**.

## Option 2: Forest-Specific PMET Partition Mode

Add a management-selected forest mode while retaining the agricultural
partition for crops. Undisturbed forest, burned forest, and possibly shrub or
grass would use explicitly named partition contracts.

Advantages:

- prevents a forest correction from changing established crop behavior;
- provides a clean place for fire severity and recovery state;
- makes model intent visible instead of embedding forest behavior in crop
  coefficients.

Risks:

- introduces configuration and compatibility decisions;
- requires an explicit mapping from management classes to ET modes;
- duplicates some logic unless the shared PMET calculations are factored
  carefully.

Disposition: **recommended production architecture if Option 1 succeeds**.

## Option 3: Bounded Post-Fire Soil-Exposure Scalar

Apply a fire-specific scalar to the current soil coefficient:

    K_Es_fire = Sfire * Kcb_adjusted * exp(-0.45 * LAI)

An initial experimental range might be `0.45-0.80` for low severity,
`0.30-0.65` for moderate severity, and `0.20-0.50` for high severity. These are
sensitivity ranges, not proposed defaults.

Advantages:

- minimal source change;
- quickly tests whether limiting reassignment can recover the target matrix;
- useful as a benchmark for more physical alternatives.

Risks:

- soil demand remains derived from a canopy crop coefficient;
- the scalar has weak physical meaning;
- a fitted severity table may not transfer among climates, soils, or recovery
  stages.

Disposition: **useful diagnostic or transitional option, not preferred final
formulation**.

## Option 4: Explicit Forest-Floor Resistance

Calculate soil evaporation using exposed mineral-soil fraction, litter or
residue mass, shallow soil water, time since wetting, and aerodynamic or vapor
resistance. Fire would change those state variables rather than merely select a
larger soil coefficient.

Advantages:

- represents rapid evaporation after wetting followed by moisture-limited
  dry-down;
- connects parameters to observable forest-floor properties;
- can represent litter recovery separately from canopy recovery.

Risks:

- requires inputs that may not currently exist in WEPP managements;
- needs event-scale soil-evaporation observations for calibration;
- adds state and potentially interacts with residue and infiltration logic.

Disposition: **preferred physical refinement after a decoupling prototype**.

## Option 5: Two-Source Energy-Balance Model

Replace the coefficient partition with separate canopy and soil energy-balance
paths, such as a two-source Penman-Monteith or Shuttleworth-Wallace formulation.
Canopy and soil fluxes would use separate surface and aerodynamic resistances.

Advantages:

- strongest physical separation of canopy and soil processes;
- naturally allows canopy loss to reduce total ET without transferring all
  demand to soil;
- offers a coherent foundation for forest recovery.

Risks:

- largest implementation and validation burden;
- requires more meteorological, canopy, and resistance inputs;
- could create false precision if the required inputs are inferred poorly.

Disposition: **long-term option if simpler decoupling cannot meet independent
validation targets**.

## Option 6: Empirical Forest Water-Balance Benchmark

Fit seasonal or monthly plant-side and soil-evaporation controls directly to
forest observations or remote-sensing ET. Use the result as a benchmark against
which process formulations are evaluated.

Advantages:

- establishes whether the target budgets are attainable under the existing
  water supply;
- provides a simple independent comparison for process-model development;
- can expose seasonal bias hidden by annual totals.

Risks:

- weak process transferability;
- remote-sensing total ET does not directly identify `Ep` and `Es`;
- site-specific fits may not generalize across forest types or climates.

Disposition: **recommended validation benchmark, not the sole production
model**.

## Required Preliminary Checks

Before selecting or calibrating a new formulation:

1. Test the suspected `wftrp = wfevp + ...` root-zone accumulator assignment in
   `evappm.for`. A defect there could distort plant stress and apparent `rawp`
   sensitivity.
2. Instrument daily reference ET, `kcbadj`, `kcbcon`, `etke`, residue
   attenuation, shallow water limitation, root-zone extraction, `Ep`, and `Es`.
3. Confirm annual and daily water-balance closure at output precision.
4. Preserve the existing agricultural path as the comparison control.

## Recommended Sequence

1. Resolve the root-zone accumulator question with a focused source test.
2. Implement an experimental forest-only decoupled `Ksoil` or exposure scalar.
3. Calibrate plant demand, soil exposure, and water stress against the existing
   ET-ratio and `Es/ET` matrix, without using runoff in the objective.
4. Require credible wetting-pulse and dry-down behavior in addition to annual
   agreement.
5. Promote the experiment to an explicit forest PMET mode only after external
   validation.
6. Advance to explicit forest-floor resistance or a two-source formulation if
   the decoupled prototype remains structurally inadequate.

## Governance and Change Boundary

These options are research alternatives, not approved parameter defaults.
Changing a production formula, threshold, default, or management-to-mode
mapping requires an ADR under the repository parameterization standard. A
production change must also document compatibility with agricultural runs,
generate current-binary output evidence, and retain a rollback path.

## Related Evidence

- [PMET calibration results](pmet-calibration-results.md)
- [Post-fire annual ET targets](et-calibration-targets.md)
- [Soil-evaporation code trace](soil-evaporation-code-trace.md)
- [Area-weighted water-balance attribution](water-balance-attribution.md)
