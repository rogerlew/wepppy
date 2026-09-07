# Disturbed MOFE management mapping contract

## Scope and authority

This contract governs management identifiers assigned by Disturbed.remap_mofe_landuse. The operator approved mapping-aware lookup on 2026-09-07 after the aliquot-shoji incident. Repository implementation conforms as of 2026-09-07 (implementation commit 1ea4b8d52); production rollout is separate.

## Mapping resolution

For an SBS-present MOFE remap, resolve burn targets by DisturbedClass from Landuse.get_mapping_dict through the existing get_disturbed_key_lookup. This includes the effective custom map when configured. Do not embed identifiers from disturbed.json or apply numeric offsets.

Severity classes 131, 132, and 133 select low, moderate, and high severity targets respectively for forest, shrub, and grass. Preserve current MOFE eligibility: unburned forest classes accepted by is_unburned_forest_disturbed_class, shrub, and short/tall grass. Eligible MOFE shrubs and grass continue to remap regardless of burn_shrubs/burn_grass; this correction does not change that flag behavior, severity determination, or unburned/ineligible assignments.

The existing lookup requires forest, shrub, and grass low/moderate/high semantic classes. Preserve its first-entry behavior for duplicate semantic classes and explicit failure for incomplete maps. Resolve this lookup before mutating OFE assignments. Do not substitute legacy IDs on lookup failure.

## State and persistence

Absent SBS remains a no-op without requiring a usable mapping. Empty OFE assignments with a complete mapping remain empty. Populated supported maps and legacy disturbed maps retain their semantic behavior. Malformed map loading errors propagate through existing error contracts.

Keep domlc_mofe_d field names and nesting unchanged. Keep existing NoDb locks, refresh, and immediate/deferred management rebuild behavior; docs/schemas/nodb-persistence-concurrency-contract.md remains authoritative for persistence.

## Rationale and recovery

Management IDs belong to their mapping namespace: C3S forest low severity is 406, while disturbed forest low severity is 106. Semantic lookup prevents invalid or incorrectly interpreted cross-map IDs and also supports custom maps without numeric assumptions. Preserve vegetation behavior to avoid changing model parameterization in a lookup correction.

After rollout, rebuild failed landuse from baseline so all derived assignments and management artifacts are regenerated. Replaying remapping against previously burned keys is not a supported repair.
