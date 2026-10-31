# Next diagnostic: initialize equivalent legacy roles before substitution

Status: designed, not executed. No production or UI parameterization decision.

## Purpose

Whole legacy soils recover 79/96 generated misses, but road-only conductivity
sensitivity recovers 24 and the coupled road treatment 25. Forty-two small-load
misses remain, with positive annual net fill exchange and negative net buffer
exchange. Separate fill generation and buffer delivery without confusing file
format with role treatment. Annual net exchange alone is not causal attribution.

## Equivalence gate

1. Freeze the existing 116-case generated/legacy panel and current revision-3
   hourly/PMET/snow settings. Retain the original generated baseline; do not add
   the new road conductivity multiplier while establishing role causality.
2. Trace legacy missing-field estimation, `avke`, effective density/retention,
   profile remapping/depth, horizontal conductivity/anisotropy, initial saturation,
   frost flag and restriction defaults. The audit observations provide actual
   SCON and completed initialization values, not values to paste indiscriminately
   into input columns that would then be corrected a second time.
3. Build a study-only whole-deck representation in the compatible modern syntax.
   Explicit missing-value sentinels, if required for native equivalence, belong
   only in this diagnostic generator; do not relax production soil-writer validation.
   Record every mapping and distinguish native-effective K from saturated K.
4. Require identical consumed non-soil inputs, identical full-period raw output
   inventories/bytes, and matching initialized states for the legacy source and
   bridge. Include all distinct legacy input decks in this frozen panel, with
   aliases reported. Do not proceed to role substitutions on failed equivalence.
   Investigate actual native format branches if no equivalent representation exists.

## Conditional role panel

After equivalence, predeclare generated road + bridged fill, generated road +
bridged buffer, and generated road + both bridged downstream roles on the same
96 misses/20 controls. All non-target role records and runtime inputs remain
fixed. Full legacy and full generated endpoints are retained controls. Validate
emitted blocks, initialized native states, all output boundaries and physical
checks before scoring. Record effects on low/high/small groups and controls.

The result is causal diagnostic evidence about whole-role soil treatment, not a
physical candidate or justification for copying legacy profiles into production.
Depth, retention, K and material differ together within a substituted role; split
those factors only where the role experiment warrants it and source evidence
supports the narrower contrast. Failed or zero-sediment runs are never silently
counted as magnitude successes. Preserve withheld materials and the human
specification/layout gate. Full development, geometry and regional-runtime
validation remain necessary for any eventual physically justified candidate.
