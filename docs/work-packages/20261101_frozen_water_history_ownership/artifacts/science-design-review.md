# Independent scientific design: frozen-water history ownership

Disposition: approve the six-scenario concept as a bounded observation campaign,
subject to a frozen observation/schema declaration and implementation prereview.
No build or execution by this reviewer. No native formula, parameter default or
surface mechanism is authorized. Prior synthetic conservation failures remain
valid even if none occurs in the selected histories.

## Source identity and activation

Independently verified sizes and SHA256 for all978 members of the retained
storage-observer build. Its binary is
`5f6bcebac1c82111a6a7c9685cd0d2a04f2e6c3066a3637e533a1a8054ff38b1`.
The frozen core FRWATC/FROSTN/WINTER/FRZNG/FRZNW/MLTTP/MLTBTM/WATDST matches the
canonical source byte-for-byte; other bound hydrologic callers contain the
retained earlier instrumentation. [Source bindings](science-source-bindings.json)
identify both versions. Compile from the complete pinned build lineage, not a
small source selection. Line references below identify the pinned copy.

WINTER335–340 requires a weather/frost predicate and effective KSFLAG=1 before
calling FROSTN. Existing `wfr_calls` increments before the KSFLAG check, so it is
not proof of an executed FROSTN call. Observe both predicates and an actual
call-entry/return marker. Log effective KSFLAG and its runtime initialization;
header0 alone is insufficient in general because SCON has an assignment in
its conductivity initialization path. Preserve the actual input header too.

FROSTN199–234 establishes NFINE. Its no-frost and initial-frost branches
(248–334) create fine state and set YST. Direction1 is only the subsequent
`else if hour=1` path (335–338), not every hour1. Direction0 runs at hour24 or
thaw completion (686). Day/hour/OFE keys alone need not identify a unique call;
use an ordered invocation ID and its parent FROSTN call. Do not infer absence
of mapping1 from a missing trace when fine-grid initialization replaced it.

## Panel and interpretation

Use the original zero/normal/high SIFT16-year, three-OFE inputs as inactive
controls and corresponding explicitly labeled KSFLAG1 diagnostic copies. Verify
that only the intended flag differs; preserve all other input bytes, calendar
and native caps. Establish a fresh pinned-binary baseline for each enabled
scenario before observer parity. Original inactive baselines may be reused only
with their complete input/output identities; fresh observer outputs must match
all seven ordinary outputs exactly, including successful complete calendars.

KSFLAG also selects conductivity behavior, so these pairs are not isolated frost
interventions. An occurrence in an enabled history is evidence about that explicit
diagnostic scenario, not a counterfactual loss attributed to the original SIFT
run. Do not compare their annual runoff/sediment as a causal frost effect.

Six scenarios are sufficient to answer whether the specified mechanisms occur
in those scenarios and to test inactive/active observability. They are not a
representative BC/Roads panel or a guarantee of full frost/partial thaw/shortage
coverage. Retain actual counts of weather opportunities, FROSTN calls, fine-grid
initializations and each mapping direction. No actual frost activity or no
particular threshold hit is a valid bounded result; add another scenario only
through a new declaration, not by tuning inputs until a desired signature occurs.
The retained29 synthetic fixtures are mandatory true-positive observation
controls, so a zero history count is interpretable as observed absence within
support rather than an untested detector.

## Minimum event and state contract

Each record needs run/scenario and executable identities, monotonically increasing
record sequence, invocation and parent IDs, simulation year/day/hour, owning OFE,
coarse/fine indices, mapping direction and stage. Use complete counted blocks
with start/end markers and declared NSL/NFINE. Reject truncated, duplicate,
out-of-order or cross-owner joins. Record initialization epoch/branch so fine
support can be reset legitimately without mistaking it for transported water.

At every valid FRWATC entry and exit retain all active layers: DG, THETDR, UL,
ST, YST, FRZW, FROZEN, SOILW, NWFRZZ, NFINE, SLSW, SLSIC and SLFSD, plus SAXFC
for the drainage path. Emit native REAL values losslessly, for example by exact
promotion to double and at least17 significant decimal digits. Record the actual
REAL-computed fine unfrozen support, not only its double reconstruction.
Physical units are water-equivalent meters except volumetric SLSW/THETDR/SAXFC
and soil-thickness supports. Do not read fine arrays before their initialized
support is known or uninitialized branch locals simply to fill a uniform record.

A native branch marker is stronger than an inferred predicate. Record the actual
predicate outcome and operands in its valid branch. Required branch support:

