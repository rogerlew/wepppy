# M0 fixture and QA checkpoint

Status: evidence preparation only; M0 and final QA acceptance remain open.
Reviewer: independent `qa_checkpoint` agent. Source revision:
`05e3450fa7d3b24572e65161100670ae542a6ea8`, plus the task-worktree planning files.

## Retained evidence

[`red_fixtures/generate_fixtures.py`](red_fixtures/generate_fixtures.py) generates
46 fixtures totaling 34,949 bytes. The
[manifest](red_fixtures/manifest.json) binds every filename to its size, SHA-256,
intended class, expected result, and semantic oracle where available.
[The execution receipt](20261116_fixture_receipt.json) records the exact command
and supported claims. A second generation produced a byte-identical manifest;
every file's hash/size was checked and no accepted/rejected outcome pair shares
the same bytes.

The existing PyArrow 16.1.0 and Shapely 2.0.4 installations generate trusted
test input only. They are not proposed production parsers or dependencies.
Valid Arrow-writer outputs were read back for exact WKB, `field_id`, and
metadata. A tiny hand-written compact-protocol **writer** constructs malformed
headers without allocating their declared sizes. Its ordinary control was read
back independently with PyArrow. No hostile fixture was decoded in this review.

There is no candidate CLI manifest at
`wepppy/microservices/shape_converter/rust/geoparquet_parser_cli/Cargo.toml`.
Consequently all candidate acceptance assertions are **NOT_RUN**. This corpus is
retained pre-implementation input evidence, not a passing security test, actual
red/green result, or permission to leave the M0 gate.

## File coverage

| Class | Retained fixtures | Assertion to execute against candidate |
| --- | --- | --- |
| GeoParquet 1.0/1.1, uncompressed/Snappy | `polygon-*`, `line-*`, `multipolygon-*`, `point-*` | Decode exact geometry, scalar fields and feature order against corresponding GeoJSON; missing CRS means CRS84 |
| Dictionary encoding | `dictionary-control.parquet` | Two identical geometries remain two features with distinct field IDs |
| Independent ordinary writer | `manual-plain-control.parquet` | Decode polygon; receiving AgFields rejects missing `field_id` |
| Missing/malformed GeoParquet metadata | `missing-geo`, `version-unsupported`, `encoding-geoarrow`, `primary-column-missing` | Stable metadata/schema rejection before workflow mutation |
| CRS ambiguity | `crs-null`, `crs-invalid` | Explicit null/invalid CRS rejection; never assume WGS84 |
| Schema/extension | `nested-properties`, `schema-columns`, `extension-metadata` | Reject nested properties, 66 root columns, and explicit extension marker |
| Unsupported codec/encoding | `codec-gzip`, `encoding-delta` | Reject before decoding excluded codec or delta allocation |
| WKB | `wkb-truncated`, `wkb-count-bomb`, `wkb-nesting` | Bounded length/count/depth rejection before geometry traversal |
| Nonfinite values | `coordinates-nonfinite`, `property-nonfinite` | Reject instead of serializing NaN/Infinity |
| Magic/footer | `magic-head`, `magic-tail`, `footer-truncated`, `footer-size-bomb`, `footer-list-bomb` | Reject exact magic/footer/count contradictions without large allocation |
| External resources/encryption | `external-path`, `encrypted-pare`, `encrypted-column`, `encrypted-footer-metadata` | Reject even when plaintext data accompanies encryption metadata; never open referenced path |
| Page allocation | `page-declared-expansion`, `page-value-count`, `dictionary-value-count`, `page-header-string-bomb` | Enforce header/count budgets before upstream reader allocation |
| Actual/declared decompression mismatch | `page-actual-expansion` | Reject 32 KiB actual body paired with declared four bytes |
| All-null parser rejection | `null-geometry` | Parser rejects: no finite observed bounds can be computed |
| Workflow geometry rejection | `mixed-polygon-point`, point and line controls | Batch/AgFields/Omni reject unsupported replacements while preserving accepted resources |

