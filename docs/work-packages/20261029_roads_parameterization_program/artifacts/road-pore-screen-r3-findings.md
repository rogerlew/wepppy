# Road pore/conductivity sensitivity: results

The bounded road-only screen identifies a conductivity response but does not
establish an acceptable generated-soil parameterization. All 348 new runs pass
physical checks; all 20 passing controls remain within magnitude bounds in each
lane. The baseline remains the frozen 840-case candidate, not a new matrix score.

| Incremental treatment | Meaningful high recovered /5 | Meaningful low recovered /48 | Small excess recovered /43 | Total recovered /96 | Passing controls /20 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pore/retention | 0 | 1 | 0 | 1 | 20 |
| Conductivity ÷2.4 | 2 | 21 | 1 | 24 | 20 |
| Coupled | 2 | 22 | 1 | 25 | 20 |

Coupled treatment gains only one case over conductivity alone (site, 2711184,
outunrut, gravel/no traffic), losing none. This offers little numerical support
for promoting the extra pore/retention assumption. Do not reinterpret the
conductivity-only result as a calibrated multiplier: the experiment starts from
an already capped road and field transfer remains unvalidated. The coefficients
were frozen before execution and were not tuned against these results.

## Artifact verification

The verifier rehashes every declared input and output, checks unchanged fill/buffer
and deeper horizons, independently checks the changed density/FC/WP/K fields,
reparses LOSS and recomputes physical audits for all 348 runs. Seven coupled cases
(one per development material, selected before scoring) are replayed with the
observation binary and must exactly match their released-binary raw outputs.
Their SCON and completed WATBAL initialization states are paired with the earlier
14 generated/legacy observation replays. Fill/buffer initialization remains exact.
See [verification](road-pore-screen-r3-verification.json).

## Remaining discrepancy and next diagnostic

There are still 42 small-reference excesses. All 42 have positive annual net fill
exchange and negative annual net buffer exchange; 15 have zero road sediment at
the first boundary. Net exchange is not source tagging: a net-depositing buffer
can generate sediment on individual days. These observations motivate separating
fill generation from buffer delivery, not assigning all exported particles to fill.
See [retained residuals](road-pore-screen-r3-residuals.json).

Neither road treatment can meet the unchanged small-reference gate on the full
matrix because these known failures already exceed its allowance. A new 840-case
sweep of these standalone treatments would not establish acceptance. Retain the
conductivity response as a component hypothesis and resolve downstream role
behavior before spending the broader validation budget.

Next is an initialization-verified same-format legacy bridge, followed by
controlled fill/buffer role substitution. First require exact full-period output
and initialization equivalence between each original legacy deck and its bridge;
do not splice 98.4 role blocks into 9002 or assume syntactic conversion preserves
state. The bridge is diagnostic and may not replace generated materials in a
candidate. If equivalence fails, trace the source branch causing the difference
before interpreting any mixed-role run. Freeze the role panel only after that gate.
[Next experiment specification](role-isolation-r3-plan.md).

No production default, soil writer, native release, withheld outcome or UI change.
The earlier full development score remains 713/766 meaningful and 31/74 small.
The research rule and limitations are recorded durably in
[ADR-0120](../../../adrs/ADR-0120-roads-generated-hydraulic-sensitivity.md).