| Signature or competing path | Minimum native observations |
| --- | --- |
| F: direction0 omitted fine support | Actual `slufdp`, threshold result, SLSW and dry reference; skipped supports count even if their water/reference difference is zero. |
| G: direction1 unapplied change | Initial ST-YST, FGLCKW, remaining VARWAT after frozen-zone and SAXFC allocations, VARUFP, VARSW, per-fine VARDP and eligibility. Distinguish zero remaining request from a skipped nonzero request. |
| H: frozen-zone liquid clearing | FROZEN and NWFRZZ immediately before reset134, ST/SOILW already assigned130–131, and actual cleared amount. Preserve entry/exit snapshots to distinguish fine loss from coarse persistence. |
| I-small: absolute-delta gate | Actual VARWAT, FGLCKW and result at160–161. Count nonzero ignored change separately from exact zero. |
| I-middle: volumetric-change gate | Actual remaining VARWAT, VARUFP, VARSW and FGLCKW at225–231. Record whether the earlier frozen allocation or drainage already consumed the request. |
| Competing allocation/floor paths | ST=0 branch149–154; frozen spare/NWINC and remainder shortcut198–219; SAXFC withdrawals175–193; WLCK/LACKW before/after carries and unresolved carry at the final supported layer. |

Observing only the five named outcomes is insufficient for ownership: their
competing branches can satisfy part of the request or move a shortage to another
layer. Local carries need initialized values only: WLCK is valid after92, and
FGLCKW/LACKW after141–142. VARWAT/VARSW/SPCAV are not valid at every entry.
Keep observation output separate from model variables and preserve arithmetic
order, COMMON layout and branch control.

## Independent stocks and numeric comparisons

Reconstruct fine liquid as sum(SLSW*u)+NWFRZZ, fine ice as sum(SLSIC), and coarse
total as ST+FRZW+THETDR*DG. Reconstruct coarse liquid with dry reference on
unfrozen support and ice with dry reference on frozen support. NWFRZZ is already
part of ST. SOILW is an independently checked reporting representation, not an
extra stock. Report geometry closure and invalid/negative supports explicitly.
Do not clamp observations to manufacture admissible geometry.

Use exact emitted native REAL operands for branch interpretation. The relevant
binary32 constants are1mm=0.0010000000474974513m,
1e-7=1.0000000116860974e-7m and1e-5=9.999999747378752e-6 in their respective
units. The last threshold is volumetric when applied to VARSW and a depth when
applied to remaining VARWAT; never aggregate them as the same quantity.
Nominal decimal equality is not a substitute for observed native comparison.

The synthetic normal bounds remain2e-8m for stock and2e-7 for the paired fine
fraction comparison; retain all actual residuals. Do not transplant2e-8m as a
universal annual/profile conservation tolerance. For history arithmetic, require
lossless REAL readback, exact integer clock/support joins, and independently
reconstructed actual branch outcomes. Use deterministic double accumulation
for physical sums. A reproducibility bound for two independently accumulated
sums can be stated as twice gamma_k times the sum of absolute terms, where
u64=2^-53, gamma_k=k*u64/(1-k*u64), and k conservatively counts all products and
additions used in that particular stock expression. Declare the implementation's
count before execution; this bounds reader arithmetic, not model water loss.

Keep source REAL rounding separate: independently replay the relevant native
scalar operation order for reference transformations and threshold predicates,
retaining its difference from the physical double stock. A tiny skipped native
request is a true branch occurrence even when below a broad physical residual
bound. Counts, signed depth, rounding contribution and unassigned residual must
remain separate columns; never erase threshold occurrences with a tolerance.

## Next consumer and residual ownership

Every FRWATC return should carry its invocation ID into the immediate caller
checkpoint. Direction1 then feeds FROSTN's fine-grid calculations and subsequent
FRZNG/MLTTP/MLTBTM/WATDST paths (FROSTN660–681). Observe the fine stock and coarse
stock before/after each executed stock-mutating routine, plus which branch ran.
The quantities have different authority at that clock; a coarse/fine mismatch
is not itself an external flux. Mark intervening energy-driven phase changes,
new water or geometry changes explicitly; if their contributions are not
observed, retain unresolved ownership rather than attributing all change to
the preceding mapping.

