# Vector upload normalization

**Status**: Closed 2026-11-17

**Started**: 2026-11-16 23:22 UTC

**Starting revision**: `05e3450fa7d3b24572e65161100670ae542a6ea8`

## Overview

Added Shapefile ZIP and GeoParquet upload support to the four first-party
WEPPcloud workflows that currently accept user-facing GeoJSON. Both binary
formats are normalized to canonical GeoJSON through the existing
shape-converter service boundary before the workflow's current validation and
persistence logic runs.

GeoParquet follows the established Rust CLI pattern, but uses a separate sibling
binary named `geoparquet_parser_cli`. It must not be added as a mode of
`shape_parser_cli`, parsed inside WEPPcloud or rq-engine, or parsed with PyArrow
on the hostile-input path. The CLI is a bounded short-lived process with strict
data-only JSON IPC, process-group termination, resource limits, provenance, and
runtime readiness checks.

## User-Facing Upload Inventory

| Workflow | Current entry points | Existing contract | Required normalized geometry |
| --- | --- | --- | --- |
| Roads | `roads_pure.htm`, `controllers_js/roads.js`, `routes/nodb_api/roads_bp.py`, `nodb/mods/roads/roads.py` | GeoJSON, 10 MiB | LineString or MultiLineString |
| AgFields | `ag_fields_pure.htm`, `controllers_js/ag_fields.js`, `rq_engine/ag_fields_routes.py`, `nodb/mods/ag_fields/ag_fields.py` | GeoJSON/JSON, 10 MiB | Polygonal features with `field_id` |
| Omni contrasts | Omni control/template, `controllers_js/omni.js`, `rq_engine/omni_routes.py`, `omni_contrast_build_service.py` | GeoJSON/JSON, 100 MiB | User-defined polygons |
| Batch Runner | Batch control/template, controller, `upload_batch_runner_routes.py`, `WatershedCollection`, `BatchRunner` | GeoJSON/JSON, 30 MiB | Polygon/MultiPolygon only (operator approved 2026-11-16; implemented) |

The canonical endpoint inventory remains
[`docs/schemas/upload-endpoint-contract.md`](../../schemas/upload-endpoint-contract.md).
M0 must verify this table against the source before changing any contract.

## Objectives

- Let users select GeoJSON, a single-dataset Shapefile ZIP, or a single
  GeoParquet file at each listed workflow.
- Normalize Shapefile ZIP and GeoParquet to bounded canonical GeoJSON in the
  shape-converter service, then reuse each workflow's existing semantic checks.
- Define a hostile-file GeoParquet admission and parser contract before code.
- Preserve endpoint authentication, CSRF, run scope, size limits, geometry
  requirements, error contracts, persistence, and downstream artifact behavior.
- Prove semantic readback from source file through normalized GeoJSON and the
  workflow's real consumed artifact.

## Scope

### Included

- The four user-facing workflows in the inventory and their browser controls,
  receiving routes, converter integration, tests, and user documentation.
- The shape-converter API/specification changes needed to accept GeoParquet
  input and return canonical GeoJSON.
- A separate service-local Rust `geoparquet_parser_cli`, its dependency
  evaluation, locked build, provenance, readiness, and hostile-input tests.
- Shapefile ZIP input through the already hardened `shape_parser_cli` path.
- Canonical upload and normalization contracts, resource-limit ADR, correctness
  review, dedicated security review, QA/code review, and rollout evidence.

### Explicitly Out of Scope

- The culvert API and every culvert upload or ingestion path.
- D-Tale support or changes; it is explicitly deferred.
- GeoPackage, KML, CSV, Arrow IPC/Feather, Parquet datasets/directories, remote
  URLs, cloud object stores, or arbitrary GDAL/OGR formats.
- Raw GeoParquet parsing in WEPPcloud, NoDb, rq-engine, or a browser.
- Reusing `shape_parser_cli` as a multi-format mode switch.
- A new service, queue, datastore, daemon, protocol, deployment topology,
  privilege, host mount, or network access from the parser.
- Production deployment or image publication without separate authorization.

## Accepted Architecture and Contract Direction

- `shape_parser_cli` remains Shapefile-specific.
- `geoparquet_parser_cli` is a sibling Rust binary in the existing hardened
  shape-converter container and uses the same launcher lifecycle pattern.
- The service normalizes accepted binary input to canonical WGS84 GeoJSON.
  Receiving workflows still enforce their own geometry and attribute contracts;
  converter success is not authorization to bypass endpoint validation.
- Initial GeoParquet support targets specification versions 1.0 and 1.1, one
  file, one root primary geometry column, WKB geometry encoding, and scalar
  JSON-compatible properties. Broader encodings or nested values require a new
  contract decision and evidence.
- Missing CRS follows GeoParquet's CRS84 meaning. Explicit `crs: null` is
  unknown and must not silently become WGS84 for these workflows. Reprojection
  must be offline and must not fetch grids or other network resources.

## GeoParquet Security Contract Gate

Before implementation, the canonical contract must define and test:

- exact `.parquet`/`.geoparquet` file admission, `PAR1` magic, and rejection of
  encrypted `PARE`, column encryption, external `file_path` references,
  directories, URLs, and multi-file datasets;
- private request scratch staging, least-privilege permissions, cleanup, and no
  raw-file persistence beyond the request;
- byte limits for upload, footer/Thrift metadata, schema depth/columns, row
  groups/rows, declared and decoded data, geometry WKB, normalized output, and
  scratch use;
