# ADR-0074: Add 60% and 70% Omni thinning canopy; retain 65%

Status: accepted 2026-09-25; implementation conformance pending.

## Context and decision

Expand canopy choices from 30/40/50/65 to 30/40/50/60/65/70%. Add eight static
files for 60/70 crossed with ground 75/85/90/93. Copy matching 40% files and change
only cancov to 0.60/0.70. Preserve 40% default, ground values, LAI, soil parameters,
formulas, units, eligibility and every old ID/file. Keep 65% visible and supported.

## Provenance

Venue: user/Codex workspace conversation, 2026-09-25 America/Los_Angeles; exact
message time unavailable. Participants: requesting operator and Codex. Decision
owner: requesting operator; implementer: Codex. Operator requested scaffolding
and execution using the 30/50 package as recipe, explicitly noting 65% removal
would break old projects. Scope includes necessary checkpoint commits.

## Rationale and alternatives

60/70 fill out useful remaining-canopy options. Retaining 65% protects existing
projects without migration. Static additive files reuse the proven recipe;
shared-template refactoring would broaden this bounded change. Existing canopy
override APIs may scale LAI and are unsuitable for canopy-only asset creation.

## Evidence and rollback

[Contract](../ui-docs/contracts/omni-thinning-contract.md) and
[package](../work-packages/20260925_omni_thinning_60_70/package.md).
Check generated source/single/MOFE/prepared managements, soil prefixes, catalogs,
legacy byte/record preservation, UI defaults/hydration and archive restoration.
Risks are ID collision, omitted catalog and unintended source/default changes.
Before any new selections are saved, selector availability may be rolled back.
Afterward, any rollback must preserve saved 60%/70% hydration and serialization,
as well as referenced assets/IDs; simply removing selector options is unsafe.
No deployment or fresh model-output claim is part of local delivery.
