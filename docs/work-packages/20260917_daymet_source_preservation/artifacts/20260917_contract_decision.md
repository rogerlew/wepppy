# Contract decision

Starting revision: 49781866e0570e6352fc927b6066b0f845c28a9a.

Operator approval: user stated source Daymet parquet should be read-only and requested “make the fix please” after the proposed preserve-source/separate-conversion/CSV approach. Commit authority persists from earlier commit/push authorization in this session.

Applicable authority: climate-parquet-lineage-contract, ADR-0006 (radiation artifact placement), artifact-observability standard. No change to NoDb persistence, climate scaling, job wiring, radiation formula or numerical conversion.

Normative delta: downstream single-location/interpolated CLI preparation never overwrites acquired Daymet parquet; precipitation/temperature retain labeled physical units. PRN conversion uses a separate working copy. Radiation transformations retain existing CSV evidence rather than rewriting source parquet. This amends ADR-0006's provenance-column placement, not its physical model.

Compatibility/regression plan: retain original columns/values; no automatic migration of existing mislabeled artifacts. Legacy extra radiation columns remain readable and unmodified. New source acquisitions replace data only through normal explicit build lifecycle. Separate CLI-derived parquet lineage remains unchanged. Test actual parquet bytes and generated PRN/CLI, including failures, and run real CLIGEN in an isolated artifact directory.

State matrix: absent source -> acquisition writes it once; valid populated source -> downstream reads only; legacy provenance-bearing source -> existing reader behavior, unchanged bytes; malformed/missing required columns -> existing explicit failure, no recovery by rewriting; empty inputs -> existing behavior (no new acceptance/fallback). Input matrix: single/interpolated, bounded/over-bound radiation, wind enabled/disabled, successful/failed downstream build. No new permission controls or exception boundary.

Security impact low. Classification: precipitation labels were a defect; radiation provenance placement is an explicitly authorized contract amendment. Independent reviews and ancestor commit required before implementation. Conformance pending.
