# Security Review - Staley M3 Soils

## Metadata

- **Package**: `docs/work-packages/20260908_staley_m3_soils/`
- **Reviewer**: independent `security_reviewer` agent.
- **Date**: 2026-09-09 UTC.
- **Context**: uncommitted changes on `master`, base
  `e8bef992ecb4bccf57d3a40ceab49e2e4b21ee97`.
- **Scope**: [soil_thickness.py](../../../../wepppy/nodb/mods/postfire_debris_flow/soil_thickness.py),
  [run_study.py](run_study.py), [acquire_sources.py](acquire_sources.py), the
  [frozen fixtures](../../../../tests/nodb/mods/fixtures/postfire_debris_flow_soils/),
  and their input/output contracts. The original acquisition probes in
  `/tmp/staley-m3-soils-study/` were also inspected; the repository recipe is
  the durable acquisition surface.
- **Related artifacts**: [correctness review](20260909_correctness_review.md),
  reviewed after all four findings closed; [validation](validation.md),
  "Scope and QA assessment" reviewed before final security sign-off.

Reviewed executable SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `soil_thickness.py` | `c9e9395c9007482e40ed2166b26c42080752601f7b0f8a1a149b02f8d774cafc` |
| `run_study.py` | `c2e7967784259c61d5ddaa4e42ec6469d627ffebfa372e73fc78fe0efa062579` |
| `acquire_sources.py` | `6ccf6d00431a10d5c23eeb69705cbe8a1decb15269847c63f8541001bf3129be` |

## Findings

| ID | Severity | Surface | Description and exploit path | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Raster input and network/file reads | Checking only the `.tif` suffix allowed a VRT renamed as TIFF to reference a separate local or remote raster. This bypassed the explicit GeoTIFF-only evaluation contract and could read sources outside the recorded input hashes before failing later during output. | Direct unmocked pre-fix probe loaded a VRT's separate local TIFF; failure occurred only when writing a VRT-derived output profile. The fixed helper and harness restrict input readers to `driver="GTiff"`. `test_disguised_vrt_rejected_before_output` covers MUKEY and mask inputs. A separate post-fix loopback HTTP probe covered MUKEY, mask, and native STATSGO inputs: all rejected, zero HTTP requests, no builder output directories. | Enforce actual GeoTIFF decoding before pixel reads at each evaluation boundary; preserve valid TIFF inputs and add regression coverage. | Resolved |

No other medium/high findings were identified. The reviewer did not edit
implementation; the executing agent applied the correction.

## Security Triage Decision

- **Security impact level**: `high`, retaining the package's predeclared gate
  for new file/SQLite readers and source acquisition. Exposure is limited by
  the offline operator scope.
- **Dedicated security review required**: `yes`, also explicitly required by M5.
- **Threat model assumptions**:
  - Operators choose trusted CLI paths, the owned WBT executable, and a new
    study output directory under a parent they control. No shared hostile
    output-directory writer is supported.
  - Evaluation consumes reviewed, frozen public soil records. External
    acquisition is an explicit separate command, with no implicit fallback.
  - No browser, API, queue, live Soils build, or production NoDb mutation is
    added. This review does not approve future service exposure.
  - Public agency data and existing GDAL/SQLite/Rust binaries remain trusted
    dependencies. File hashes detect changes relative to the reviewed manifest;
    they are not signatures authenticating an arbitrary replacement manifest.
- **Valid states preserved**: populated canonical sources, URI-special local
  filenames, complete and partial catchments, unknown/outside-survey keys, and
  per-component missing horizons retain their documented outcomes. Missing DBs,
  malformed/empty source tables, disguised VRTs, and existing output directories
  fail explicitly. Empty individual components remain scientific unavailable
  records, not adapter errors.

## Verdict

- **Gate status**: `pass` for the reviewed offline study.
- **Unresolved findings**: high 0; medium 0; low 0.
- **Release recommendation**: `ship` within the authorized offline scope.
  Broad-suite results, final evaluation evidence, and package publication remain
  executing-agent closeout responsibilities; this gate does not certify them.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

