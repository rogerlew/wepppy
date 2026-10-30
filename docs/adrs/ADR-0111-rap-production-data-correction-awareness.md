# ADR-0111: Retain RAP production correction notice for future impact assessment

Status: Accepted (reference record; no runtime change)  
Date: 2026-10-29

## Context

The Rangeland Analysis Platform (RAP) published a [production-data correction notice](https://rangelands.app/changelog/2024-2025-production-update/) on September 28, 2026 (reviewed October 29, 2026). It reports a processing error affecting 2024, 2025, and provisional 2026 production data. Effects varied geographically; annual forb/grass production was generally too high and perennial forb/grass production too low. Corrected data replaced these Earth Engine assets:

- `projects/rap-data-365417/assets/npp-partitioned-16day-v3`
- `projects/rap-data-365417/assets/npp-partitioned-16day-v3-provisional`
- `projects/rap-data-365417/assets/npp-partitioned-v3`
- `projects/rap-data-365417/assets/npp-partitioned-v3-masked`

The notice's comparison figures use incorrect minus corrected values. It does not identify vegetation-cover products as affected.

## Decision

Retain this notice as a discoverable reference for future RAP production/NPP integration, provenance questions, or discrepancies involving the affected years. Defer remediation until a WEPPpy consumer or retained artifact is shown to use affected data.

This record authorizes no code, parameterization, cache invalidation, or existing-run rebuild. It does not establish that any current WEPPcloud run is affected.

## Decision provenance

Repository operator/Codex conversation, 2026-10-29: the operator supplied the notice and requested an ADR in case it becomes relevant. The accepted decision is to retain the evidence and a conditional assessment path.

## Rationale and local evidence

Replacing data under existing asset names creates a reproducibility concern: an asset identifier alone cannot distinguish retained earlier values from corrected values. This is an inference from the upstream replacement notice, not a measured WEPPpy discrepancy.

The inspected [RAP download helper](../../wepppy/landcover/rap/rangeland_analysis_platform.py) uses `rap-vegetation-cover` GeoTIFFs. A search of repository Python sources found no literal references to `npp-partitioned` or `rap-data-365417`. These limited checks do not audit deployed services, external data mirrors, or historical run artifacts. The existing [RAP_TS cover normalization decision](ADR-0010-rap-ts-management-cover-fraction-normalization.md) addresses a separate cover-processing concern.

## Alternatives considered

- Immediate refresh or rebuild: deferred because there is no confirmed affected consumer or run.
- Treat every RAP product as affected: unsupported by the notice and the inspected cover-data path.
- Keep only a conversation bookmark: rejected because future investigations need a durable, searchable reference.

## Consequences and implementation notes

Revisit this ADR when adding a production/NPP consumer or investigating a matching data discrepancy. At that point:

1. Identify the exact product, asset, years, acquisition date, local cache/mirror, and downstream consumers. Distinguish cover from production and provisional from finalized data.
2. Preserve available original inputs and record retrieval metadata and content digests for comparisons. Do not infer correction status solely from an unchanged asset name or a local file timestamp.
3. Compare retained and corrected inputs over the relevant geography; verify propagation into generated model inputs and consumed outputs before claiming an impact or successful repair.
4. Document the affected-run scope, compatibility/regression plan, and operator-approved remediation separately. Keep historical outputs attributable to their original inputs.

## Risk and rollback notes

This documentation-only decision introduces no runtime rollback requirement. The unresolved risk is unknown historical provenance if an affected production dataset is discovered later. No affected-run inventory or quantitative downstream impact has been established.

Review is event-driven by the triggers above; no scheduled implementation is implied.
