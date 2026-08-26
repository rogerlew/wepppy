# Phase 2A Pilot Exit Report

**Disposition**: FULL CENSUS WITHHELD

Selection `3b5778d7c9171311` covers Hills 106, 84, 8, 35, 31, 91, 85, 62.
All 64 mutation trials completed; 697 event rows across 61 trials screened as candidates.

## Automatic Exit Criteria

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `mutation_manifest_realization_terminal_and_input_diff` | **PASS** | mutation-terminal-summary.json |
| 2 | `outer_join_preserves_absence_distinct_from_zero` | **PASS** | mutation-terminal-summary.json and event-pairs.parquet |
| 3 | `real_observer_no_surplus_packet_validates` | **PASS** | event-packets/topanga-h031-1980-day045-no-surplus.json |
| 4 | `unmutated_hillslopes_unchanged` | **PASS** | routing-validation-summary.json and external route manifests |
| 5 | `offpath_channels_unchanged` | **FAIL** | routing-trial-validation.csv |
| 6 | `every_changed_channel_record_is_on_declared_path` | **FAIL** | routing-trial-validation.csv and routing-topology.json |
| 7 | `hydrograph_timestamps_nonnegative_flow_and_volume_consistency` | **FAIL** | hydrograph-validation-summary.json and h106-1986-day046-volume-check.csv |
| 8 | `known_positive_adaptive_bracket_and_frozen_replay` | **PASS** | candidate-adjudication.json and h106-1986-day046-adaptive-bracket.csv |
| 9 | `storage_partitioning_and_retention_acceptable` | **PASS** | storage-runtime-projection.json and artifact-storage-*.json |
| 10 | `incomplete_hdrive_replays_stopped_and_dispositioned` | **PASS** | candidate-adjudication.json |

## Disposition

The full census remains withheld because criteria 5, 6, 7 failed.

Smallest remediation:

1. Remove shared/event-global channel transmission-loss effects so a one-hillslope HBP mutation cannot alter sibling off-path channels.
2. Make interval chan.out discharge integrate to the same authoritative outflow volume reported by chanwb.out, then rerun routing criteria 5-7.

## Cost Projection

The 1,120-trial initial census projects to 261.7 GB of raw daily routing output and 46.1 sequential routing hours (5.8 hours at eight workers).
