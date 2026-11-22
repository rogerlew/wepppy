# ADR-0157: Pack large WEPP interchange files across source boundaries

Status: Accepted for implementation

Date: 2026-11-22

## Context

The 47,582-hillslope diagonal-intersection run exceeded the native writer's 32,767 physical row groups per file. The old sink flushed at each parser chunk. Both AgFields validation and per-hillslope daily reads depended on that layout.

## Decision

Keep the existing Parquet paths, scientific schema and source order. Identify hillslopes and sub-fields by their data columns. Report the physical group count from the closed footer. Keep neighboring sources together so a daily reader can select a compact range of rows for each identity.

For known bulk lists above 32,767 sources, target groups of `ceil(source_count / 16,384)` nonempty chunks. This reserves space for automatic splits on long sources. For every sink, increase the minimum chunks per manual flush to 2, 4 and 8 at 16,384, 24,576 and 28,672 physical groups respectively. At 30,720 physical groups, let the library's row cap and final close determine the remaining boundaries. The limits govern storage and leave the model calculations intact.

## Rationale and alternatives

Retaining a single file keeps existing consumers and publication behavior compatible. Sharding would change paths and completeness rules across readers. Filling every group to the library maximum from the first source would discard the cheap single-hillslope statistics lookup for ordinary runs. Keeping the old flush rule would reproduce the same failure on retry.

## Provenance and validation

The WEPPpy operator commissioned this incident package in the Codex session on 2026-11-22, Pacific time. Codex selected and implemented the storage thresholds. Independent correctness and QA reviews checked the packed files, their identities and daily totals. [Failure-class assessment](../work-packages/20261122_interchange_row_groups/artifacts/failure-class.md) and [validation results](../work-packages/20261122_interchange_row_groups/artifacts/validation.md).

## Consequences and rollback

Physical groups can contain several sources and large sources can span several groups. External files with interleaved IDs can require a wider scan. The underlying per-file group ceiling still applies. Monitor source identity, actual footer counts and daily totals on the first complete production replay. Rollback restores the prior paired WEPPpy and native releases. Preserve raw files for regeneration because the old AgFields validator expects the earlier layout.