- [x] Direct unmocked checks exercise valid SQLite/GeoTIFF inputs and hostile
  database/raster/output states.
- [x] Existing full/partial support contracts and missing-component outcomes
  are preserved by the GeoTIFF restriction.
- [x] Failed missing-source reads do not create a database; failed hostile
  raster validation does not create builder outputs.
- [x] Linked correctness/QA artifacts reviewed after findings closure.
- [x] Security approval does not establish scientific source acceptance or
  replace correctness/QA approval.

### 1) Auth, Session, and Authorization

Not applicable: no route, session, JWT, CSRF, or role boundary changes. CLI
filesystem access uses the invoking operator's existing permissions.

### 2) Secrets and Credential Handling

No added credentials, token transport, secret mounts, or secret fallback.
Inspected acquisition code and fixture text contain public soil records,
source metadata, and query provenance. A focused credential-pattern scan found
no matches; this is scoped evidence rather than a universal secret detector.

### 3) Input Validation and Output Safety

- SQLite uses an encoded file URI with `mode=ro`, `query_only=ON`,
  `trusted_schema=OFF`, disabled extension loading, fixed selected columns, and
  a real-table/schema check. Connections close in `finally`.
- The adapter rejects a `component` view instead of executing its projection.
  Table and selected-column identifiers are implementation constants.
- The study's disposable SQLite reconstruction inserts CSV values through
  placeholders. CSV headers come from the hash-checked, operator-selected
  fixture bundle; this is not an arbitrary-upload SQL boundary.
- GeoTIFF inputs require the GTiff driver; MUKEY/mask grids and included-cell
  values are checked before cross-raster aggregation. SEC-01 is closed.
- Catchment identifiers remain CSV values and do not determine builder output
  paths. A traversal-like identifier `../label` completed without path traversal.
- No `eval`, pickle, shell expansion, or executable deserialization was added.
  Raw CSV text is data; the inspected fixture fields had no leading `=`, `+`,
  or `@` formula strings. Outputs are not a general spreadsheet sanitization API.

### 4) File System and Run-Tree Boundaries

Input files resolve to regular local files; SQLite sources are read-only.
New output directories use `exist_ok=False` and fixed artifact names. A direct
existing-output symlink test raised `FileExistsError` without overwriting data.
Source hashes are recorded and checked after the build. Failure can leave
partial new outputs without a completion manifest; the contract requires a
fresh output directory on retry. No live project or generated WEPP file is
written. Operator-owned parent paths and ordinary process umask apply; this is
not a sandbox against a concurrent local attacker.

### 5) Queue, Worker, and Subprocess Surfaces

No enqueue sites, dependencies, worker tasks, or RQ contracts change. The
operator-supplied owned WBT executable runs through an argument list with
`shell=False` by default and `check=True`; its hash and command arrays are
recorded. WBT jobs are operator-bounded by the fixed three-site study. There is
no subprocess timeout, so a hung binary requires operator cancellation; this
does not expose a request-driven denial-of-service surface.

### 6) Agentic Tooling and MCP Surfaces

No new MCP server, tool permission, token, or autonomous remote-action path.
Review delegation is explicitly authorized in M5. Review writes are limited
to this artifact and disposable temporary test files. No publication or
deployment is performed.

### 7) Network and External Integrations

Evaluation has no acquisition fallback; disguised VRT references are rejected.
Explicit acquisition uses fixed NRCS SDA and ScienceBase HTTPS endpoints and
requires the expected exact USGS COG asset URL. SQL predicates contain positive
integer raster keys, with at most 1,000 keys per site. Native raster windows are
capped at 2,000,000 cells. HTTP requests have 30/60-second timeouts, GDAL has a
30-second HTTP timeout, and no retry amplification loop was added. The intended
local spatial-source VRT is explicit only in acquisition. Public-provider
responses, normal HTTPS redirects, and operator-selected terrain/source files
remain trust assumptions; acquisition is not a hostile-URL upload service.

### 8) CI/CD and Supply Chain