Direction0 returns to FROSTN and WINTER, possibly followed by another winter
hour/init branch. Also retain the WINTER→CONTIN return checkpoint. In the pinned
call flow, CONTIN850 calls WINTER, CONTIN972 calls IRS, IRS394 can call GRNA,
and WATBAL can run inside IRS593 or at CONTIN1128. Therefore there is no single
universal next hydrologic consumer. Instrument actual GRNA entry and WATBAL entry/
exit with phase/owner IDs, and next fine-grid initialization or FRWATC invocation
for the same owner. SOIL/INFPAR earlier in the day is not a later consumer of
that day's winter mapping (CONTIN812 precedes WINTER850).

At GRNA, record the consumed saved/local ST, UL and live FRZW and identify any
upstream owner/snapshot reuse. At WATBAL retain stock before/after, accepted
external/interlayer transfers and their area/length convention if a flux claim
is intended. A WATBAL exit difference alone does not isolate FRWATC's effect.
Hourly percolation, ET, tile/lateral removal and surface return remain independent
owners; do not subtract a requested flux as though it was actually removed.

Maintain one ledger entry per newly introduced unassigned amount, with source
invocation/layer/support and successive resolution states: remains represented,
transferred with a named recipient, recovered, overwritten, or unresolved.
A repeated coarse-minus-fine difference is a continuing imbalance, not a second
loss. H's clearing and later coarse catch-up are one stock event, not two;
G's unapplied requested change and F-style omission are distinct mechanisms.
A representation reset may erase, restore or change an imbalance and must remain
visible. Aggregate only disjoint, causally followed changes in a common spatial
basis. Without complete ownership, report occurrence and residual ranges plus
unresolved endpoints, not annual water loss or sediment attribution.

## Pre-invocation gates and limits

Require a concrete observation schema, complete private patch review, all29
synthetic controls reproducing original final states/signatures, and complete
seven-output parity for every accepted history against the correctly matched
pinned baseline. All enabled inputs must first complete their uninstrumented
baseline or retain the failure. Do not weaken activation, weather, physical
thresholds or model precision to obtain an event.

No branch occurrence is an automatic mandate for a native fix. This panel may
establish recurring mapping inconsistencies and bounded ownership without
establishing a conservative replacement. Drainage domains, freeze/thaw energy,
surface support and eventual release/UI acceptance remain separate. Declare a
larger panel or behavioral lane only after interpreting this bounded result.

## Accepted bounded alternative: first stock consumer only

For the first history campaign, full snapshots at every hourly fine-grid boundary
are not required if conclusions stop at the observed ownership endpoint. The
following narrower design is scientifically useful and acceptable for a frozen
prereview declaration:

- Keep every actual FRWATC entry/exit with complete active fine/coarse states and
  the branch observations above. No sampling of mapping invocations.
- Keep actual WINTER gating/FROSTN calls and initialized-support provenance.
  Record coarse CONTIN boundaries before/after WINTER and before/after each
  actual WATBAL path, including the IRS path where it executes.
- While a mapping residual is pending, record full fine/coarse before/after the
  first executed stock-mutating frost phase or fine-grid initialization. These
  are directed observations, not every hour's fine-array dump. Record the routine
  or initialization branch and any known donor state, especially SOILW for
  no-frost reinitialization. Physical support must be valid before a fine dump.
- Keep enough per-OFE linkage across hours/days to follow H-style liquid clearing
  into possible later SOILW-based fine-grid restoration. A single latest-map ID
  must not overwrite an older open residual. The offline ledger can maintain
  these identities from ordered events; observer bookkeeping must not modify
  model state or COMMON layouts.
- If GRNA entry/read support is omitted, call the endpoint a next observed stock
  writer/boundary, not a proved next consumer. A small coarse-only first-two-layer
  GRNA entry record with saved/upstream owner clocks is sufficient for a claim
  about delivery to that reader; it does not establish a resulting flux change.

A first phase's pre/post stocks establish only the change across that observed
routine. They do not isolate its causal dependence on a prior imbalance or close
unobserved phase-energy/input terms. Mark the ledger unresolved at the first
unobserved stock mutation, or at an observed boundary whose external terms are
unknown. A later FRWATC can reveal the then-current mismatch but does not assign
all intervening change to the original event. Coarse-only boundaries cannot prove
fine-grid stock conservation between them.

This reduced campaign can defensibly report occurrence, the direct mapping
residual, delivery to a first observed writer, immediate clearing/restoration,
and unresolved future ownership. It cannot report complete hydrologic closure,
unique annual lost water or runoff/sediment effects. In particular, do not sum H's
fine clear, coarse persistence, later coarse overwrite and possible SOILW restore
as independent losses. A subsequent study may add the missing transitions once
actual recurrence identifies which observations are needed.
