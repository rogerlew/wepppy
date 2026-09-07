# Correctness and User-Experience Review - MOFE Mapping Lookup

## Metadata

- **Package**: `docs/work-packages/20260907_mofe_mapping_lookup/`
- **Reviewer**: Independent agent `/root/contract_review_a`
- **Date**: 2026-09-07
- **Scope reviewed**: `wepppy/nodb/mods/disturbed/disturbed.py` and `tests/nodb/mods/disturbed/test_landuse_remap.py`; actual map resolver and MOFE management writer dependencies.
- **Commit context**: Working diff after checkpoint `38789cb4c`, whose parent is starting revision `83ae87a2e6`. Checkpoint ancestry verified; implementation is not in that checkpoint.
- **Canonical contracts**: `docs/schemas/disturbed-mofe-mapping-contract.md`, Mapping resolution, State and persistence, and Rationale and recovery; unchanged `docs/schemas/nodb-persistence-concurrency-contract.md`.
- **Related artifacts**: `2026-09-07_contract_decision.md`. No security boundary changed.

## User Outcome

- **User goal**: Build multiple-OFE landuse with burn targets belonging to the effective management mapping.
- **Success**: C3S forest targets become 406/418/405; legacy disturbed targets remain 106/118/105; custom targets resolve semantically without numeric assumptions.
- **Failures reaching the user**: Existing lookup assertions for missing semantic classes and existing custom-map load errors remain explicit failures.
- **Partial state**: Lookup failures occur before assignment mutation or management rebuilding. Later raster, persistence, and management failures retain existing behavior. Failed historical builds require rebuilding baseline landuse, as the recovery contract states.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| SBS absent, explicit custom map missing | Yes | No lookup, mutation, or rebuild | `test_mofe_no_sbs_does_not_load_missing_map` |
| Complete map, empty OFE assignments | Yes | Empty assignments; existing rebuild scheduling | `test_mofe_empty_assignments_remain_empty` |
| C3S or complete custom map, populated assignments | Yes | Semantic targets and usable management output | `test_mofe_effective_mapping_and_generated_managements` |
| Legacy disturbed map | Yes | Same identifiers and vegetation behavior | Same parameterized test |
| Incomplete, malformed, or missing explicit custom map with SBS | No | Explicit failure before assignment mutation | `test_mofe_invalid_mapping_fails_before_assignment_mutation` |
| Previously burned assignments from failed build | Recovery state | Rebuild baseline before retry | Canonical recovery guidance; no live repair claimed |

## Input Matrix

The new populated-map test crosses three mapping sources with both rebuild modes. Within each case it covers forest, shrub, short grass, and tall grass at severities 131/132/133; non-burn 130 and an ineligible class remain unchanged. Both burn flags are false, proving the preserved MOFE behavior. Existing MOFE tests also exercise the prior default behavior. This is bounded coverage, not an exhaustive cross-product of all forest variants, duplicate classes, or hostile filesystem states; their existing helper and validation behavior is unchanged.

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| No SBS | Expected optional absence | No-op | State and persistence contract |
| Missing required burn semantic class | Exceptional configuration | Existing assertion propagates | Mapping resolution contract |
| Malformed or missing explicit custom mapping | Exceptional configuration | `LanduseCustomMappingError` propagates | State and persistence contract; actual effective-map loader exercised |
| Later management generation failure | Exceptional | Existing failed job behavior | Rebuild flow and persistence contract unchanged |

## Review Checks

- [x] Canonical intent and operator scope are recorded in the checkpoint; implementation conforms to that scope.
- [x] Absent, empty, populated, legacy, and malformed states have separate evidence or explicitly bounded coverage.
- [x] Input/flag combinations are distinguished from stored state.
- [x] No safety or persistence boundary is changed; existing locks and refresh/rebuild paths remain intact.
- [x] Real `Landuse.get_mapping_dict`, effective custom-map resolution, semantic lookup, and management summary resolution are exercised rather than mocked.
- [x] Real MOFE synthesis, two-year expansion, serialization, and rereading exercise generated files under `wepp/runs/`; cover-value assertions compare all 12 generated OFEs with their resolved source managements.
- [x] The fake landuse isolates lock orchestration and rebuild call counts; it does not replace the mapping failure boundary. Tests do not claim full production orchestration or live recovery evidence.
- [x] No security controls are changed; valid custom maps and invalid configurations retain existing loader behavior.
- [x] Recovery guidance requires baseline regeneration, avoiding unsupported remapping of already-burned IDs.
- [x] Existing severity, eligibility, flags, schema, and timing remain compatible.
- [x] Coverage claims name their dimensions and limitations.

## Findings

No correctness defects identified in the reviewed implementation or tests. The patch uses the existing shared lookup after the no-SBS return and before mutation, replacing only the nine fixed target identifiers. First-entry duplicate selection and incomplete-map validation remain owned by the unchanged helper.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**: High 0; Medium 0; Low 0.
- **Release recommendation**: `ship-with-conditions`: complete the in-progress full repository suite. Parent execution evidence confirms 18 focused tests passed in 1.17 seconds, including the final generated cover-value assertions, and the related disturbed/MOFE suite finished with 110 passed and 20 skipped. This reviewer inspected code and tests but did not independently rerun them. Deployment and recovery on wepp1 are not validated by this artifact.
- **Reviewer sign-off**: `/root/contract_review_a`, 2026-09-07.

## Post-review validation disposition

2026-09-07 19:45 UTC, Codex executor: the remaining validation condition is satisfied. Final focused generated-cover assertions passed (18 tests); the full repository suite passed with 7662 passed and 72 skipped, exit 0. This records execution evidence without changing the independent review. Production deployment and live recovery remain separate.
