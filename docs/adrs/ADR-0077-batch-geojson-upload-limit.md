# ADR-0077: Batch GeoJSON upload limit

Status: Accepted
Date: 2026-09-30

## Context and Decision

The operator requested increasing the batch GeoJSON upload limit from 10 MiB to
30 MiB (31,457,280 bytes). Set that default in the upload handler, Flask
configuration, and batch page defaults. Preserve `BATCH_GEOJSON_MAX_MB` overrides.
The canonical limit is recorded in the batch row of the
[upload endpoint contract](../schemas/upload-endpoint-contract.md).

## Decision Provenance

Decision Venue: Codex chat, 2026-09-30, America/Los_Angeles; time not recorded.
Participants Present: requesting operator and Codex.
Decision Owner: requesting operator.
Implementer: Codex.

## Rationale and Alternatives

Allow larger batch watershed collections at the operator's requested bound.
Retaining 10 MiB would not satisfy the request; an unlimited cap was not requested.

## Evidence and Validation

Operator instruction: "increase geojson limit to 30 MiB please".
Validate literal defaults and documentation by direct readback; no executable
logic or tests change. SBS remains 100 MiB.

## Risk and Rollback

Larger accepted files can increase parsing memory and processing time.
Revert these defaults to 10 MiB if the increased cap causes resource problems.
Existing deployment overrides still take precedence; activation requires the
updated application configuration and code to be loaded.
