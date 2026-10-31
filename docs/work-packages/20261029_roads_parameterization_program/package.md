# Roads parameterization and configuration view

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
