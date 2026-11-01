# Scientific prereview: prepared-v6 observation layer

Disposition: useful bounded observation design, with one initialization-support
condition requiring resolution and two interpretation constraints below. This
is not yet complete campaign invocation approval: the reader, runner and frozen
declaration remain to be reviewed. No build/run or native-source edit by reviewer.

Reviewed the actual authored helper/state/control driver and private prepared-v6
patch, not merely the intended instrumentation. No legacy source is reproduced
here. Bound identities are listed below.

## Required initialization-support resolution

FH_READY treats every nonzero initialization kind as fully valid when NFINE is
in range. That is justified for the complete no-frost assignment loop and the
explicit synthetic driver initialization, but not automatically for the native
initial-frost branch. Its second initialization loop reuses JSTART on subsequent
coarse layers; it can leave lower fine indices outside that loop. A valid NFINE
alone proves neither assignment nor retained-value initialization provenance.

Before declaring fine support available for kind2, either track the actual
assignment coverage with observer-only bookkeeping, establish a prior complete
initialized state with compatible support, or report the unproven support as
unavailable. Do not initialize native arrays merely to make observations valid.
A case-specific declaration excluding initial-frost entry can bound interpretation
but must be checked against actual branch markers. Cold-weather entry through
normal no-frost initialization remains a separate valid path. This concern is
about the helper's availability claim, not a newly demonstrated history defect.

## Accounting and labeling constraints

**D1_END VARWAT is not final unapplied liquid.** FRWATC can successfully distribute
VARSW across fine layers without reducing VARWAT. Therefore a nonzero final
VARWAT must not become a ledger loss or unapplied-flux total. Recover actual fine
stock change, requested ST-minus-YST, earlier frozen/SAXFC allocations, skipped
supports and carried shortage separately. D1_VOL_REQUEST is a pre-distribution
request; D1_UPDATE_END and complete map snapshots establish what happened.

PHASE_PRE/POST bracket the first executed frost phase block, which can include
FRZNG, a melt routine and WATDST. Describe it as a composite phase boundary,
not the first individual routine or a proved recipient of a mapping residual.
Immediate pre/post physical stock is meaningful; internal ownership and energy
transfers remain unresolved without additional observations. GRNA reader delivery
is not covered by the proposed coarse WINTER/WATBAL snapshots and must not be
claimed from them.

FN_INIT increments the epoch before INIT_PRE, so that number identifies the
initialization event/target epoch; INIT_PRE's fine values belong to the preceding
state. Define that distinction in the schema rather than treating both records
as already initialized under the new epoch. Earlier open H-event identities
must remain in the offline ledger even though helper FH_LAST identifies only
the newest mapping. The persistent initialization-pending flag provides later
state observations; it does not establish one-to-one causal attribution.

## Positive findings

Mapping snapshots are complete when support is available and include SOILW,
NWFRZZ, adjusted ice and dry-reference variables. The actual branch markers
expose thresholds, frozen allocation, SAXFC withdrawals and shortage carries.
The inserted local reads inspected are placed after native assignment, including
VARWAT only in its nonzero-ST branch and VARDP after the zero-depth skip. Missing
fine/SAXFC support is explicitly marked unavailable rather than silently inferred
from a zero placeholder. Readers must honor the availability flag.

WINTER logs actual weather eligibility, runtime KSFLAG and actual FROSTN call
boundaries. This separates the existing weather counter from executed calls.
Both CONTIN and IRS WATBAL paths are observed, and WB_PATH identifies daily versus
hourly dispatch. All native COMMONs are read-only in the helper; observer state
is separate. Synthetic readiness kind3 makes the standalone control driver's
assigned fine values observable without relying on an unexecuted FROSTN path.

The pending phase flag and separate initialization flag preserve opportunities
to see a later SOILW-based restore after an H-style clear. Such restoration must
be reported as observed state evolution, not automatically as recovery of every
older amount. Stop ownership at unobserved/intervening mutations. No annual-loss
aggregation, whole-cycle closure or physical correction is approved by this
instrumentation review.

