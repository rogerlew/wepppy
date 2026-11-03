# ADR-0135: Expose supported Roads fallback controls

## Operator clarification: default settings and user overrides

Operator direction, 2026-11-03: this is a default settings harness, not a
calibration harness. Users need explicit key-driver overrides to increase/decrease
Roads runoff and sediment toward observations or user expectations. The former
five-fallback-only proposal is insufficient and requires revision; its reviews
apply only to that earlier scope. Lack of field calibration does not exclude useful
controls. Preserve source values, explicit override precedence and honest response
limits. See the authoritative [requirement and rationale](../schemas/roads-settings-contract.md#operator-clarification-default-settings-and-user-overrides).
Specification/layout review and human approval remain required before wiring.
The earlier proposed decision below is retained for context and is superseded
where it restricts controls to five fallbacks.



Status: **proposed; human specification/layout approval absent; implementation pending**.

## Decision provenance

- Decision venue: Roads revised completion handoff, 2026-11-03 UTC; operator
  environment America/Los_Angeles.
- Participants present: operator and Codex through the task conversation; independent
  agent reviews are required and have not been substituted for operator approval.
- Decision owner: operator Roger Lew; the precise proposal remains unapproved.
- Proposed implementer: Codex after the explicit human gate and contract checkpoint.
- Authorized work now: defect disposition, bounded sensitivity, proposed specification
  and static layout. No production view/persistence/application wiring yet.

## Proposed decision and exact delta

Expose five already supported Roads fallback settings in the existing panel:
surface, traffic, road width, fill length and fill slope. Preserve their existing
baseline values gravel, low, 4 m, 30 m and 10%, validation limits, template assembly,
feature precedence and role applicability. Add Edit/Save/Cancel/Reset with Reset
changing the draft until Save, and additive provenance metadata/visible artifact
records. Exact fields, protocol, metadata and state behavior are specified in the
[proposed Roads settings contract](../schemas/roads-settings-contract.md).

Before, the panel exposes surface/traffic fallbacks but users must use the API or
input attributes for width/fill defaults. After approval and implementation, users
can edit these five supported fallbacks without CSV/native edits and inspect which
current-run segments used them. No formula, threshold, unit conversion, soil policy,
scientific default or native executable changes. Existing ordinary API numeric strings, aliases and omitted-key partial updates
remain supported. The proposal deliberately rejects JSON booleans previously
accepted as numeric values and JSON null previously normalized to traffic `none`;
the string `none` stays valid. This bounded validation delta requires approval.
Present malformed saved values become an explicit repair state rather than silent
normalization; absent legacy keys keep existing defaults. Unrelated settings remain
unchanged. Study values are not calibrated ranges.

The panel's existing Apply Attribute Mapping also submits surface/traffic fallbacks.
Separate it prospectively: mapping action submits mapping only; settings Save submits
the five settings only. Dirty drafts block adjacent upload/mapping/Prepare/Run actions
with inline Save/Cancel guidance; passive refresh cannot replace a draft. Matching
Save responses own hydration, and Cancel reloads without mutation. This reviewed
client behavior change prevents accidental Save/discard while preserving the existing
server API and normal clean-state workflow.

## Rationale and alternatives

The revised operator objective prioritizes defects and useful controls over fitting
legacy-model agreement. Interpretable existing geometry and management choices have
known production consumers and can be characterized with bounded paired studies.
Width affects modeled footprint; traffic and surface are coupled packages. Showing
those limitations and actual source precedence makes the controls understandable.

Reject direct Ki/Kr knobs as the first UI merely because they are easy to vary;
reject blanket attribute override because it changes working source authority;
reject buffer override because routing-derived geometry is not a free default.
Texture/profile fragments remain inspectable but are not selected as initial fields.
Profile fragments are not surface armor. Generated `erosion_road_cap` remains a
conditioned research baseline, not a policy adoption hidden behind the new editor.
A new endpoint, queue, generic optimizer or CSV table adds unnecessary scope.

## Evidence and acceptance

Source and native consumer evidence:
[control inventory](../work-packages/20261029_roads_parameterization_program/artifacts/revised-control-inventory.md).
Workflow reasoning and layout:
[design draft](../work-packages/20261029_roads_parameterization_program/artifacts/revised-workflow-design-draft.md) and
[static layout](../work-packages/20261029_roads_parameterization_program/artifacts/revised-settings-layout-draft.html).
Current [adjudication authority](../schemas/roads-parameterization-adjudication-contract.md)
separates numerical correctness, legacy comparison and empirical uncertainty.

The [profile study](../work-packages/20261029_roads_parameterization_program/artifacts/revised-sensitivity-results.md)
and [project study](../work-packages/20261029_roads_parameterization_program/artifacts/revised-project-sensitivity-results.md)
retain the completed bounded contrasts and their source-supported limitations.
The [scientific review](../work-packages/20261029_roads_parameterization_program/artifacts/revised-sensitivity-science-review.md)
assesses control characterization separately from default adoption. Width changes
footprint, fill responses differ on total versus density scales, and traffic
rankings are not universally monotonic. This ADR does not establish field
calibration or completed-run browser/RQ validation. Before implementation require independent contract/science/security/UX
reviews, disposition, explicit human approval of both specification and layout,
and the standalone contract-first ancestor. After implementation require the actual
browser-to-native-to-report chain, invalid/readonly/reset/reload/fork/restore states,
source/role diagnostics, output isolation and production-equivalent boundaries.

## Risks and rollback

Fallback changes may affect no segments when feature values win; expose actual
completed-run usage rather than silently overriding features. Width changes area;
report both absolute and area-normalized study outputs. Validity bounds do not imply
robustness or empirical calibration. Additive metadata cannot certify historical
outputs or silently migrate projects. Preserve old payload keys and values.

If implementation violates source precedence, baseline isolation, atomic validation
or lifecycle readiness, withhold release and repair or revert the editor change.
Keep diagnostics and history. An undeployed rollback removes the new view/wiring
without changing scientific defaults or overwriting projects. Deployment and any
new-default adoption require separate authorization.
