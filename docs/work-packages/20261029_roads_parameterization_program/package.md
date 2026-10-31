# Roads parameterization and configuration view

Current resumption (2026-10-31): revision-3 native release and scientific/application
review are complete. Use [ledger v12](artifacts/candidate-ledger-v12.json), not
historical release prerequisites below. All 840 cases pass physical checks;
713/766 meaningful and 31/74 small comparisons meet magnitude criteria. Refresh
road/fill/buffer attribution on the final pair before the next parameter contrast.
Withheld materials and the human UI specification/layout gate remain untouched.

Status: active. One outcome-driven program, authorized by the operator on
2026-10-29 Pacific (2026-10-30 UTC). This supersedes the sequence of individually
approved experiments; closed studies remain historical evidence.

Deliver a physically defensible Roads parameterization using WEPPcloud-generated
soils and released `wepp_261029`, with order-of-magnitude agreement against FSWEPP2 Roads,
then a run-scoped Roads parameterization view for editing key values by road
configuration. The operator clarified that users need not edit CSV files.

Execution follows the [active plan](prompts/active/program_execplan.md),
[acceptance criteria](acceptance.md), [autonomy charter](autonomy.md) and
[tracker](tracker.md). Completion requires both the scientific gate and a working
user-facing workflow, not a favorable selected case or a scaffold.

## Current scientific checkpoint

Current [ledger v10](artifacts/candidate-ledger-v10.json): D2 confirms the
EPLANE array-origin defect. Both twelve-case factorial lanes and clean-output
parity pass. Combined source candidate implemented; broader gates underway.
See [findings](artifacts/native-D2-geometry-findings.md) and proposed ADR-0119.

Earlier ledger v9 rejected standalone U1 because scalar continuity alone left
an unsupported local surface source; that rejected control remains retained.


Earlier [ledger v8](artifacts/candidate-ledger-v8.json): O6 identifies the QINF
regime discontinuity. Isolated U1 completes 12/12 full periods with no observed
unfunded demands; one negative local exchange remains unresolved. Scientific
acceptance and broad gates are pending. See
[findings](artifacts/native-ownership-findings.md).


Earlier [ledger v7](artifacts/candidate-ledger-v7.json): O5 reconciles matching-
boundary stock accounting (24 exact-parity replays; maximum residual 0.000312 mm).
Original funding failures remain. Next is O6 storm/recession ownership
attribution; see [findings](artifacts/native-stage-ledger-findings.md) and
[experiment specification](artifacts/native-joint-ownership-experiment.md).


Earlier [candidate ledger v6](artifacts/candidate-ledger-v6.json) includes the rejected O4 shadow rule.

O4 adds 26 exact-parity executions and analyzes 185,824 states; monotone
recession ownership creates 179 negative outflows. Reconcile stock/sink
observation boundaries, then define joint GRNA/QINF local ownership before any
behavior lane. See [shadow findings](artifacts/native-shadow-ledger-findings.md).


Earlier native observation: ten self-contained fixtures and 70 exact status/output
comparisons locate an unfunded daily request before hourly losses. Next is a
shadow water-ownership ledger, not a guard or parameter change. See
[native observation findings](artifacts/native-funding-observation-findings.md).


Earlier continuation (2026-10-31): restriction provenance and the 52-case
no-detected boundary-flag control are complete. Zero misses recovered; five
substantive native funding failures retained. Next is an isolated native funding
trace, not parameter promotion. See [latest findings](artifacts/restriction-provenance-findings.md)
and [historical ledger v4](artifacts/candidate-ledger-v4.json). The U10 acceptance
counts below remain the unchanged baseline; later experimental failures are not
covered by that baseline pass statement.


The native accounting investigation accepts the bounded repairs in `wepp_261029`
artifact revision 2, source `ba9f2ad91`. The frozen U10 panel passes all 840
physical/accounting cases. Parameterization acceptance remains unmet: 719/766
meaningful-reference cases (93.864%) and 30/74 small-reference cases (40.541%)
pass; 749/840 is only a descriptive combined score. Annual exports match U9a at
reported precision. Six withheld materials remain unused; no Roads defaults or UI
have changed. See [U10 scoring](artifacts/U10-magnitude-summary.json) and the
[release integration](../20261030_wepp_261029_rerelease/package.md).

Next: with revision-2 release integration complete, investigate outunrut low-reference and
routing behavior using the frozen development panel and physically justified
controls. The [failure-direction assessment](artifacts/U10-continuation-recommendation.md)
separates 41 meaningful low, six meaningful high and 44 small-reference misses.
Preserve the separate small-load criterion. Do not fit around native
defects, consume withheld materials early or treat accounting success as magnitude
acceptance. UI specification/layout remains human-gated before implementation.

The resumed [role-attribution study](artifacts/role-attribution-findings.md)
completes 840 paired boundary readbacks and 111 same-engine legacy-soil controls.
It points to downstream soil treatment while retaining nine distinct residual
engine/runtime comparisons. Legacy substitution is diagnostic only; generated
parameterization acceptance remains unmet.

## User-facing intent

Users select a road configuration and see relevant parameters, units, defaults,
current overrides and concise explanations. They can change supported values,
validate, save and reset defaults. Saved changes propagate to generated Roads
inputs and a subsequent Roads run. Existing results are marked stale when needed;
saving must not silently imply that WEPP has rerun. The view should use familiar
WEPPcloud controls. Storage format is an implementation choice; manual CSV editing
is not the workflow. Import/export is optional, not a completion requirement.