## Remaining gates

Resolve kind2 support provenance, freeze the schema/interpretation above, and
review the actual reader/runner before invocation. Then demonstrate29 synthetic
final-state parity and signature recovery, plus seven-output byte parity for
all accepted complete histories against matched baselines. Observation-induced
failure or an unavailable required mapping block stops that interpretation;
it is not permission to change native physics or loosen thresholds.

## Reviewed bindings

- `docs/work-packages/20261101_frozen_water_history_ownership/artifacts/fh_observer.for` SHA256 `6a31f748c565fa7419b1635840d98d614bac72c6b50b877d7c77e295768843ad`.
- `docs/work-packages/20261101_frozen_water_history_ownership/artifacts/fh_state.inc` SHA256 `a8b738dcfb0b6797f6d56c5b35dd0e1513a61aaf1f6ebc4365ddbc0888d24cea`.
- `docs/work-packages/20261101_frozen_water_history_ownership/artifacts/observer_control_driver.for` SHA256 `65c94b8a6298151c11d701d20f770fc9f77854d7cdf9a2a3f04ba162c4eb1c0b`.
- `out/frozen-water-history-20261101/prepared-v6/observer.patch` SHA256 `8bc90f6d3944b1436483b8853310e87d1f0b150aa71b4e9a15a92566846a7896`.
- `out/frozen-water-history-20261101/prepared-v6/source-bindings.json` SHA256 `081176e8f8ab610a0b31ed572f397e04a8346f57bafd4a8e7523ccfdf15c1cf2`.

## Prepared-v7 scientific closure

The initialization-support condition is resolved for the reviewed observer.
Only complete no-frost initialization (kind1) or explicitly initialized synthetic
state (kind3) establishes coverage. Kind2 and no-initialization paths require
prior readiness and unchanged fine counts. This establishes initialized-value
provenance, not proof that every such state is physically coherent; geometry
and stock checks remain the reader's responsibility.

Unavailable branch records now emit G without dereferencing the REAL arguments;
readers must preserve that as unavailable support and must not count it as a
zero threshold event. Valid-support mismatches cannot be silently repaired or
filled from adjacent records. The supplied branch arguments use assigned locals
or array-element references; no new physical expression is evaluated by the
helper to replace missing data.

FROST_BLOCK_PRE/POST now accurately identify the composite phase boundary.
The earlier constraints remain: final VARWAT is not necessarily unapplied water,
INIT_PRE is a preinitialization state associated with the target epoch, and
older open residual identities require the offline ledger.

Scientific instrumentation closure accepted for prepared-v7. This is not
campaign execution approval: the concrete observation schema, reader, runner,
declaration, synthetic controls and implementation review remain required.
No build or model execution was performed by this reviewer.

Reviewed v7 SHA256 bindings:

- `docs/work-packages/20261101_frozen_water_history_ownership/artifacts/fh_observer.for`: `caa18c97f6d7ff62ee56a47dabab27de7dca7b94f20b967d6a1f5ff33f1c56f8`.
- `docs/work-packages/20261101_frozen_water_history_ownership/artifacts/fh_state.inc`: `a8b738dcfb0b6797f6d56c5b35dd0e1513a61aaf1f6ebc4365ddbc0888d24cea`.
- `docs/work-packages/20261101_frozen_water_history_ownership/artifacts/observer_control_driver.for`: `65c94b8a6298151c11d701d20f770fc9f77854d7cdf9a2a3f04ba162c4eb1c0b`.
- `out/frozen-water-history-20261101/prepared-v7/observer.patch`: `7c51fe2d9830ba025894fe1a3fc84fc9ee981c37493e5074eb25e7473a9a70ba`.
- `out/frozen-water-history-20261101/prepared-v7/source-bindings.json`: `ed6921e1ef01c77614b233164fb8601c357f9041841f18aa36c688515e8a2cc0`.
