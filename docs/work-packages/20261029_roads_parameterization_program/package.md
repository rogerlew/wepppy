# Roads parameterization and configuration view

Status: active. One outcome-driven program, authorized by the operator on
2026-10-29 Pacific (2026-10-30 UTC). This supersedes the sequence of individually
approved experiments; closed studies remain historical evidence.

Deliver a physically defensible Roads parameterization using WEPPcloud-generated
soils and `wepp_261026`, with order-of-magnitude agreement against FSWEPP2 Roads,
then a run-scoped Roads parameterization view for editing key values by road
configuration. The operator clarified that users need not edit CSV files.

Execution follows the [active plan](prompts/active/program_execplan.md),
[acceptance criteria](acceptance.md), [autonomy charter](autonomy.md) and
[tracker](tracker.md). Completion requires both the scientific gate and a working
user-facing workflow, not a favorable selected case or a scaffold.

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
binary remains exact `wepp_261026`; any proposed change to that constraint is an
operator decision. Production deployment is separate.

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
