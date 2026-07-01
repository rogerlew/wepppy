# Architecture Decision Records (ADRs)

This directory stores durable decision records for project-level decisions across WEPPpy/WEPPcloud, including but not limited to feature maturity, release governance, architecture, operations, and policy.

## Purpose

ADRs answer: why did we make this decision at that time?

Use ADRs when a decision is likely to be questioned later, affects user-visible behavior, or changes release/operational governance.

Parameterization changes are explicitly in scope and require ADRs. See:

- `docs/standards/parameterization-adr-standard.md`
- `docs/adrs/ADR-template.md`

## Scope

ADRs in this directory may cover:

- feature maturity and release decisions,
- visibility and role-gating policy,
- architecture and contract decisions,
- operational/reliability governance,
- deprecation and migration decisions,
- grant/stakeholder-driven release constraints.

## File Naming

Use a stable, sortable naming convention:

- `ADR-0001-<slug>.md`, `ADR-0002-<slug>.md`, etc.
- Use `docs/adrs/ADR-template.md` as the starting template for new records.

## Recommended Sections

Each ADR should normally include:

- title,
- status,
- date,
- context,
- decision,
- rationale,
- alternatives considered,
- consequences,
- implementation notes,
- review/expiration date when relevant.

## ADR Index

- `ADR-0001`: [Time-Limited Publication Embargo for OMNI Contrasts](ADR-0001-time-limited-publication-embargo-for-omni-contrasts.md) (Accepted, 2026-05-22)
- `ADR-0002`: [Require ADRs for Parameterization Changes](ADR-0002-parameterization-change-adr-requirement.md) (Accepted, 2026-05-22)
- `ADR-0003`: [RUSLE `observed_rap` Surface-Rock Partition for `C`](ADR-0003-rusle-observed-rap-surface-rock-partition.md) (Accepted, 2026-05-27)
- `ADR-0004`: [RUSLE `scenario_sbs` Surface-Rock Partition for `C`](ADR-0004-rusle-scenario-sbs-surface-rock-partition.md) (Accepted, 2026-05-27)
- `ADR-0005`: [RUSLE `K` Conservative Second-Stage Gap Fill](ADR-0005-rusle-k-second-stage-gap-fill.md) (Accepted, 2026-05-27)
- `ADR-0006`: [Observed-Daymet Radiation TOA Normalization](ADR-0006-observed-daymet-radiation-toa-normalization.md) (Accepted, 2026-06-06)
- `ADR-0007`: [Project-Local SSURGO SQLite Cache](ADR-0007-project-local-ssurgo-sqlite-cache.md) (Accepted, 2026-06-19)
- `ADR-0008`: [SSURGO Reclaimed Soil Restrictive Layer Fallback](ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md) (Accepted, 2026-06-22)
- `ADR-0009`: [Deciduous and Mixed Forest Managements](ADR-0009-deciduous-mixed-forest-managements.md) (Accepted, 2026-06-26)
- `ADR-0010`: [RAP_TS Management Cover Fraction Normalization](ADR-0010-rap-ts-management-cover-fraction-normalization.md) (Accepted, 2026-06-26)
- `ADR-0011`: [Geneva NOAA Rounded-Zero Intensity Row Normalization](ADR-0011-geneva-noaa-rounded-zero-intensity-row-normalization.md) (Accepted, 2026-06-30)
