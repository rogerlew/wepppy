# Independent EROD / RUNGE U5 implementation review

Reviewed hashes:

- EROD: `122f56d173977dbe7acf983b59ca7e93ad90ce0017bb82135be85c43a8350036`
- RUNGE: `35496c2dd96cdd598df25e126ef87dce6609a797bcf0120cfba27b6bfe18f8a0`

## Prior U4 endpoint-closure failure is repaired

The new pre-integration EROZERO check locates the earlier transition rather
than integrating to a zero-capacity endpoint. Independently confirmed the
C=.001-x case now returns x=.000632120646 in about .024 seconds, and the
positive-capacity hump returns an interior transition in about .072 seconds.
Internal starts and all-zero-capacity with interrill supply behave consistently.
All **55 source tests pass independently in 1.17 seconds**.

## P1 — An interior capacity closure followed by reopening hides the first transition

EROZERO returns immediately when capacity at XE is positive. RUNEXP can then
integrate across an earlier capacity closure and a later reopening. The final
load may be below final capacity even though the erosion solution crossed
capacity much earlier; EROD returns NDEP=0 and misses the required first
transition.

Actual source reproduction:

    xb=0, xe=.009, theta=0, load=0,
    capacity=.000016, atc=1, btc=-.01, erodibility=1

C=max(0,(x-.002)*(x-.008)), D=1. Native returns:

    load=6.9445382e-6, DL=.00792264938, XDBEG=-1, NDEP=0

Independent RK4 integration stopped at the FIRST crossing, entirely before
any capacity zero, yields:

    h=1e-8: x=.00007290561019273585
    h=5e-9: x=.00007290560947197596

Thus this is a missed physical event, not merely endpoint integration error.
Retained standalone reproducer: `/tmp/erod-u5-first-transition-probe.py`.
No production prevalence is inferred from this synthetic supported-coefficient
control.

Before eager integration, inspect the earliest capacity-closing boundary in the
prefix even if capacity reopens before XE, and bracket the first transition
there. A terminal-only zero-capacity test is insufficient. Add this failure
family to source regressions and preserve the independent first-crossing oracle.

## Disposition

U5 closes the previous endpoint-closure finding but is not ready for promotion
with the earlier-event loss above. Existing tiny-capacity initial-excess scope
also remains separately unresolved. Shared anchors, interval-bisection progress,
prefix-only source checks and actual-load returns showed no additional concrete
implementation defect in this review. Full physical/particle, native and runtime
gates remain required after correction.