Expose only supported parameters identified during the study. Likely families are
road-surface erodibility, critical shear, rock/cover and compaction hydraulics, with
separate fill/buffer settings where justified. Do not expose every native parameter
or promise arbitrary changes remain benchmark-validated.

## Compatibility and boundaries

Preserve existing projects' effective behavior until an explicit adoption/reset or
migration action; version accepted defaults and overrides. Parameterization is
Roads-scoped. Do not alter general SSURGO generation, Disturbed defaults, uploaded
soil semantics or the shared property-preserving 200 mm normalization. Native
binary is the reviewed matched `wepp_261029` pair; retain `wepp_261026` as a
historical control. Any further binary change needs its own explicit disposition. Production deployment is separate.

Before production implementation, promote durable scientific/UX/data rules into
canonical contracts, record parameterization ADRs, and complete the repository's
reviewed ancestor-checkpoint requirement. The current instruction authorizes this
program's objective and autonomous experimental choices; it does not imply a
specific unreviewed field schema or production rollout.

Security impact: medium potential because the final view writes run-scoped model
inputs. Preserve existing run authorization, readonly and CSRF controls; retain
correctness and security/noninterference review. Reassess if the actual design adds
an authorization boundary. Complexity budget: existing Roads/NoDb/Flask/controller
patterns, owned native writers/readers and local batch execution; no new service,
dependency, optimizer infrastructure or deployment topology.


## Human gate for configuration specification and layout

Operator instruction, 2026-10-30: continue the recommended scientific program
with broad authority to use forest, up to a human review of the UI configuration
specification and layout. Prepare concrete fields, units, ranges, applicability,
version/adoption/reset behavior and a static layout proposal. Human approval of
both specification and layout is required before implementing the configuration
view or its production persistence/application wiring. Scientific experiments,
disposable builder/full-project validation and reviewable design documents remain
authorized. Do not treat silence, scientific acceptance or AI review as UI approval.

## Historical revision-2 scientific checkpoint

Completed 333 erosion-anchor and 98 runtime-factor runs; see
[findings](artifacts/role-runtime-ablation-findings.md). Erosion-only substitution
recovers at most 10/91 misses and loses one passing control; reject promotion.
Hourly-off with PMET/snow fixed recovers 8/9 legacy residual input sets. Six
alternate hourly/Penman cases fail the native water guard and remain rejected.
All 431 recorded input/output inventories and soil changes independently verified;
raw evidence has a verified archive receipt. Next: generated/legacy soil crossed
with hourly on/off, keeping PMET/snow present, before hydraulic parameter choice.
No defaults or acceptance changes; withheld outcomes and human UI gate untouched.

## Completed soil/hourly interaction

[Findings and figure](artifacts/soil-hourly-interaction-findings.md): 208 new runs
and 236 reused cells complete the 111-case factorial; all 444 physical audits
reproduce. Generated hourly-off recovers 21/91 misses but loses a passing control;
legacy-off passes 108/111, with three labels aliasing one remaining failing input.
Reject runtime-only promotion. Next: trace generated lower-boundary provenance
and native drainage semantics before declaring hydraulic changes. Current
[candidate ledger](artifacts/candidate-ledger-v3.json) supersedes historical v2.
No defaults, withheld outcomes or UI implementation changed.

## Restriction audit and boundary-flag control completed

[Findings](artifacts/restriction-provenance-findings.md): seven source materials
classified by retained generation evidence; 52 no-detected flag-off runs yielded
47 physical passes, zero recovered misses and five native funding stops. Exact
paired files and completed native audits verified. Reject promotion; investigate
0.131–0.180 mm hourly funding deficits on the retained PMET-on failing decks
before more tuning. [Ledger v4](artifacts/candidate-ledger-v4.json) is current.
No parameter/binary changes, withheld outcomes or UI implementation.

## Historical D2 candidate checkpoint — 2026-10-31

[Findings](artifacts/native-D2-geometry-findings.md) and [ledger v10](artifacts/candidate-ledger-v10.json)
are current. Confirmed native array-origin defect; origin-only and combined
candidates each pass twelve full-period physical checks. Clean candidate outputs
match the combined observer exactly. Source candidate implemented with 13 new
regression tests; 75 existing focused tests pass. [ADR-0119](../../adrs/ADR-0119-native-recession-and-equivalent-plane-geometry.md)
is proposed. Finish native gates, then Disturbed, Cedar Creek and Roads magnitude
rebaselining. Released binaries/defaults unchanged; withheld outcomes untouched;
UI specification/layout remains human-gated.

### Broader D2 checkpoint

Native gates: 1073 tests and 18 watchlist cases pass; Disturbed 99 pass. Roads physical gate 840/840; magnitude 713/766 meaningful and 31/74 small, two recoveries and seven regressions. All 864 Cedar hillslopes complete; watershed and semantic/particle audit pending. No release or parameter adoption.

## Accepted native baseline: artifact revision 3

The user authorized re-releasing the undeployed `wepp_261029` under its existing
name. The matched final pair is vendored; source and scientific gates passed.
[Ledger v12](artifacts/candidate-ledger-v12.json) is current. The
[release package](../20261031_wepp_261029_rerelease_r3/package.md) records
application and publication delivery. This fixes native geometry/recession defects;
Roads parameterization acceptance remains unmet at 713/766 meaningful and 31/74
small references. No parameter defaults or UI are promoted.
