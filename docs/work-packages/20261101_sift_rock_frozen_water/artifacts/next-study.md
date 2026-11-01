# Recommended next decision: reconcile water lost at mapping boundaries

This is a proposed follow-up, not an active implementation plan or authorization
to change native physics. The current SIFT conversion can be accepted on its own.
The original rock/surface-cover and Roads programs remain open.

## First establish whether the synthetic mechanisms occur in histories

Use an observation-only build to record every FRWATC invocation in complete
predeclared histories, including normal and threshold controls. Record execution
order, day/hour, owning OFE, coarse/fine indices, actual fine-layer geometry,
mode, ST and YST, THETDR, DG, UL, FRZW, SOILW, NWFRZZ, SLSW, SLSIC and SLFSD.
Observe the entry and exit of each mapping and the consumer immediately following
it. Count omitted supports, cleared frozen-zone liquid and each skipped-delta
branch separately. Retain zero counts as observed zeros; absent calls are missing
support, not zero loss.

Reconstruct physical liquid and ice using the same support definitions already
reviewed in this package. Report signed residual per invocation and aggregate
only disjoint transfers. A representation mismatch can later be restored, persist
or propagate into an external flux; summing all mismatches across repeated calls
would double-count. Follow each residual to the next mapping or named transfer
before reporting any annual loss.

Accept the observer only if all ordinary outputs match the corresponding
unchanged complete histories exactly. Bind compiler, full source/include/object
inventory, executable, all runtime inputs and calendar. Do not use a partial
source directory as build provenance. Preserve the original histories and keep
new artifacts in a fresh root. No withheld Roads materials are needed for this
mechanism test.

## Define the correction before testing one

The five counterexamples imply three distinct ownership questions:

1. For nonzero unfrozen support below 1 mm, identify whether water must remain in
   fine storage, enter coarse storage, or move through a named transfer. A layer
   geometry threshold cannot by itself authorize dropping a stock.
2. When a frozen zone becomes too thin to retain NWFRZZ, name its recipient and
   require an equal and opposite stock change. Clearing the value after coarse
   reconstruction conceals the first mismatch and fails on the next mapping.
3. For small requested water changes, either apply the change or retain an
   explicit residual for later reconciliation. A tolerance is a comparison bound,
   not an unnamed sink or source.

Review each rule scientifically and against existing native conventions before
any behavioral ablation. Retain all 29 current fixtures as regression evidence,
including the five failing examples. Add exact floating-point branch boundaries,
multiple coarse layers, shortage carried between layers and simultaneous liquid/
ice constraints. Do not adjust comparison bounds to admit a proposed fix.

## Keep drainage and phase-change gates independent

A frozen mapping repair does not establish feasible conductivity or drainage.
The source inventory identifies FC/UL in the conductivity logarithm and
UL-minus-DRFC in hourly lateral drainage; ordered dry, field and saturation
limits alone do not protect those expressions. PURK/PERC, tile drainage and ET
must be exercised with actual accepted stock removals, not requested fluxes.
Only bottom seepage is external to a profile; interlayer transfers must cancel.

FRZNW/FRZNG also compare frozen support capacity with absolute fine-grid ice.
The passing FRWATC dry-reference controls do not validate those phase-change
expressions. Any later capacity change requires their own reference-consistent
stock/energy evidence, complete daily/hourly coupling and full-period comparison.
No global multiplication of POR or UL is ready for promotion.

## Surface rock work can proceed separately

The next useful surface-data artifact is a provenance-preserving observation
table: measured/proxy source, particle-size cutoff, total-area versus bare-area
support, vegetation overlap, covered/exposed status, date, component weight and
unsupported/unallocated area. Unknown and observed zero must remain distinct.
The earlier survey acquisition is incomplete and does not justify a Roads armor
map. Profile volume-to-mass conversion supplies none of the missing overlap
information. Choose a measured or explicitly declared surface interpretation
before proposing a new erosion-model default.

## Stop and acceptance rules

Observation failures stop interpretation until build/runtime identity or reader
errors are resolved. A finding of no occurrence in the declared histories is a
valid bounded result, not proof that the synthetic counterexamples are impossible.
A failed behavioral candidate remains retained and is rolled back; do not stack
unattributed threshold, porosity and drainage edits. Promotion requires complete
stock/flux accounting, non-regression and independently reviewed scientific
validity. Deployment and Roads parameter/UI acceptance are separate decisions.