Names in the table omit `.parquet` unless a wildcard or explicit extension is
shown. Dictionary-count and header-bomb files deliberately include more than
one malformed condition; acceptance must demonstrate the intended early budget
check, not merely any eventual decoder error.

## Required dynamic and missing coverage

The following remain required before milestone acceptance; static files do not
prove these controls:

- Add deterministic Shapefile ZIP counterparts and exact three-format equality.
  No Shapefile fixture dependency was added during this checkpoint.
- Add valid explicit projected CRS and offline reprojection oracles, scalar
  null/boolean/string/integer/float edges, empty collections, multiple row groups,
  and saved legacy project cases. Add a mixed-null/non-null parser control:
  optional nulls are preserved when a non-null geometry provides finite bounds;
  receiving workflows still reject unsupported null geometries.
- Exercise each numeric threshold at limit and limit plus one using generated
  temporary inputs. Current small declarations establish mutation classes, not
  near-limit memory, CPU, decoded-byte, scratch, or output acceptance.
- Add actual expansion beyond the configured page ceiling; current 32 KiB case
  proves a declaration mismatch class only. Test valid compressed controls at
  the same boundary to exclude false-positive rejection.
- Exercise extension metadata nested in a serialized `ARROW:schema`, not just
  the explicit key retained here. Do not deserialize extension objects.
- For timeout, repeated cancellation, descendants, concurrency, cleanup,
  readiness and provenance, use the actual launcher/process boundary. Verify
  process disappearance, reclaimed scratch, release of admission ownership,
  and a succeeding recovery control in the same exact image.
- For converter bypass, send malformed or semantically unsupported canonical
  GeoJSON directly to receiving endpoints and assert no accepted-resource
  replacement or queue mutation.
- Test absent, present-empty, populated, malformed, and saved legacy workflow
  states. Snapshot accepted artifact bytes and NoDb values before failed
  replacement; reload and read generated downstream artifacts afterward.
- Run actual browser/auth/CSRF/API paths, archive/restore, and visible artifact
  readback under production-equivalent identities. Mocked converter success
  cannot satisfy these gates.

## Findings and disposition

`COR-M0-02` (Medium, resolved): PyArrow 16.1's `store_schema=False` discarded
all key/value metadata, including `geo`. Initial metadata-negative fixtures were
byte-identical to the purported valid control. The generator now preserves
writer metadata, removes only the exact known `ARROW:schema` key/value from the
trusted footer, and independently asserts exact metadata equality. Its encoded
sequence must occur exactly once; writer layout drift fails explicitly.

Independent `source_review` re-review verified all 46 hashes/sizes, eight valid
controls against their complete GeoJSON geometry/property oracles, and seven
metadata-negative controls against their intended differences. It confirmed
zero contradictory outcomes for identical bytes. Reviewed manifest SHA-256:
`3cb63c002cd9a5e9eda9c0210ad3f0aa679621e21177cf84a01709cc9378885f`.

The final contract clarified that all-null input rejects at the parser because
finite observed bounds are required. The generator and manifest now give
`null-geometry.parquet` that explicit expectation. All 46 fixture byte hashes
and sizes remain unchanged; regeneration, exact metadata readback and manifest
hash checks passed again. Current manifest SHA-256:
`30f5ea40ae35fcd41843ca29e0d75671f32fc8e5a80a024b1965709daeac7bd5`.
The prior independent review hash above is retained as historical evidence;
this expectation-only amendment adds no candidate/runtime test claim.

Residual risk: the hand-built malformed fixtures need candidate execution and
assertions at their intended enforcement points. Their construction and hashes
alone do not validate hostile parsing. Final QA must review the implemented
tests after primary correctness review, against the same committed revision
and exact image used by the other reviewers. The separately reported security
review interruption is not replaced by this fixture-preparation work.
