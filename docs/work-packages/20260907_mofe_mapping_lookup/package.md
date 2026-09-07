# Mapping-aware MOFE burn management lookup

**Status**: Open (2026-09-07)  
**Timezone**: UTC

## Overview

On wepp1, aliquot-shoji job 041e93ae-3103-4bb4-b4dc-f00471a87d30 failed at 2026-09-07 16:50:40 UTC with InvalidManagementKey: 106 is an invalid key. The run selects c3s-disturbed, but the multiple overland-flow-element (MOFE) remapper writes disturbed.json identifiers. Fix this confirmed lookup path without changing severity calculations or vegetation eligibility.

## Scope and success criteria

Resolve forest, shrub, and grass severity targets using the existing effective-map lookup. Preserve deferred rebuilds, no-SBS no-op, and legacy disturbed mappings. Verify C3S and custom identifiers, explicit invalid-map failure, and downstream management generation. Production deployment and live-run recovery are separate operator actions.

## Security and parameterization

Security impact: none; no new attack surface, paths, queue wiring, or execution boundary. Dedicated security review: not required. Parameterization change: no; no defaults, formulas, thresholds, units, or fallback heuristics change. ADR: not required.

## Stakeholders

The requesting operator owns behavior approval; Codex implements and independent reviewers check contracts and correctness.

## Compatibility and regression plan

Keep persisted field names and nesting unchanged. Only generated OFE management identifiers change to match the active map. Existing correct disturbed assignments remain identical. Rebuild landuse from baseline after rollout; do not translate already-burned persisted keys manually. Test real map loading and management serialization into temporary wepp/runs artifacts, plus remapping with absent SBS, empty assignments, complete maps, and incomplete maps.

## Hardening hypothesis and observation

Using the effective map eliminates this InvalidManagementKey signature for supported maps. Health evidence is successful remapping, summary resolution, and generated management files. Danger signals are wrong vegetation/severity, changed legacy outputs, and unexpected map rejection. Use recurrence-triggered observation on the next C3S MOFE rebuild; no temporary mitigation or scheduled monitoring is introduced.

## Related work

Existing custom-mapping recovery work in ../20260424_landuse_legacy_flask_state_route_removal/ is historical context; reuse the current get_mapping_dict authority, not its old recovery implementation. Current governance: ../../standards/contract-first-change-standard.md and ../../standards/hardening-lifecycle-standard.md.

## Deliverables

See tracker.md and prompts/active/mofe_mapping_lookup_execplan.md. Contract: ../../schemas/disturbed-mofe-mapping-contract.md.
