# Signed channel coupling review and controls

Independent scientific/correctness review, 2026-10-21. Native paths refer to
`/workdir/wepp-forest-release-20261009`. Tests use the isolated corrected
`mc-interface-candidate-v2` WSHCHR, actual WSHCQI and native MC4/5. No production
source was changed for this review.

## Scoped promotion and package status

**Support promotion of the independently validated publication and source
corrections, conditional on final gates and the separate threshold/cascade
review.** The corrected candidate removes the first-call baseflow double count,
excludes positive side-impoundment transfer from the new local-source condition,
and publishes/transfers the accepted outlet integral without inventing a
residual storage. The retained baseflow continuation evidence supports those
changes. They preserve the MC recurrence and its storage authority.

**Do not close the full routing package.** The controls below demonstrate
unresolved signed-source/soil coupling even with fixed positive coefficients.
They also separate it from negative-flow behavior present without a withdrawal.
Neither changing a report nor scalar source normalization repairs both paths.

## The generating contract matters

WSHDRV computes channel runoff after WATBAL, then defines
`rtrans=rvolon+chnvol-runvol` (`src/wshdrv.for:1012`, also `:1043`). WSHCHR
defines its lateral net amount as `rvolat+chnvol-rtrans` (`src/wshchr.for:151`).
Because `rvolon=rvolat+rvotop`, these imply:

```text
lateral_net = pre-routing_runvol - rvotop
declared_total_net = pre-routing_runvol
```

A negative lateral amount can therefore be a valid daily subtraction from top
runon while total daily runoff remains nonnegative. It is not, by itself, proof
of excess total withdrawal. An arbitrary control with negative total daily net
input does not represent this ordinary producer path.

WATBAL has already incorporated `roffon-runoff` into infiltration at
`src/watbal.for:353` or `src/watbal_hourly.for:359`. The hourly channel path
divides this daily fin over its water-balance steps (`:479`). Changing rtrans
later without reconciling that soil calculation can leave water both in the
soil accounting and in the routed export. A final scalar correction is not a
coupled repair.

## Retained controlled experiment

Full receipts, raw records, binaries and source hashes are retained at:

```text
/workdir/watershed-physical-water-repair-20261021/reviewer-signed-loss-v3/
/workdir/watershed-physical-water-repair-20261021/reviewer_signed_loss_probe.py
```

The compact repository receipt is
[signed-coupling-control-summary.json](signed-coupling-control-summary.json).
It includes the full receipt's hash. The retained diagnostic script builds
separate observer-on/off variants; all 24 controls preserve identical exported
hydrographs, publication, transfer volume and geometric diagnostic with the
observer enabled. No recurrence coefficient or clipping rule is modified.

Each run has a dry establishment day, a pulse day and a recession day. The
upstream channel supplies a 100 m³ top hydrograph early or late on the pulse day;
its endpoints are zero. Daily post-soil runoff is prescribed as either 100 m³
(zero-loss control) or 50 m³. The driver applies the actual WSHDRV identity to
derive rtrans. **WATBAL is not executed:** this establishes producer-consistent
coupling inputs, not a full soil-state regression.

The matrix covers MC4/5, both lateral modes, early/late input, and zero/50 m³
loss on the native grid. Additional MC4 controls freeze eight cells and the
reference discharge at 0.5 m³/s. Those fixed controls have K=1262.18054 s,
X=0.230734825 and positive recurrence coefficients, with minimum coefficient
0.0069011254. They isolate signed forcing from negative coefficient artifacts,
coefficient revaluation and regridding.

Observers retain every raw spatial/time node, every executed recurrence and
its coefficients, initial/final profiles, actual source quadrature, exported
rates and publication. Omitted recurrence intervals are explicit. Requested
but skipped forcing is separated from the much smaller lateral division/spatial
rounding term. Summed MC increments, within-day coefficient revaluation and
daily grid/coefficient jumps are retained rather than imposing geometric closure.

## Findings established by the controls

### High: fixed positive-coefficient routing does not reconcile a daily soil loss

Three-day totals for fixed MC4 are:

| Lateral mode / pulse | Requested loss | Loss omitted in skipped intervals | Raw outlet integral | Accepted outlet integral | Export minus raw clipping |
| --- | ---: | ---: | ---: | ---: | ---: |
| Point / early, zero-loss control | 0 m³ | 0 m³ | 99.999916 m³ | 99.999905 m³ | -0.000011 m³ |
| Point / early | 50 m³ | 0 m³ | 49.999958 m³ | 91.519098 m³ | +41.519140 m³ |
| Point / late | 50 m³ | 47.395834 m³ | 97.395750 m³ | 98.214077 m³ | +0.818328 m³ |
| Cell / early | 50 m³ | 0 m³ | 49.999952 m³ | 91.438337 m³ | +41.438385 m³ |
| Cell / late | 50 m³ | 47.569445 m³ | 97.569363 m³ | 98.367059 m³ | +0.797695 m³ |

The late zero-loss control matches the early zero-loss totals. Final algebraic
coordinates are negligible in these fixed controls; C and J are zero. The
regular recurrence residual is about 0.00004–0.00008 m³, far below the signed
coupling discrepancies. These observations do not depend on geometric storage.

The early loss is applied throughout the day, including after the pulse. Raw
negative outlet flow makes its signed integral approach 50 m³, but clipping
removes that negative export and the accepted outlet is approximately 91.5 m³.
The late case skips 137 pulse-day intervals before arrival because boundaries
and retained state are dry, despite a negative requested lateral source.
Only the remaining portion of the requested loss enters executed updates.

