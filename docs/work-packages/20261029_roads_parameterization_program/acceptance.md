# Success criteria

Status: continuation gates frozen on 2026-10-30 under operator instruction to
continue the recommended program. Numerical thresholds are unchanged.
The operator requested order-of-magnitude reasonableness and delegated experiment
selection. Freeze this document and a machine-readable manifest before candidate
selection. Any later criterion change must be explicit and cannot retroactively
turn a failed validation into a pass.

## 1. Comparable executable baselines

Use the released matched `wepp_261029` pair for the modern treatment and frozen FSWEPP2 Roads/WEPP2010
references. Retain modern-binary legacy-soil controls to distinguish engine effects
from parameterization effects. Hash binaries, source, generated/prepared inputs,
climates, runtime sidecars and native outputs. Confirm actual mode activation.

Compare the same physical outlet, contributing area, geometry, climate period and
road configuration. Distinguish direct road delivery from routed fill/buffer delivery.
Do not compare different contributing areas or OFE roles as if they were equivalent.
Modern runs use actual Roads runtime settings, including `wepp_ui.txt` where the
project enables it. Climate-specific settings must be explicit; do not transplant
site evaporation/snow settings to other climates without justification. Validation
must include actual production builders and full-project execution, not only a
hand-assembled three-OFE surrogate.

Paved/gravel, traffic and ditch distinctions must reach the emitted inputs according
to their supported semantics. Report actual input aliases and unique soil signatures;
labels and duplicated MUKEY material do not create independent evidence.

## 2. Order-of-magnitude agreement

Frozen practical gate: at least **95%** of meaningful-load comparisons lie in
**0.1–10 times** the FSWEPP2 annual sediment export, and at least **90%** pass within
each declared climate, design/routing, surface, traffic and soil/restriction group.
Apply these gates separately to the development confirmation and genuinely withheld
validation panels; count soil material groups with equal weight and report raw counts.
Report all intersections and worst cases even where their sample size is small.
No hidden material stratum can be excused by the overall mean.

Frozen small-load convention for the frozen benchmark geometries: a reference
above **1 kg/year** uses the ratio gate. A reference at or below 1 kg/year has no
ratio lower-bound requirement and must have candidate export no greater than
`max(1 kg/year, 10 * reference)`. This is an explicitly chosen engineering tolerance,
not a measurement detection limit or epsilon division. Report exact zero references,
raw positive ratios and absolute differences separately, including the small-load
cases excluded from the ratio denominator. Apply the same 95%/90% success requirements
to this group where populated. If changing geometry scales, declare an area-aware
small-load convention before execution; do not reuse 1 kg blindly across sizes.

Every remaining failure must be identified, bounded and explained. A failure that
indicates broken configuration semantics, systematic missing physics, invalid output
or a runtime mismatch is a hard blocker even if the percentage gates pass. A candidate
must not trade excessive sediment for systematic severe underprediction. Report
signed log-ratio bias and reductions/increases by stratum, not only pass fractions.

## 3. Physical and numerical validity

No negative sediment boundary flux, nonfinite values, failed native execution,
missing climate dates or unexplained water/sediment accounting discrepancy may be
accepted in the release validation panel. Native source-supported differences in
report definitions may be reconciled explicitly; do not widen precision tolerances,
clip negative values or call an unexplained mismatch a pass.

Preserve the normalized 200 mm boundary. Use generated material profiles and
source-informed restrictive-layer classes. Distinguish mineral restrictions,
lithic/other geological restrictions and missing restriction information. Do not
use climate-, MUKEY- or case-specific output correction factors, replace generated
soils with legacy templates and call that modern-soil success, or choose bedrock
conductivity solely to make sediment match.

Document parameter meanings, units, supporting ranges and expected directional
responses. Verify hydrology, saturation, deep/lateral flow partition and erosion
budgets. A lower sediment number alone does not prove physical improvement.
Compatibility with FSWEPP2 is not field calibration; user-facing documentation must
say what has actually been validated.

## 4. Generalization and search integrity

Prior runs and their outcomes are development evidence, including the old specimen
named `holdout`. Select additional semantically distinct generated profiles and
withheld climate/geometry combinations before fitting. Inspect metadata for sampling,
but do not use their native outputs to pick the winner. Freeze explicit split IDs,
runtime bundles and stratification in the manifest. Use at least the existing five
climates, all four road designs, both surfaces, all three traffic levels, multiple
soil/restriction classes and geometry/routing stress cases.

Keep a complete candidate ledger: parameter values/rules, rationale, hashes, batch
membership, diagnostics, failures and selection decisions. Screening may be adaptive;
the final panel is evaluated after the selected parameterization is frozen. If it
fails and its outcomes inform a revision, it becomes development data; establish a
new withheld panel rather than repeatedly calling it independent validation.

## 5. User-facing parameterization view

After the scientific gate passes, provide a Roads configuration view with relevant
editable parameters, units, validated ranges, default/override status and reset.
A normal user must not need to edit CSV or native files. Configuration selection
must make applicability clear: road versus fill/buffer, surface, traffic and ditch
or routing distinctions as supported by the selected model.

Save, reload, fork and restore must preserve effective choices. Invalid values fail
atomically without partially changing a project. Editing/reset must mark affected
Roads outputs stale and regenerate the correct inputs on the next run. Verify the
full chain: browser -> request -> saved state -> prepared WEPP inputs -> native
execution -> regenerated Roads report. Display custom status; custom values are not
automatically described as benchmark-validated.

Version the accepted parameter set and retain provenance in run artifacts. Existing
projects remain reproducible; global soil/Disturbed behavior remains unchanged.
Finalize exact field schema, permissions and migration behavior in canonical
contracts and the ADR before implementation. Exercise authorized, readonly, missing,
legacy, empty, invalid and hostile states through real boundaries.

## Completion claim

The program is complete only when the accepted modern parameterization and the
user-facing view are implemented, wired and validated with actual artifacts, tests,
review and documentation. If no candidate meets the gates, report the limiting
physics/model issue and continue justified investigation; do not lower the gates or
ship a tuning interface as if an accepted default had been established.


## Human gate for configuration specification and layout

Operator instruction, 2026-10-30: continue the recommended scientific program
with broad authority to use forest, up to a human review of the UI configuration
specification and layout. Prepare concrete fields, units, ranges, applicability,
version/adoption/reset behavior and a static layout proposal. Human approval of
both specification and layout is required before implementing the configuration
view or its production persistence/application wiring. Scientific experiments,
disposable builder/full-project validation and reviewable design documents remain
authorized. Do not treat silence, scientific acceptance or AI review as UI approval.