- CPU, memory, file descriptor, process, wall-time, cancellation, concurrency,
  and process-group drain behavior;
- an explicit compression-codec allowlist and rejection of unsupported codecs;
- bounded and schema-validated GeoParquet metadata, no trusted Arrow extension
  deserialization, and no executable/object-capable IPC;
- full geometry decode with recomputed types and bounds, finite coordinates,
  per-geometry and aggregate vertex limits, and workflow-specific validation;
- stable bounded errors, content hashes, parser/binary provenance, and no
  leakage of scratch paths or attacker metadata into logs;
- malformed footer, metadata expansion, decompression expansion, external-path,
  encryption, unsupported-codec, WKB/vertex, nonfinite-coordinate, CRS,
  timeout, cancellation, cleanup, and concurrent-load adversarial fixtures.

## Complexity Budget

- **Reuse**: existing shape-converter service/container, hardened subprocess
  launcher, JSON response contract, scratch cleanup, provenance/readiness, and
  current workflow validators.
- **Permitted addition**: one sibling Rust CLI and the smallest reviewed Parquet,
  WKB, CRS, and resource-limit crate graph that passes the dependency standard.
- **Not permitted**: PyArrow on hostile input, a general-purpose format bridge,
  shared parser state, silent fallback, additional infrastructure, or weakened
  receiving-endpoint validation.
- **Escalation rule**: stop and amend this package with retained failure evidence
  before adding any mechanism outside this budget.

## Parameterization ADR Gate

- **Parameterization change present**: yes. GeoParquet requires new limits for
  rows, row groups, schema/metadata, decoded bytes, geometry/vertex counts,
  output, concurrency, and execution resources.
- **ADR required**: yes, before implementation.
- **Evidence required**: representative valid files, bounded hostile fixtures,
  service/container envelope measurements, existing upload ceilings, and an
  explicit rationale for every new default or threshold.

## Dependency Evaluation Gate

No Rust Parquet/Arrow, WKB, CRS, or related crate may be adopted until the
precedent, capability, ownership, license, unsafe-code, transitive dependency,
malformed-input, build provenance, vulnerability, maintenance, size, and
performance gates in the dependency-evaluation standard are recorded in
[`artifacts/20261116_dependency_evaluation.md`](artifacts/20261116_dependency_evaluation.md).

## Generated Artifact Validation Gate

This package transforms an uploaded artifact and feeds the result to four
artifact-consuming workflows. Completion requires direct semantic readback of:

1. the exact uploaded fixture and its declared intent;
2. the converter's bounded canonical GeoJSON output;
3. the exact normalized payload consumed by the receiving workflow;
4. reloaded persisted state and downstream generated run artifacts; and
5. the user-visible success/error result.

Hashes, file existence, job success, and converter metadata alone are
insufficient. The current highest supported completion claim is `diagnosed`.

## Security and Review Gates

**Security impact**: high. The service accepts attacker-controlled binary columnar
files, compressed encodings, metadata, and WKB. A dedicated independent security
review is mandatory. Package closeout also requires independent correctness,
code, QA, and operations reviews against the same revision and exact image.

## Success Criteria

- [x] Canonical contracts and the parameterization ADR are ratified before code.
- [x] Dependency evaluation accepts the exact locked Rust crate graph.
- [x] All four workflows accept valid GeoJSON, Shapefile ZIP, and GeoParquet
      while preserving existing auth, CSRF, size, geometry, attribute, and
      persistence behavior.
- [x] Invalid and hostile files fail with bounded actionable errors and leave no
      partial workflow state or request scratch residue.
- [x] The exact image proves parser provenance, enforced resource limits,
      cancellation/process-group drainage, cleanup, recovery, and no network
      dependency.
- [x] Direct semantic readback proves equivalence across all three input formats
      for each workflow, including downstream artifacts.
- [x] Scoped Python/frontend/Rust/Compose checks and independent review gates
      pass with no unresolved High or Medium findings.
- [x] Documentation distinguishes local validation, environment validation,
      rollout, and production resolution; rollout remains separately authorized.

## Local completion

M0-M5 are complete on `codex/vector-upload-normalization`. Final source is
`4da014fee8a3c80643fc542165d6c529a85532ad`; executable source is `f96483108`.
The [final acceptance](artifacts/20261117_final_acceptance.md) and
[machine-readable receipt](artifacts/20261117_final_validation.json) retain
source-qualified broad and affected tests, exact image/artifact readback,
independent reviews and rollout boundaries. Ordered continuations cover the full
suite after a reviewed Roads provenance correction and isolated-checkout build
prerequisites. The last continuation passed 854 cases; every earlier failed node
passes at the final source. Historical Roads results remain explicitly stale.

Public/team sharing includes retained evidence, as recorded in the canonical
[sharing contract](../../schemas/vector-upload-normalization-contract.md#sharing-copies-and-existing-workspace-resets).
No remote integration, publication or production deployment occurred. Production
activation remains a separately authorized operator task using the retained
readiness/canary/recovery procedure.
## References

- [Shape-converter specification](../../../wepppy/microservices/shape_converter/docs/specification.md)
- [Shape-converter security conformance package](../20261113_shape_converter_security_conformance/package.md)
- [Upload endpoint contract](../../schemas/upload-endpoint-contract.md)
- [Contract-first change standard](../../standards/contract-first-change-standard.md)
- [Dependency evaluation standard](../../standards/dependency-evaluation-standard.md)
- [Generated artifact validation standard](../../standards/generated-artifact-validation-standard.md)
