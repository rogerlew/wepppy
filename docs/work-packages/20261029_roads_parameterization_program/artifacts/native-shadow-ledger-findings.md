# Native shadow ownership findings

The monotone cumulative recession rule is rejected. Preserving already assigned
QINF loss alone does not reconcile the equivalent-plane GRNA calculation with
local soil ownership. No native behavior, release binary, Roads parameter or
acceptance threshold changed.

## Evidence

O4 adds 26 native executions: ten original fixtures with observation off/on,
plus fresh release/off/on runs for delayed-return and Charleston deposition
controls. All expected statuses and complete output inventories match exactly.
Ten executions reproduce the five known failures; 16 complete successfully.
Together with O0–O3 the incident retains 96 executions. Expected failure parity
is not a physical pass. The supplemental decks cover their full 16 years.

The offline ledger retains 185,824 daily element states (185,819 completed),
including 4,310 linked GRNA/QINF states, 331 return-input states, 62,463 lateral-
input states, 3,008 ROCHEK states and 2,746 states absorbing incoming runoff.
The rule `R_owned = max(previous_owned, R_equivalent)` and
`Q_shadow = Q_raw - R_owned` produces 425 negative incremental recession
requests and **179 negative outflows** above the 1e-6 m³ display threshold.
All signed values remain in the raw ledger. No negative output was floored.

For example, delayed_return year 1/day 191/element 3 has 1.021654 m³ previously
assigned recession, 0.447189 m³ equivalent recession, and 0.014716 m³ actual
outflow. The shadow outflow becomes **−0.559750 m³**. This is a decisive
counterexample independent of the stock-ledger limitations below.

The original loam year 12/day 190/fill deficit changes from −0.051114 m³ to a
positive shadow funding margin of 0.725992 m³. That selected improvement cannot
validate a rule with impossible runoff elsewhere. Zero flagged unfunded shadow
states is not acceptance: negative outflow itself supplies fictitious water.

Ten retained geometry scenarios and two dispatch scenarios reproduce the earlier
C3 counterexamples: local peak scaling changes with element count and the
incoming-runoff deposition path can be lost. These prescribed-flow probes are
counterexamples, not full dynamic sediment validation of a new candidate.

## Observability limits

Actual daily FIN reconstructs to a maximum absolute error of 1.522e-6 m³ across
all states, using single-precision native marker values. However, the separate
stock/sink diagnostic has residuals as large as **2.400805 m³** (Charleston,
year 9/day 93/element 3). It is not a reconciled conservation ledger. The current
markers sample aggregate ET/sinks and stocks at different native stages; their
complete ownership/timing has not been established. Do not interpret those
residuals as a newly proved native water defect. Reconcile them before relying
on storage closure or promoting a behavior lane. The three frozen-sink capacity
warnings likewise cannot establish dynamic overflow.

The shadow holds actual stocks, routed return/lateral transfers and sinks fixed;
it is not a newly integrated trajectory. ROCHEK stages are counted but their
ownership is not inferred. The analyzed geometry is equal-width, noncontoured
hillslope only. No variable-width claim follows.

A repeated WBL_LOCAL marker occurs after WBL_END on some days because the
instrumentation anchor also matches a later interception reset. The parser
retains it as WBL_LOCAL_POST and never replaces the first value. Raw logs and
failed first parser attempt are retained. Two failed frame-probe setup attempts
preceded reconstruction using the hash-verified full historical C3 patch; these
were setup failures, not omitted simulations.

## Next bounded experiment

First extend stage observations to reconcile actual liquid/frozen storage and
ET, drainage, interception, return and lateral transfers at matching boundaries.
Use the worst stock residual above and the negative-runoff counterexample as
mandatory diagnostic fixtures alongside the original five failures.

Then declare a joint GRNA/QINF ownership hypothesis in physical volumes: each
local element may consume only water reaching it and its own available storage;
water already assigned upstream cannot be reintroduced by a downstream
averaging operation. Separate storm-time infiltration from recession losses.
Keep soil length, hydraulic routing length, reporting length and partially
wetted extent distinct. Preserve incoming-event evidence even with zero outlet
runoff. Do not restore C3 wholesale, clamp runoff, weaken the hourly guard, tune
parameters around the issue, or treat a frozen-state pass as a dynamic pass.

Only a reconciled ledger and explicit scientific contract justify one isolated
behavior lane. That lane must pass the ten full-period cases, delayed return,
zero recession/partial runon and geometry/deposition controls, followed by native
release gates, Disturbed, Cedar Creek and the unchanged 840-case Roads panel.
Withheld materials and the human UI specification/layout gate remain reserved.

## Reproduction and retention

Helpers and compact receipts are adjacent: build_ledger_observer.py,
O4-build.json, O4-off-replay.json, O4-on-replay.json,
replay_ledger_controls.py, O4-supplemental-replay.json,
replay_frame_controls.py, O4-frame-controls.json, shadow_ledger.py and
O4-ledger-summary.json. O4 source is isolated under
/workdir/wepppy/out/roads-native-funding-20261031/O4; production src is unchanged.
The new archive receipt is shadow-ledger-retention-receipt.json. Prior
observation-v1 archive and receipts remain immutable.

Native research package: `/workdir/wepp-forest-release-20261009/docs/work-packages/20261031-roads-open-boundary-funding`.
Parent ledger: [v6](candidate-ledger-v6.json).

Validation: O4 host smoke completed all three configured years. Package doc lint
and native ablation artifact policy pass. The shadow archive retains 695 files
(551,332,999 uncompressed bytes); every member SHA-256 was verified. Archive
SHA-256: `739e15e7e0a71d2b6d468cc03bfeeb1be4023c72472ddde84495b7496195f5ef`.
Full release/Disturbed/Cedar gates were not rerun because no behavioral candidate
or release is proposed.