This is a real accepted-transfer/withdrawal mismatch for a daily amount already
assigned to the soil side of the contract. Executing the omitted negative
forcing unconditionally would create a negative raw state before water arrives;
it would not establish an availability-safe repair. Removing clipping would
export negative flow and change the existing method. Neither is recommended.

### Medium: clipping also exists without a signed loss

Native MC5 zero-loss controls have nonzero negative raw outlet/clipping:
approximately +1.964191 m³ for the early pulse and +0.759600 m³ for the late
pulse over the retained three days. Variable coefficients and transitions
require the C/J ledger; their outlet totals must not be interpreted by subtracting
only geometric or endpoint storage. In these controls the executed recurrence
still agrees with the independently calculated MC increment within native
arithmetic.

Consequently, signed forcing cannot explain every raw-negative or clipped
outlet in full-period runs. Pair zero-loss and signed-loss controls before
attributing a clipping discrepancy to withdrawals. A generic prohibition on
negative algebraic H would also contradict the operator's selected MC contract.

The complete observed identity, including skipped forcing and spatial rounding,
closes within 3.6e-14 m³ in the independent binary64 post-processing. This checks
the decomposition, not physical correctness or an acceptance tolerance for the
native solver. The native regular-step arithmetic residual remains separately
reported.

## Minimum next step within the current authority

Keep the validated interface promotion separate from signed-coupling closure.
Retain a validation ledger that compares daily soil-side exchange, requested
per-step source, executed source, skipped source, raw/export clipping and accepted
downstream transfer. A case with an unexplained mismatch must fail the **repair's
acceptance gate**, with the date/channel/component exposed. Do not introduce a
blanket runtime failure based merely on negative X, H or raw Q: zero-loss MC
controls demonstrate why those are insufficient diagnoses.

The adaptive MC4 late zero-loss control exposes another distinct boundary:
day two ends with 58 cells and a positive interior discharge profile; day three
regrids to 101 cells and retains positive interior discharge, but its zero
reference coefficient gives K=0 and a combined coordinate jump of about
-99.999982 m³. Export remains zero over the retained three days. This is not
observed deletion of that profile and must not be attributed to signed loss;
coefficient selection/propagation needs a separate analysis. The fixed-grid,
positive-coefficient comparisons above avoid this confounder.

Next, execute an actual WATBAL→WSHDRV→WSHCHR control using the same early/late
hydrographs and channel soil. Observe the pre/post soil stores, infiltration,
Dp, lateral release and ET, then reconcile the generated rtrans with the signed
forcing and accepted outlet. The current prescribed-soil controls already
prove the interface limitation; this additional test identifies which real soil
state must be reconciled and prevents an incorrect late-stage correction.

No further model-state authority or solver change is needed for these
observations, control reproduction, acceptance diagnostics, or promotion of the
independent omission/publication fixes. Do not represent those steps as a
completed signed-loss repair.

## Bounded repair design requiring an explicit coupling contract

A complete repair can retain the MC recurrence, but it must make **accepted
channel withdrawal and soil-side credit the same transaction**. The smallest
design boundary is the channel source/sink interface among WATBAL, WSHDRV and
WSHCHR, not replacement of MC or adoption of geometric-volume authority.

The contract must define a desired exchange, an accepted amount and an unmet
amount, with the segment/time of acceptance. If acceptance differs from the
daily amount used by WATBAL, the soil calculation must be committed or replayed
from its pre-exchange state using the accepted exchange. Simply subtracting an
amount from final soil storage is insufficient: percolation, ET, return flow and
the hourly allocation sequence may already have changed. A preview/replay
prototype must demonstrate deterministic restoration and matching coupled
budgets before choosing that implementation.

Availability cannot be defined by silently calling H a nonnegative liquid store.
Nor does `q_out>=0` alone measure physical availability. For an individual
regular cell, an output-positivity bound can be derived from the no-withdrawal
update and the lateral coefficient; that is a numerical admissibility test,
not an independent water inventory. It can fail even without a withdrawal when
the original coefficients produce an undershoot. Any use of it must retain that
distinction and leave the zero-loss method behavior explicit.

Proportionally scheduling the daily loss against the channel's top hydrograph
does not by itself protect lower segments before the wave reaches them. A
per-segment limiter changes the accepted amount and therefore requires the soil
reconciliation above. Moving all absorption to the inlet, deferring a loss to
another day, changing the source's temporal/spatial distribution, or adding an
independent physical storage all select additional hydrologic behavior. They
must be evaluated as explicit coupling choices, not hidden in a scalar
normalization or called a proven arithmetic correction.

The concrete next design is therefore a **limited coupled exchange prototype**
on the retained single-channel early/late controls: preserve MC and existing
storage meaning; expose desired/accepted/unmet exchange; choose and document
the temporal/spatial acceptance rule; commit the same accepted exchange to soil;
then test daily/hourly soil and both MC methods before extending to cascades.
The operator's existing authorization permits the diagnosis and interface fixes;
it does not supply an unstated availability definition or authorize a new
physical-storage model. Record the selected coupling behavior in ADR-0101 before
promotion. Until that contract is settled and tested, the scientifically safe
disposition is explicit incomplete signed-coupling acceptance, not a claim of
robust watershed closure.
