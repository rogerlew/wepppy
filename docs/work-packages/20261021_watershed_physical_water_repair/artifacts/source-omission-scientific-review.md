# Source-omission scientific review

Independent read-only review, 2026-10-21. Reviewed actual WSHCQI/WSHCHR source,
WSHIMP output contracts, and the 40 source-assembly controls at
`/workdir/watershed-physical-water-repair-20261021/source-omission-controls-v4/receipt.json`.
Native source paths refer to `/workdir/wepp-forest-release-20261009`; the proposed
changes remain isolated in the experiment's four `wshchr.for` variants. No
production source was changed for this review.

**Corrected candidate disposition:** source inspection of
`/workdir/watershed-physical-water-repair-20261021/mc-interface-candidate-v2`
confirms removal of the redundant first-call baseflow addition and exclusion of
positive side-impoundment transfer from the new local-source branch. The actual
MC4/5 three-day receipt at `mc-baseflow-routing-v4/receipt.json` confirms a
uniform first-call baseflow state, 100 m³ first-day publication and retained
ordinary-day q0 carry. The two prototype findings below are closed for that
candidate. Scoped promotion is scientifically supported subject to final gates
and the independently reviewed threshold cascade. Signed coupling remains open;
see [signed-coupling-review.md](signed-coupling-review.md).

## Findings requiring disposition

### High: admitted baseflow is counted twice in the initial outlet state

Fix B adds `bflwpere/86400` to `qin(nt0:ntchr)`. On the first routing call,
nt0=0, so qin(0) now includes that source. The existing initial-state assignment
at `src/wshchr.for:259` also adds `bflwpere/86400` separately:

```text
q1(0) = qin(0) + qlat(0) + bflwpere/86400
```

The prototype therefore initializes the outlet with twice the admitted baseflow
contribution. For a baseflow-only 100 m³/day input, the inlet starts at
100/86400 m³/s while the outlet starts at 200/86400 m³/s. This alters the initial
discharge profile, geometric diagnostic and the subsequent MC trajectory.

The source-assembly probe returns before this assignment, so its passing source
sum cannot detect the error. **Required same-change correction:** remove the
now-redundant special baseflow addition from the first-call outlet initialization.
Initialize from the completely assembled qin(0)+qlat(0). Retain ordinary-day
q0 carry. Exercise a full first-call native MC4/5 baseflow-only control, then
continue through changing/zero daily baseflow; source-only observations are not
sufficient for this finding.

### Medium: the local-source predicate also introduces an impoundment timing rule

Fix A enters the existing uniform-lateral branch whenever the summed side-hill
surface volume is zero. However, `rvolat` already includes side-impoundment
`tmpvol(nileft/nirght)` at `src/wshcqi.for:167`. Thus a positive side-impoundment
release with no side-hill surface runoff now becomes a uniform 24-hour lateral
source, even with zero local channel water.

That recovers a previously omitted amount but introduces a release-time
approximation beyond the demonstrated local-source case. WSHIMP retains the
release amount, peak and duration (`src/wshimp.for:207` through `:215`). The
current controls initialize all impoundment links to zero and do not show that
uniform daily forcing preserves that release contract. Meanwhile top-impoundment
volume is admitted by `src/wshcqi.for:201` but still has no corresponding explicit
WSHCHR rate assembly. The two placements would remain inconsistent.

**Smallest narrow disposition:** restrict the new eligibility to ordinary
channels without a positive side-impoundment transfer, leaving the preexisting
impoundment gap explicit. The old `volin<=vsbbs` branch remains as it was.
Alternatively, retain the broader predicate only with isolated side/top
impoundment controls and a documented release representation. A volume-only
assembly pass does not establish impoundment timing correctness. No broader
routing-method change is needed to test this boundary.

## Supported contract: local net water without side-hill surface runoff

For ordinary channels define:

```text
V_lateral_net = rvolat + chnvol - rtrans
V_side_subsurface = lateral_hillslope + admitted_side_baseflow
```

The existing branch uses a uniform daily source when the net amount does not
exceed the subsurface amount. When the net amount is larger but side-hill
surface volume is zero, the old reconstruction branch has nothing to scale and
adds only subsurface flow; the positive channel-local remainder is omitted.
Extending the existing uniform branch to this case is a defensible bounded
source correction. It preserves the admitted amount and uses the existing
daily representation for a term without a finer temporal source trace.

The v4 controls demonstrate the independent causal effect:

| Ordinary-channel input | Baseline lateral source cells | Local-only correction |
| --- | ---: | ---: |
| 100 m³ local, zero side surface and loss | 0 m³ | 100.000000745 m³ |
| 100 m³ local, -20 m³ transmission exchange | 0 m³ | 120.000002906 m³ |
| 100 m³ local, 100 m³ loss | 0 m³ | 0 m³ |
| 100 m³ local, 150 m³ loss | -50.000000373 m³ | Identical source array |
| 100 m³ local, 100 m³ side surface | 200.000005960 m³ | Identical source array |

