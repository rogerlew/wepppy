# Roughness counterfactual: upstream coupling localization

Status: predeclaration for independent review; no localization binary or runs.
The original [persistence counterfactual](buffer-roughness-counterfactual-r4-plan.md)
and its upstream-isolation criterion remain unchanged. Attempt `u1b` failed
that criterion after four completed full-period runs; the remaining 32 runs
have not executed. No counterfactual parameter is accepted.

## Trigger and bounded question

The modern B1 off/on pair has exact density, porosity, density-driver and upstream
RRC/RH trajectories, but its upstream outputs differ. The first reported change
is simulation year 4, day 233: road peak runoff changes from 942.874 to
113.080 mm/h and effective duration from 0.051 to 0.426 hours. Fill sediment
changes from 0.441 to 0.648 kg/m. Upstream water volumes first differ on day 243,
the next reported runoff event. Raw residue differences begin later. These are
an exact isolation failure; they cannot be dismissed as printing error.

Source inspection identifies an existing candidate explanation: IRS assigns a
connected routing group's final duration and peaks back to upstream OFEs;
XINFLO/PARAM/SHEARS changes their persistent rill width. At the next storm,
FRCFAC reads that width, RDAT derives the flow coefficient, and QINF uses it for
recession infiltration. This is a source-supported path, not yet a quantitative
reconstruction of the first changed events and not a newly established defect.

Observe those actual producers to distinguish native routing feedback from an
unintended intervention. Do not modify the routing law, freeze upstream state,
change a parameter, or retroactively pass the rejected experiment.

## Frozen inputs and four replays

Use only the already selected B1 modern case, in both original modes (`O4` off,
`U1` retained initial buffer RRC). Reuse the exact full 16-year core and auxiliary
decks, the same guarded roughness rule and all original full-period state
observations. Two bounded observer selectors cover:

- Target year 4/day 234, observing days 233–234: first changed peak/width and
  the following day's state.
- Target year 4/day 244, observing days 243–244: next runoff event and first
  observed upstream residue difference.

This gives four full-period native executions. Each must reproduce all seven
ordinary output files byte-for-byte against its corresponding retained `u1b`
mode. The date selectors affect diagnostics only. No new soil, climate,
management value, treatment value, reference target or held-out case is used.

First run the two modes for the first window; continue to the second window
only after both parity/runtime/accounting/coverage checks pass. Retain failures;
never overwrite an attempted run or relax an accounting threshold.

## Minimal additional observations

Retain the original O3/U1 observations and distinguish their owning phases.
The private exact map and patch must be independently reviewed before build.

| Producer | Required observations and purpose |
| --- | --- |
| IRS connected-group finalization | Current OFE, group start, terminal plane; actual duration, peak, runoff and effective length immediately before and after each upstream assignment. Reconstruct the assignment using its native REAL operation order and unchanged geometry. |
| SHEARS width update | Owning OFE, width-control branch and assigned discharge; initialized incoming width and actual computed outgoing width. Establish whether the first changed peak produces a persistent width change. |
| FRCFAC | Actual consumed width/spacing and assigned equivalent friction factor. Preserve distinct hydrology and sediment-phase calls. |
| RDAT | Actual assigned flow coefficient and its valid friction/slope operands. |
| IRS around QINF | Actual receiving plane, incoming runoff, flow coefficient, effective length, conductivity, duration/terminal infiltration operands and returned runoff. |

Read a local only after its producing assignment or under its exact valid-state
guard. Do not add uninitialized or stale values merely to fill a trace field.
Use original assigned variables and observer-only state; preserve all native
source lines, model arithmetic, loop boundaries, and control conditions.

The full-period density/porosity/driver invariants remain exact. For each mode,
its full-period roughness-state trace must also match the corresponding `u1b`
trace, apart from an explicitly declared diagnostic-only field if required.
The upstream-output invariant is **not** applied between modes in this
localization dataset: that already retained failure is the object of study.
Within-mode byte parity to `u1b` is mandatory.

## Readback and stop rule

Freeze source/includes/objects, calendar sibling, compiler and libraries,
observer patch/map, runner and dependency closure before execution. Bind the
failed-attempt records, inputs, ordinary outputs and original rule. Require
native completion, exact inventories, canonical physical audits and unchanged
strict particle audits. Require complete paired before/after marker coverage,
valid producer ownership, and post-run byte readback.

Assess only whether the executed assignments and observed native operands
explain the first peak/width change and the next-storm hydraulic response.
Reconstruct exact REAL expressions where the observed operands suffice;
otherwise identify the unresolved link. Residue changes remain a downstream
association unless the existing observations independently establish their
producer; this study does not add every decomposition equation.

No annual magnitude or parameter-promotion conclusion follows from this four-run
localization. No new model defect is inferred from the mere existence of native
nonlocal coupling. A subsequent campaign that permits that coupling requires an
explicit reviewed addendum and fresh declaration. It cannot relabel `u1b` as a
passed isolated experiment.
