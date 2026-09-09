# ADR-0060: Pseudo-BARC256 fixture derivation

Status: accepted for test artifacts, 2026-09-09.

## Context and decision

The owner requested pseudo-BARC256 maps from the two existing Arizona dNBR
fixtures. Those source samples encode dNBR × 1000. Derive byte samples as
`floor(clip((source + 275) / 5, 0, 255))`, retaining source grid and finite valid
support. Use an internal mask rather than reserving valid byte values for NoData.
No production model or source fixture changes; no field-validated SBS claim.

## Rationale and alternatives

The [USGS BAER description](https://burnseverity.cr.usgs.gov/baer/index.php/background-products-applications)
provides the inverse scale relation. Explicit clipping prevents byte wraparound;
floor defines deterministic quantization. Per-image min/max stretching would
lose the common BARC scale. Reserving 0 or 255 would discard valid observations.
Four-class severity thresholds and field calibration are outside this request.

## Decision provenance

- Venue: repository task conversation, 2026-09-09, America/Los_Angeles.
- Participants: requesting repository owner and Codex.
- Owner: requesting user, authorizing pseudo-BARC256 fixture creation.
- Implementer: Codex; quantization/mask choices are documented engineering choices.
- Change: two new derived test rasters; no previous conversion is replaced.

## Evidence, risk and rollback

[Fixture derivation and checks](../../tests/nodb/mods/fixtures/postfire_debris_flow_dnbr/pseudo_barc256/README.md)
record source/output hashes, clipping and readback validation. These derivatives
share dNBR ancestry and cannot count as independent observed SBS evidence.
Remove the derivatives to roll back; originals remain unchanged.