The small differences are from representing the uniform rate in native
precision; acceptance should derive its error bound from that conversion and
quadrature. Do not fit a tolerance to the table.

With positive side-hill surface runoff, the original `volhf` reconstruction
remains unchanged. That is good scope containment, but it means local water
continues to inherit side-hill surface timing in that branch. This correction
does not establish independent local timing in every mixed-source case.

## Supported contract: deferred upstream baseflow admission

WSHCQI defers groundwater below the contributing-area threshold using `bflw`
(`src/wshcqi.for:114`). At a receiving channel meeting the threshold it admits
the accumulated upstream amount as `bflwpere` (`:145`), includes it in qBase and
rvotop (`:157`, `:206`), and separately includes that channel's direct hillslope
baseflow. WSHCHR must supply the admitted upstream amount to its ordinary daily
top-rate array once. Adding a uniform `bflwpere/86400` contribution after the
upstream channel arrays is consistent with that existing daily baseflow contract.

It is distinct from upstream routed Q: below-threshold `bflw` was deferred from
those routed rates. Do not add already routed upstream baseflow again merely
because it is present in qBase. Use only the amount WSHCQI explicitly admits.

The retained controls show 100 m³ deferred upstream water entering the top
source in `lr_bf=1` above the threshold. At 10 ha contributing area with a 20 ha
threshold, it remains deferred with zero admitted source. Legacy `lr_bf=0`
source arrays remain identical. Combined local/baseflow controls add 100 m³
to each respective source path without cross-scaling. These observations support
Fix B's daily assembly **after correcting the first-call double count**.

Require an actual cascade with upstream deferred water, first qualifying
receiver and a further downstream channel. It must show one admission, then
ordinary rate/volume transfer, with direct hillslope baseflow separately
accounted. Include threshold equality. Do not infer this end-to-end property
solely from manually seeding one upstream `bflw` value.

### Required first-call and continuation controls

Use actual WSHCQI, WSHCHR and CHRSTATE with MC4 and MC5:

- Baseflow-only first call, 100 m³/day: verify qin(0)=q1(0)=100/86400 m³/s,
  a constant initial spatial profile, steady subsequent outlet within native
  arithmetic, and accepted outlet volume approximately 100 m³. Record initial
  H and G explicitly; the established steady initialization is not a dry start.
- Continue through 100→0→changed daily baseflow. Preserve the prior endpoint
  as q0, observe its dt*q0/2 source contribution on the dry-input day, and
  reconcile outlet recession with the carried MC state. Zero scheduled new
  baseflow does not imply zero outlet or zero initial stored discharge.
- Route three channels: upstream below threshold, the first receiver exactly
  at threshold, then another perennial receiver. Verify one baseflow admission
  followed by ordinary q1/tmpvol transfer; include direct hill baseflow as a
  separate contribution so it cannot mask double counting.
- Retain legacy-mode parity, local-only first/continuing days, unchanged negative
  and zero net sources, unchanged positive side-hill reconstruction, and a
  positive side-impoundment control proving the narrowed predicate stays off.

These controls should observe actual initial/full profiles, source components,
raw/exported outlet integrals, H/C/J/clipping and publication/transfer. The
corrected source amount alone does not establish any of those downstream facts.

## Quadrature and signed-exchange limits remain explicit

The probe reports positive-index rectangle source sums and exits before routing.
Its q1 sentinel makes nt0=0 even though sdate is 2. It does not exercise ordinary
midnight carry, MC4/5 consumption, clipping, initial state, publication or
downstream receipt. The 40 cases are assembly evidence, not full-routing tests.

On subsequent days a uniform new source with inherited q0 is consumed by the
point/trapezoidal path with the previously derived half-step endpoint term.
Cell-mode lateral consumption differs. Retain those source and carry ledgers;
do not renormalize unrelated arrays to force a daily total. A zero source-cell
gap on the first call is not a claim of zero per-day quadrature difference for
all later calls.

The negative-net array remains byte-identical in the retained control. Neither
fix proves that a requested loss is available at the appropriate time and
location, that raw MC rates remain nonnegative, or that outlet clipping
reconciles the withdrawal with the channel-soil calculation. A positive top
baseflow addition can make some water available but cannot justify an arbitrary
lateral demand. Keep requested, accepted and unmet withdrawals distinguishable
in the eventual signed-exchange contract. Do not clip away a shortfall or derive
a geometric store from the desired balance.

## Review disposition

The two intended source omissions are real and their proposed ordinary-channel
daily representations are scientifically defensible within the existing MC
interface. Before promotion, correct the first-call baseflow double count and
either contain or explicitly validate the impoundment effect. Retain full
first/subsequent-day MC and cascade evidence in addition to these assembly
controls. Signed-loss availability and source point/cell conversion remain
separate open acceptance boundaries; neither is repaired by these additions.
