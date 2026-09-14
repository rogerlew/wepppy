# ADR-0067: Production M3 soil usability and spatial weighting

Status: Accepted replacement; original strict-material proposal rejected by owner  
Date: 2026-09-14

## Context

The offline thickness helper is not a production eligibility contract.
The development basin's legacy H horizons are unavailable under strict material
classification on 99.798094363342% of its cells. Its cache lacks survey lineage
tables, and no prepared original THICK window was found for the basin.
NRCS NSSH 618.38(C)(2) explicitly recognizes legacy H layers retained in
approved map units. Rejecting H as unknown material missed that source evidence.
Collection lineage still cannot be inferred from a cache filename.

## Decision

Preserve offline defaults and shared WEPP soil builders. Advance recorded-depth
production policy: include O/A/E/B/C, documented H1/H2/etc. and weathered Cr;
exclude explicit terminal hard R. Use representative bottom minus top, retaining
reported thickness disagreement as an audit warning. Do not reject a whole
profile solely for H/Cr or a separate thickness-field disagreement. Require
positive finite intervals starting at zero with no unexplained gaps/overlap;
reject conflicting IDs and soil below an intervening R layer. No extrapolation
or inferred zero from missing records.

For legacy combination pairs only, count one interval for exactly
two distinct IDs with identical positive endpoints and identical combination
master/name containing `/` or ` and `, independently admitted material, and
no conflicting stable IDs. Retain both originals and a pair diagnostic. Other
overlap stays unavailable. Current NRCS guidance instead calls for contiguous
representative intervals; this is bounded support for older records, not blanket
union aggregation. Analytical examples have passed; authentic pair evidence
remains absent in this panel.

Normalize a map-unit thickness by its positive usable component weight.
Individual invalid percentages reject the estimate; totals above 100 alone do
not. Record raw known, usable, nonsoil and rejected weights separately from
spatial coverage. Select a usable primary estimate per cell, then aligned
original THICK. Use nearest-neighbor alignment and inches × 2.54 for THICK cm.
Compute the spatial mean over common valid cells without another component
fraction weight. Missing thickness never becomes zero.
All-R primary components remain nonsoil and ineligible. Finite zero THICK
remains eligible under its nonnegative-value contract. Source lineage queries
describe current associations, not the historical vintage of cached horizons;
retain content hashes and retrieval metadata without fabricating a survey version.

## Decision provenance

Decision Venue: repository execution conversation, 2026-09-14, America/Los_Angeles.  
Participants Present: repository owner and Codex.  
Decision Owner: repository owner; replacement approved by “proceed” after the explicit ratification question.  
Implementer: Codex; no implementation performed.

The owner requested package execution, rejected strict soil rules as non-viable,
then authorized investigating a depth-based replacement. This explicitly rejects
the original strict-material proposal. After the replacement assessment and
review corrections, the owner approved adopting the replacement by “proceed.”
Common support, source priority and builder isolation remain accepted. THICK
acquisition remains unapproved. Runtime schemas and prepared-input boundaries
are specified in the production scientific integration runtime contract.

## Change summary and rationale

Offline v1 rejects totals above 100 and weights spatial means by component
valid fraction. Proposed production means normalize usable weights within
each map unit and then weight its pixels equally, consistent with ADR-0066's
binary spatial support. Two equal-area pixels at 100 and 200 cm produce
150 cm even if their usable component weights differ. This avoids treating
unlocated component proportions as spatial holes.
H-only eligibility restores all 4,311,420 development basin cells. The broader
depth policy additionally recovers recorded profiles in the frozen panel;
its Cr and endpoint choices are not needed simply to make this basin pass.

## Alternatives considered

Strict material eligibility was rejected by the owner. H-only is a narrower
alternative, sufficient for the development basin, but continues discarding
complete recorded Cr profiles in the fixture panel. Cr is soft bedrock:
its inclusion is an explicit cumulative-material proxy choice, not a soil
taxonomy claim. All-layer inclusion most closely follows the retained original
THICK arithmetic, but including hard R increases some az_ponderosa map-unit
means by up to 155.059 cm relative to depth-no-R. Keep it as sensitivity evidence.
Taking every interval union would conceal unexplained overlap. Fractional
spatial weighting remains a different estimator from binary cell support.

## Evidence

- [Source inventory](../work-packages/20260914_staley_m3_integration/artifacts/source_inventory.md)
- [Replacement evidence and experiment](../work-packages/20260914_staley_m3_integration/artifacts/depth_policy_assessment.md)
- [Exact proposal and numerical examples](../work-packages/20260914_staley_m3_integration/artifacts/source_delivery_proposal.md)
- [Current production contract](../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m3.md)
- [Offline thickness contract](../../wepppy/nodb/mods/postfire_debris_flow/docs/m3_soil_thickness.md)

## Risks and rollback

Recorded profiles may be limited by observation depth and can include weathered
material; these estimates are not calibrated evidence of mobilizable sediment.
Source lineage and historical-version limits must remain explicit before
claiming primary SSURGO contribution.
Keep model/source/policy identities explicit and preserve old output semantics.
Any eventual rollback changes future execution, never rewrites accepted results.

## Implementation notes

This decision does not authorize acquisition or alone complete the contract checkpoint.
Resolve source delivery and remaining schema/snapshot details, synchronize
canonical contracts, obtain independent reviews and commit their checkpoint
before runtime edits. Soil nonregression and real RQ/WBT validation remain due.