No CI workflow, runner permission, image, registry, or dependency-manifest
changes. The code uses existing requests, rasterio/NumPy, matplotlib, SQLite,
wepppyo3, and owned WBT capabilities. The frozen bundle contains 17 files,
322,537 bytes total after final provenance refresh: all hashes and sizes match,
no symlinks are present, and
all six `.tif` files have TIFF magic bytes.

### 9) Data Integrity, Locking, and Concurrency

No NoDb dump/lock/cache or Redis state changes. Inputs and fixtures are hashed;
evaluation verifies frozen files before generation and again at completion.
The builder reserves a new output directory and emits its completion manifest
last. Concurrent input mutation is outside the frozen-study contract and the
post-build hash check is a detection measure, not transaction isolation for
a live SQLite WAL database. Scientific provenance and parameter choices remain
subject to the separate correctness review and ADR.

### 10) Logging, Monitoring, and Incident Readiness

Failures are explicit exceptions; no new broad exception swallowing. WBT
stdout/stderr, command arrays, binary/source hashes, and source query metadata
support diagnosis. Logs contain public paths/data rather than credentials.
Containment is to stop the offline process, retain incomplete outputs for
diagnosis, and rerun to a new directory after correction; no production rollback
is needed.

## Validation Evidence

- `wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_soil_thickness.py -k 'readonly or rejects_disguised or generated_pipeline' --maxfail=1`:
  2 passed, 30 deselected. The actual VRT test name requires the separate selector
  below; this command covered read-only and normal generated-pipeline behavior.
- `wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_soil_thickness.py -k disguised_vrt --maxfail=1`:
  1 passed, 33 deselected; two dependency deprecation warnings.
- Direct `wctl run-python -` probes, using temporary SQLite/GeoTIFF files and a
  loopback-only `ThreadingHTTPServer`, without mocked storage or raster calls:
  - Valid SQLite containing `?mode=rw#` in its filename read successfully and
    remained byte-for-byte unchanged.
  - Missing SQLite rejected without creation; a schema-shaped SQLite view
    rejected explicitly.
  - Before correction, a VRT named `.tif` read its referenced local raster and
    failed later at output; after correction, VRTs referencing the loopback
    HTTP TIFF were rejected at all three evaluation boundaries with zero
    HEAD/GET requests and no builder output directories.
  - Valid 2-by-2 GeoTIFF pipeline produced 30 cm and a completion manifest;
    traversal-like catchment ID stayed a value; an existing output symlink was
    rejected and input bytes stayed unchanged.
- Local fixture audit, repeated after final provenance refresh: 17/17 SHA-256
  and size checks passed, TIFF signatures passed, zero symlinks. Final manifest
  SHA-256 is
  `e304b99a814eec1081c847beff9ef8b72ab550e2947f555dbc50fdbb42b3ee81`.
  The initial focused credential-pattern scan returned no matches.
- The correctness review records all four findings closed, including numeric
  overflow and Float32 representation. Executing-agent QA records 35 passing
  focused tests, passing stub hygiene, and byte-identical reproduction of all
  six CSV and six raster inputs through the promoted acquisition recipe.
- `wctl doc-lint --path docs/work-packages/20260908_staley_m3_soils/artifacts/20260909_security_review.md`:
  1 file validated, 0 errors, 0 warnings. `uk2us` spelling preview had no diff.

## Residual Risk

There are no accepted open security findings and no risk-acceptance request.
Ordinary residual risks are trusted local operator inputs/binaries, agency
source authenticity and availability, resource use for explicitly supplied
rasters, and incomplete new output folders after interruption. The study does
not offer a sandbox, production readiness signal, or automated public service.
Future NoDb/UI/RQ integration requires its own threat model, auth/path controls,
production identity evidence, and security review.

## Sign-off

- **Security reviewer**: independent `security_reviewer` agent, 2026-09-09 UTC;
  SEC-01 verified resolved, correctness/QA crosscheck complete.
- **Package owner acknowledgment**: no unresolved finding requires acceptance;
  overall package closure remains with the executing agent and scientific
  policy decisions remain with the requesting owner.
