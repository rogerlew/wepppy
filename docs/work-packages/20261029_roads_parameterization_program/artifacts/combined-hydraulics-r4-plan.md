# Revision-4 generated-soil hydraulic factorial

Status: declared before execution; research only. Execute after revision-4 native acceptance and focused application delivery
gates (provenance, host/container smokes and actual selected hill/PASS/watershed/
reader workflow). The full application suite may run concurrently and remains
a required release handoff gate. This continues ADR-0120 with its existing values,
not a parameter search or a production rule.

## Question and design

Can the already declared road pore/conductivity treatment and downstream
conductivity treatments complement one another without losing passing controls?
The repaired native engine is fixed at artifact revision 4. Reuse the original
116-case diagnostic panel (96 magnitude misses and 20 passing controls), original
climates/periods, FSWEPP2 reference values and generated soil format.

Use a complete 2 x 2 x 2 factorial: road coupled treatment off/on, fill adjustment
original/fixed, and buffer conductivity original/capped. Reuse 464 exact-U12
cells already generated and verified (116 baseline plus 348 downstream cells),
rehashing their input/output bytes and rechecking physical audits. Execute the
remaining 464 cells, with the road treatment enabled and all four downstream
combinations. Do not substitute outputs from revision 3.

The road treatment is exactly ADR-0120: subtract 0.02 pore fraction using its
native-clamped density, scale retention with its fixed normalized-shape rule,
and divide existing capped road conductivity by 2.4, only through the explicit
200 mm horizon break. Fill changes only `ksatadj` from 1 to 0. Buffer caps only
active upper-200-mm conductivity at the original configuration-matched legacy
buffer `avke`. These are declared diagnostic priors with unresolved transfer
limitations, especially on paved surfaces. No coefficients vary by climate,
case outcome, or failure group. No further conditioning or legacy role copying.

## Compatibility and validation

No production schema, defaults, soil writer, native executable or runtime option
changes. New run directories and additive research JSON use the existing parser
and accounting helpers. Every non-soil input remains byte-identical; only the
union of the previously declared soil fields may change. Reparse the generated
soil, verify unchanged deeper horizons and role fields, and retain original
inputs. Hash declarations, helper dependencies, binaries, inputs and outputs.
Require complete native periods, finite/nonnegative fluxes, output accounting,
and full EVENT particle/bulk checks. Keep strict fraction flags visible; reuse
an existing arithmetic certificate only if its exact applicability is verified.
New unexplained discrepancies block candidate acceptance.

Report all eight cells for every case, misses recovered, control regressions,
physical failures, meaningful/small-reference counts and every climate/material/
configuration stratum. The panel is selected for diagnosis, so even a perfect
screen does not establish the frozen 95%/90% broad success requirements.
Every combination considered for broad confirmation must retain all 20 originally
passing controls. Reject any recommendation with a control regression. If combinations
improve coverage, select a physically interpretable candidate for fresh 840-case
confirmation and broader geometry/runtime tests before any withheld validation.
If small-load failures persist, trace road/fill/buffer source contribution rather
than fitting a sediment multiplier. Six withheld materials remain untouched.

The UI specification/layout still requires human approval before implementation.

## Paired contrasts and acceptance status

For every case retain all eight cell values and every first-, second- and
third-order finite difference at each background factor configuration. Report
absolute annual sediment, runoff depth, and road/fill/buffer sediment boundary
and net boundary exchange, plus surface/lateral water outflow and deep percolation.
The differences retain their native units; interaction signs describe response,
not causal proof of the assumptions. The road factor is a coupled package and
cannot identify pore versus conductivity causality. Include all five individual
strata and all case intersections, positive meaningful-reference signed log-ratio
bias, and zero-export meaningful cases separately.

Existing `physical_pass` and `within` fields retain their narrow historical audit
semantics. Reports explicitly label reviewed physical acceptance as pending;
particle flags never disappear inside a magnitude pass count. No combination
advances until every strict flag has exact accepted-certificate applicability or
a new reviewed explanation. Parameter transfer remains unaccepted even when all
computational checks pass. These clarifications were made before any new run.

Effective transitive audit/parser Python files, owned soil/interchange modules,
installed native-reader package bytes and the resolved climate-calendar manifest
are hashed and checked at execution. Net OFE boundary exchange is bookkeeping,
not tagged sediment provenance. The shallow trafficked-forest rationale does not
validate uniform treatment through 200 mm, paved roads or buffer avke-to-Ksat
transfer. Those remain physical hypotheses requiring later justification.

## Execution scheduling clarification

Before execution, the focused delivery checks and independent installed-byte,
workflow, scientific-design and complete-deck reviews all passed. The full
application suite is running its large existing soil-preparation matrix. Direct
native diagnostic executions are independent of those tests, use separate run
folders and cannot promote a release or parameter candidate. Permit concurrent
execution without waiving, truncating or counting the unfinished suite as passed.
This changes scheduling only; input decks, factors and scientific criteria are
unchanged. Retain the preceding declaration and this amendment before execution.
