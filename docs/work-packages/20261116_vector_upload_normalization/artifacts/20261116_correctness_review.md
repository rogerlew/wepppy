# Correctness checkpoint review - Vector upload normalization

Status: M0 checkpoint reviewed; implementation approval withheld pending the
findings and independent gates below. This is not final M5 sign-off.

## Review identity and scope

Reviewer: independent `source_review` agent, 2026-11-16. Starting runtime revision:
`05e3450fa7d3b24572e65161100670ae542a6ea8`. No candidate image exists for this
review. Read-only source comparison found the reviewed shape-converter and four
receiving workflows identical between task and shared checkouts.

Reviewed draft SHA-256 values:

| Artifact | SHA-256 |
| --- | --- |
| `docs/schemas/vector-upload-normalization-contract.md` | `f118d4ec09c7b225f5e07d0556c4a63804e14e400625fbd9ca3a3b3047b1b9c4` |
| `docs/adrs/ADR-0145-geoparquet-upload-resource-bounds.md` | `3c311055f716d6be071577969157b7c594d2e3955bf9c625d633d7d686c5d126` |
| `artifacts/20261116_threat_matrix.md` | `7962c830db3027add749ddd54d89ab427a7e17a4d350cb3e5f55d42fc7a18f75` |
| `artifacts/red_fixtures/manifest.json` after QA repair | `3cb63c002cd9a5e9eda9c0210ad3f0aa679621e21177cf84a01709cc9378885f` |

The source inventory and acceptance states are retained in
`20261116_source_checkpoint.md` and `20261116_correctness_state_matrix.md`.
This review covers valid behavior, compatibility, observable artifacts and
contract completeness. It does not replace the independently required security
or exact locked dependency review, including the interrupted security lane.

## Findings and disposition

| ID | Severity | Finding and concrete evidence | Required closure | Disposition |
| --- | --- | --- | --- | --- |
| COR-M0-01 | High | Raw-input deletion conflicts with artifact-observability requirements; the draft Lifecycle section requires deletion while Publication says the exception is unapproved. Hashes cannot recover an uploaded original. | Record operator disposition naming exact removed files, reason, retained evidence and archive limitation in canonical contract before adoption. | Open; operator question pending, accurately identified by threat matrix |
| COR-M0-02 | High | Initial fixture generator used PyArrow 16.1 `store_schema=False`, dropping all metadata. Seven purported rejection fixtures had identical bytes/hash to a valid control. | Preserve `geo` metadata, remove only known `ARROW:schema`, independently verify metadata and semantic controls. | Resolved by QA generator repair and independent readback below |
| COR-M0-03 | Medium | Canonical upload-endpoint matrix still restricts all consumers to GeoJSON; shape-converter specification still says ZIP-only. New vector draft cannot silently override them. | Amend both affected specifications in the standalone checkpoint ancestor, mark conformance pending, cross-link the vector profile. | Open at reviewed hashes |
| COR-M0-04 | Medium | Initial receipt inventory omitted concrete paths and normalized failed candidates. Amended Publication section names all receipt paths and retains `candidate.geojson` with hash/size when receiving validation rejects successful normalization. | Prove visible browse/download and archive/restore, and no automatic reuse of rejected candidates. | Resolved at contract level; execution evidence pending |
| COR-M0-05 | Medium | Initial category list lacked explicit status mapping. Amended Transport table maps validation 400, caps 413, unavailable 503 and existing `request_timeout` 408 without changing outer envelopes. | Implement adapters and regression assertions matching the accepted table. | Resolved at contract level; implementation evidence pending |
| COR-M0-06 | Medium | Initial profile omitted page/null policy. Amended profile permits DataPage V1/V2 and dictionary pages with ordering constraints, preserves optional null rows, rejects empty/all-null datasets, and requires receivers to reject any null. | Align fixture expected outcomes with this resolved policy; add V2, mixed-null and empty controls and candidate validation in M1. | Resolved at contract level; fixture/implementation coverage remains required |
| COR-M0-07 | Medium | ADR does not yet have representative/near-ceiling valid measurements. Aggregate page byte accounting must include dictionaries/all columns and groups, and admission must span both parsers. Independent maxima do not establish the overlap envelope. | Retain measured evaluation before numeric acceptance; clarify shared aggregate accounting and preserve independent image qualification in M2. | Open; operations review identifies same constraint |
| COR-M0-08 | Medium | Inherited `crs.py:230` uses ordinary `Transformer.from_crs`; offline mode alone does not prove rejection of fallback transformations. Amended CRS section explicitly rejects ballpark and missing-best-operation grids. | Implement and verify projected, invalid and missing-grid cases with no network. | Resolved at contract level; implementation/test obligation remains |

The original Batch geometry contract question is resolved by the operator's
Polygon/MultiPolygon decision; no further geometry question is needed. Apply
that gate to new upload admission, leaving shared saved-project reload alone.
The draft now correctly acknowledges missing polygon admission checks in current
AgFields/Omni and explicitly requires them. The explicit internal EPSG:4326
handoff also resolves the design ambiguity around Roads/AgFields CRS inference;
execution coverage is still required.

## Fixture repair verification

A read-only command under `/workdir/wepppy/.venv/bin/python`, executed with task
worktree cwd, verified all 46 manifest record sizes and SHA-256 values, zero
contradictory hashes, eight valid geometry/property controls against their
GeoJSON semantic oracles, and seven metadata rejection controls against the
intended metadata changes. It exited 0 and reported:

```json
{"manifest_records":46,"hash_size_pass":true,"contradictory_hashes":0,"semantic_controls_passed":8,"metadata_negative_controls_passed":7}
```

Only trusted writer output and structurally ordinary metadata controls were read
with the existing PyArrow/Shapely oracle. No hostile page/list/count fixture was
sent through this Python path. The generator's exact known-metadata-list
replacement is guarded by unique occurrence and independent metadata-equality
readback. This proves fixture intent after repair; it does not prove candidate
Rust rejection, resource bounds or end-to-end workflow behavior.

## Required green evidence

- All three formats must preserve geometry, properties, feature order and
  multipart identity through receiving validation, persisted reload and actual
  generated artifacts, with distinct feature labels/IDs in equivalence fixtures.
- Roads must retain line-only behavior and explicit normalized CRS; parse
  `roads/roads.uploaded.geojson` and generated monotonic segments.
- AgFields must enforce polygon and literal `field_id` semantics before replacing
  canonical geometry/attribute files; duplicate-ID warnings remain compatible.
  Read back `fields.WGS.geojson`, `rotation_schedule.parquet` and field raster.
- Both Omni paths must reject normalization/receiving failures before
  `parse_inputs` alters saved state; compare prior bytes/path/settings. Parse
  `build_report.ndjson` selections and confirm run versus dry-run enqueue behavior.
- Batch must reject unsupported new geometries before replacement/registration,
  reload existing projects unchanged, and parse each generated
  `dem/target_watershed.geojson` with original properties and added runid/index.
- Browser/auth/CSRF/error/retry/reload paths, visible artifact download and actual
  archive/restore must be exercised under intended identities. Mocked converter
  success, file existence and successful jobs cannot stand in for these checks.

## Verdict

The revised normalization direction is coherent and the initial red-fixture
metadata defect is repaired. M0 remains unapproved: explicit observability
ratification, affected canonical amendments, resource/dependency evidence and independent security review remain required.
No runtime implementation, dependency adoption, image qualification, rollout,
publication or deployment approval is given by this review.
