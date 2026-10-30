# ADR-0110: Consistent generated-soil boundary at 200 mm

Status: Accepted for generated inputs; upload preservation unchanged.  
Date: 2026-10-29

## Context

The Roads study demonstrated that equivalent split/unsplit sandy-loam horizons
produce different native results. Disturbed preparation inserts a 200 mm boundary;
ordinary raw generation and other writers do not consistently do so. The user
requests consistent insertion across WEPPpy/wepppyo3 soil writers.

## Decision

Normalize every generated soil profile at its serialization boundary, inserting
an identical-material horizon break at 200 mm when required. Preserve physical
properties, depth and restrictive data. Keep explicit upload preservation and
immutable source files unchanged. Fail before publication if insertion exceeds
the native ten-layer capacity, including layers already inserted by conversion. Use the shared Python operation where input files
are owned; Rust output Parquet and anisotropy-return APIs are not input writers.

## Decision provenance

Decision Venue: this development conversation, 2026-10-29, America/Los_Angeles.  
Participants Present: requesting operator and Codex.  
Decision Owner: requesting operator, via explicit instruction to proceed with
consistent insertion across all soil writers.  
Implementer: Codex.

Existing uploaded-soil preservation remains unchanged. On 2026-10-29, the
operator additionally requested durable ADR discoverability and a user-facing
explanation in the soil-file specification; that documentation adds no new
parameterization behavior.

## Change summary and rationale

Before: generated profiles could cross 200 mm without a boundary depending on
which writer was used. After: generated writers apply the same idempotent split.
The verified `wepp_261026` reader, source commit
`b73e93b19a724d1991d341d38a18d11e742231bd`, adjusts source-horizon conductivity
while constructing its top 200 mm calculation layer. When a source horizon
crosses that boundary, its adjusted value can persist into the deeper portion.
An explicit boundary gives the deeper material a separate source row, preserving
its supplied conductivity there. The source explanation and native replay are
retained in the evidence below; this finding is scoped to the verified release.

The common normalization operation is
`wepppy.wepp.soils.horizon_boundary.ensure_200mm_boundary`. Python input writers,
including channel-soil writers, apply it before opening their destination.
Future input-soil writers must follow the shared contract; Rust model-output
writers must not synthesize input horizons into reported model outputs.

No supplied conductivity or erosion coefficients change. Source-object layer count is not
mutated by serialization; emitted layer count matches the emitted rows.

## Alternatives considered

Removing boundaries to reduce sediment was rejected: it hides native sensitivity.
Changing native WEPP was rejected for this package: the operator requested writer
consistency. Duplicating a Rust input writer was rejected because Python owns
confirmed input serialization. Silent layer merging/truncation was rejected
because it changes or discards material properties.

## Evidence

- [Prepared-soil study mechanism](../work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/mechanism.md).
- [Contract](../schemas/soil-horizon-boundary-contract.md).
- [Native replay and regression validation](../work-packages/20261029_soil_200mm_boundary_consistency/artifacts/validation.md).
- [User-facing soil specification](../../wepppy/weppcloud/routes/usersum/input-file-specifications/soil-file.spec.md#weppcloud-normalization-at-200-mm).
- [Implementation package](../work-packages/20261029_soil_200mm_boundary_consistency/package.md).

## Risks and rollback

New results can differ materially from earlier unsplit runs; boundary consistency
is not a promise of lower sediment or field accuracy. Preserve original run
artifacts and record new consumed-input identities. Revert the code change if
properties, restrictive records or upload preservation regress; do not rewrite
historical generated files. No deployment or binary replacement is included.
