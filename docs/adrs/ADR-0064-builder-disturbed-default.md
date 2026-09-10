# ADR-0064: Disturbed is standard for Config Builder projects

## Status

Accepted by operator, 2026-09-10; implementation pending.

## Context and decision

Builder previously serialized an empty module list when no optional modules were
selected. That omitted Disturbed and the Soil Burn Severity upload control.
Every new Builder project now includes Disturbed as an internal dependency,
independent of locale, resolution, backend or optional model selection.
Use its normal landuse and soil adjustment workflow, including its existing
behavior when no SBS map is uploaded. Upload remains optional.

## Decision provenance

Venue: this development conversation, 2026-09-10 (America/Los_Angeles).
Participants: project operator and Codex. Decision owner: project operator.
Implementer: Codex. Owner instruction: “config builder projects should always
have disturbed”; owner continued after explicit explanation that this means
normal behavior including soil adjustments, with no SBS-only guard.

## Parameterization delta and rationale

Before: Builder's default module list omitted the Disturbed event workflow.
After: that existing workflow is active by default. This can change generated
landuse/soil model inputs relative to old Builder projects. No numerical routine,
lookup-table contents, soil version (including existing shared sol_ver=7778) or
burn-severity threshold is changed. Select existing compatible landuse mappings:
NLCD/EMAPR → disturbed; CORINE → eu-disturbed; Australian landuse → au-disturbed;
C3S → c3s-disturbed (already selected). Plain mappings lack required burn classes,
so retaining them would fail even a no-map landuse build. SBS is ordinary project
input and should not require selecting another model to expose its upload.

## Alternatives

A template-only change leaves the upload controller absent. An SBS-only event
guard would create different Disturbed behavior for Builder projects; the owner
explicitly chose normal Disturbed behavior instead. Neither is implemented.

## Compatibility, risk and rollback

Preserve source selections and historical config bytes. New configs include the
required dependency in effective modules; config updates accept exact historical
or new effective lists and preserve existing values. Explicit existing-project
repair preserves controller/map state and uses normal NoDb locks, except the
explicit fair-division Landuse mapping repair from absent/default to disturbed. Only the
operator-named fair-division is repaired here. Other old projects require scoped
repair, not automatic GET mutation or a silent fleet upgrade.

Generated inputs may differ because normal Disturbed is now enabled. Existing
artifacts are not rebuilt automatically. Reverting the creation default affects
future creates only; existing project rollback needs explicit scoped state
restoration and regeneration of any subsequently built artifacts.

## Evidence

[Work package](../work-packages/20260910_builder_sbs/package.md) and the
[canonical contract](../schemas/project-owned-config-contract.md#builder-soil-burn-severity-support-2026-09-10)
track focused tests, controller initialization and browser upload evidence.
