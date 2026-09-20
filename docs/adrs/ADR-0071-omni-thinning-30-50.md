# ADR-0071: Add 30% and 50% Omni thinning canopy

Status: accepted; implementation and generated-input conformance locally
validated 2026-09-20. Deployment remains separate.

## Context and decision

Add eight static management variants: canopy 30/50 crossed with ground cover
75/85/90/93. Copy matching 40% sources and change only cancov to 0.30/0.50.
Keep existing files/IDs/classes intact and preserve UI default 40%. Ground,
LAI, soil parameters, units, formulas and eligibility are unchanged.

## Provenance

Venue: user/Codex workspace conversation, 2026-09-20 America/Los_Angeles;
exact message time unavailable. Participants: requesting operator and Codex.
Decision owner: requesting operator; implementer: Codex. Operator narrowed the
original 30–75% expansion to 30/50 and authorized scaffolding and executing this
work package after accepting the additive compatibility approach.

## Rationale and alternatives

Two new choices need eight assets, not forty. A shared template would change
loading, saved-state and MOFE boundaries unnecessarily. Existing canopy overrides
also scale LAI and therefore do not preserve the static-file parameterization.
Do not remove legacy files or migrate saved runs.

## Evidence, risk and rollback

[Canonical contract](../ui-docs/contracts/omni-thinning-contract.md).
[Work package](../work-packages/20260920_omni_thinning_30_50/package.md).
Validate all new choices and generated management inputs against source files.
Risks: key collision, unintended canopy default change, omitted regional mapping.
Rollback selector availability if necessary; retain assets referenced by saved
runs. Deployment and fresh model-result validation are outside delivery scope.
