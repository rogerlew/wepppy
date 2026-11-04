# Roads correctness, sensitivity and parameter controls


Status: replacement specification/layout approved at `9532a2968`, ratified at
`73b5da4ac`; Roads-owned parameterization and dedicated view implemented with
local native/report and lifecycle validation. The [settings contract](roads-settings-contract.md)
is the current project/view authority. Historical scope clarifications below do
not reopen the satisfied approval gate or adopt scientific defaults.

## Operator clarification: default settings and user overrides

Operator direction, 2026-11-03: this is a default settings harness, not a
calibration harness. Users need explicit key-driver overrides to increase/decrease
Roads runoff and sediment toward observations or user expectations. The former
five-fallback-only proposal is insufficient and requires revision; its reviews
apply only to that earlier scope. Lack of field calibration does not exclude useful
controls. Preserve source values, explicit override precedence and honest response
limits. See the authoritative [requirement and rationale](roads-settings-contract.md#operator-clarification-default-settings-and-user-overrides).
Specification/layout review and human approval remain required before wiring.
The earlier proposed decision below is retained for context and is superseded
where it restricts controls to five fallbacks.



## Authority and rationale

Operator direction, 2026-11-03: resolve known defects and defects discovered during
execution, then focus on sensitivity analysis and a parameterization harness that
supports end-user controls. This replaces legacy-agreement-driven candidate search
as the Roads program's closure authority. The original WEPP:Roads comparison is a
limited model reference, not measured truth. Pursuing narrow agreement can introduce
regressions that outweigh a benchmark recovery.

Historical experiments, thresholds and failed classifications remain unchanged.
Their agreement statistics characterize compatibility; neither 100% agreement nor
the historical 95% overall/90% stratum gates determine current closure. This does
not convert rejected candidates into accepted defaults or waive correctness checks.

## Defect adjudication

Maintain a bounded issue register with evidence, affected consumers, consequence,
reproduction, disposition and regression validation. Resolve confirmed defects in
the supported workflow before closure; newly discovered defects enter the same
process. Repair shared failure classes across confirmed consumers. Unsupported
contexts require an explicit scope disposition, not silent dismissal.

Distinguish implementation defects, numerical/accounting findings, legacy-model
differences and missing empirical validation. A legacy mismatch alone is not a
defect. A numerical flag must receive a source-supported disposition; do not hide
it, relax a bound to obtain a pass, or assume that a printed-output discrepancy
proves an internal conservation defect. Unexplained findings remain open.

Preserve input units and identity, layer/OFE ownership, runtime activation,
calendar coverage, finite/valid outputs, baseline isolation and applicable
water/sediment accounting contracts. Use actual generated artifacts and bounded
full-workflow evidence; job success and unit tests alone are insufficient.

## Sensitivity and parameterization harness

After defect disposition for a proposed experiment's affected path, declare a
bounded sensitivity study using the supported engine and canonical builders.
Do not repeat rejected universal sweeps merely to improve legacy agreement.

For each proposed control retain meaning, units, road/fill/buffer applicability,
source support, baseline, candidate range and native consumer. Distinguish hard
validity limits, studied ranges and empirically calibrated ranges. Unknown bounds
remain unknown; a tested range is not automatically a recommendation.

Verify requested -> effective -> emitted -> native-consumed values, including
aliases, clipping, inactive controls and cross-role coupling. Begin with small
paired contrasts and include passing, high-export and underpredicting contexts;
then examine justified interactions and scope coverage. State what each batch can
decide before running it. Expected directional responses are hypotheses to test,
not grounds for forcing monotonic behavior.

Retain water and sediment responses, event/annual results, role-boundary fluxes,
numerical findings and regression effects alongside legacy differences. Pin inputs,
engine, sidecars, declared sample membership and complete successful/failed outputs.
Separate engine, source-data and parameter changes. Reuse existing harnesses and
production builders; do not introduce a second parameter formula implementation.

A useful sensitivity result can support an interpretable control without proving
field calibration or establishing a new default. Changing defaults, formulas or
parameterization policy still requires its own evidence, ADR and applicable review.
Preserve the six reserved materials; declare any new use before execution, and
never describe adaptively inspected cases as independent validation.

## Contractual default and project authorities

The [repository baseline contract](roads-parameterization-baseline-contract.md)
specifies soil/management values and selection/adjustment rules. The
[project/view contract](roads-settings-contract.md) specifies authoritative
`roads.nodb` state, retained baseline material, override precedence and lifecycle.
These are separate contractual layers: changing repository defaults cannot
silently change a bound project. A dedicated parameterization view exposes both
source arithmetic and actual emitted values. Neither UI constants nor study
fixtures are alternate production default authorities.

## End-user workflow and closure

Prepare a concrete field specification and static layout after sensitivity evidence
supports the proposed controls. Preserve the explicit human approval gate for both
before implementing the view or production persistence/application wiring.

The eventual workflow provides edit/save/reload/reset without manual CSV editing,
clear units and applicability, default/custom status and honest range labels.
Specify versioning, provenance, validation, stale-result handling, adoption,
fork/restore and permissions in canonical contracts before implementation. Verify
browser -> saved state -> prepared inputs -> native execution -> Roads reports
under production-equivalent boundaries. Existing projects remain reproducible.

Closure requires disposition of known findings with confirmed supported-path defects
resolved, a reproducible sensitivity/parameterization harness, documented limits,
and the approved, wired, validated user workflow. It does not require universal
agreement with legacy predictions or exhaustive discovery of all possible defects.
Scientific uncertainty remains visible. No deployment, new-default adoption or
real-project regeneration is authorized by this change of program direction.
