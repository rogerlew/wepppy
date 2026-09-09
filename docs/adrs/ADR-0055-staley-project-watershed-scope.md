# ADR-0055: Staley assessment uses the project watershed

## Status and decision provenance

Accepted domain scope; implementation pending. Decision venue: user/Codex
repository conversation, recorded 2026-09-09 04:18 UTC (2026-09-08 Pacific).
Participants: repository owner (user) and Codex. Decision owner: user.
Documentation implementer: Codex; numerical/runtime implementation not started.

## Decision and rationale

Use the existing WBT project watershed and its existing user-selected,
canonically resolved outlet as the single Staley assessment domain. Users should
manually isolate burned basins they suspect may be at risk when defining their
projects. Preserve the full delineated contributing area for basin predictors;
the fire perimeter and observed-data support do not replace that domain.

This replaces an unratified roadmap proposal to assess each channel's upstream
catchment plus the project outlet. There is no existing production behavior or
persisted schema to migrate. WEPPcloud already owns outlet selection and
delineation; Staley does not require another set of nested catchments.
See the [canonical scope](../../wepppy/nodb/mods/postfire_debris_flow/specification.md#project-watershed-assessment-scope).

## Alternatives considered

Per-channel/nested assessments could add spatial detail, but the owner chose
the project watershed for initial delivery. They require separate future scope
approval. Automated isolation of burned areas is not requested. Clipping to
burned pixels would change contributing-area predictors and is not equivalent
to selecting a basin outlet. Multi-outlet offline tests remain useful evidence
without imposing a multi-catchment production interface.

## Evidence, risks, and rollback

The owner explicitly directed: use the watershed defined by the project and
guide users to manually isolate suspected burned basins. The
[implementation roadmap](../../wepppy/nodb/mods/postfire_debris_flow/implementation_roadmap.md)
and first assessment/engine package implement this planning correction.

An overly broad basin can conceal tributary-scale variation. Preserve intended-
use and study-domain guidance; a basin result is not the probability of any
debris flow anywhere in a larger landscape or a runout estimate. Revisit scope
through a new accepted contract if users need internal spatial assessments.
No production migration or deployment rollback is required for this doc change.
