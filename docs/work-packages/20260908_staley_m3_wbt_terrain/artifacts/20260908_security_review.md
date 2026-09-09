# Security Review - Staley M3 WBT Terrain

## Metadata

- **Package**: `docs/work-packages/20260908_staley_m3_wbt_terrain/`
- **Reviewer**: Independent Codex `security_reviewer` agent.
- **Date**: 2026-09-08, America/Los_Angeles.
- **Scope reviewed**: `/workdir/weppcloud-wbt/` new
  `whitebox-tools-app/src/tools/hydro_analysis/d8_upstream_relief.rs`, tool
  registration, `whitebox_tools.py`, `WBT/whitebox_tools.py`, and the directly
  affected `whitebox-raster/src/geotiff/mod.rs` and
  `whitebox-raster/src/lib.rs` header, metadata, serialization, and output error
  boundaries.
- **Commit/branch context**: Uncommitted changes on `master`, based on
  `0af47c38356ab12967e209f5b2fde3a8d802348b`.
- **Final binary SHA-256**:
  `d4adb49d0e856a587ff996cf695bb71fbacf5669b90e4b526de403aac91d4718`.
- **Related artifacts**: [Terrain contract](terrain_contract.md),
  [correctness review](20260908_correctness_review.md), and
  [validation](validation.md). QA evidence is provided by the executing agent's
  complete test runs and the independent correctness review; the ExecPlan does
  not require a separate delegated QA artifact.

## Security Triage Decision

- **Security impact level**: `high`, following the repository default for
  new CLI file/path handling and subprocess bindings.
- **Dedicated security review required**: `yes`, also explicit in ExecPlan M5.
- **Triage rationale**: The change adds local raster inputs and several output
  paths to an existing executable. It creates no HTTP endpoint, upload handler,
  queue edge, credential dependency, network connection, or deployment change.
- **Threat model assumptions**: The operator chooses input/output paths under
  the executable's existing OS identity. Input rasters and output parent
  directories remain caller-controlled and stable during execution. Independent
  invocations may choose the same output name; this must fail without replacing
  an existing file. The CLI is not an adversarial multi-user filesystem sandbox
  or a validator for arbitrary untrusted TIFF uploads.
- **Valid states that controls must preserve**: New distinct output files;
  optional coverage absent or requested; aligned supported UTM rasters;
  valid finite or NaN NoData conventions; terminal and domain-exiting pointers;
  conditioned routing over raw rising/flat elevations. Missing required inputs,
  empty valid-data domains, unsupported grids/units, mask mismatches, invalid
  pointers, cycles, and existing/aliased outputs are contract-defined errors.
  There is no legacy interface for this new command.

## Findings

| ID | Severity | Surface | Description and trigger | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Output file integrity | Initial existence checks preceded raster loading/traversal, while final `File::create` could truncate a destination created in between, including a symlink target. Two concurrent invocations could therefore replace an output despite the new-file contract. | Original `new_output()` and `run()` output loop; shared GeoTIFF writer's `File::create`. | Publish completed output with an atomic no-replace operation; retain explicit failure and cleanup. | Resolved: `publish()` uses private same-parent staging and `hard_link`. Direct publication test confirms an existing destination returns `AlreadyExists` and preserves its bytes. |
| SEC-02 | Medium | Failure reporting and partial output integrity | Original `out.write()?` invoked `Raster::write`, which prints GeoTIFF writer errors and returns `Ok(())`. Missing/truncated output could therefore be reported as successful. Buffered final write errors also needed propagation. | `whitebox-raster/src/lib.rs`, `Raster::write` GeoTIFF arm and final return; `whitebox-raster/src/geotiff/mod.rs`, `write_geotiff`. | Use a fallible TIFF writer and explicitly flush before publication; fail the command on writing/publication errors. | Resolved: direct `write_geotiff`, `flush()?`, and propagated `publish()` errors. Tests confirm missing-parent and writer-level errors fail without publishing failed output, and staging is cleaned. |

No accepted-risk exception is requested for either finding. No exploit
demonstrations were executed; findings derive from source review. Validation
uses ordinary unit and integration tests.

## Verdict

- **Gate status**: `pass` for the reviewed local CLI, wrappers, and affected TIFF
  I/O boundaries.
- **Unresolved findings**: High: 0; Medium: 0; Low: 0.
- **Release recommendation**: `ship` within the reviewed local tooling scope,
  subject to remaining non-security package gates. Production integration,
  deployment, binary vendoring, and model availability decisions are outside
  this approval.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

- [x] Final independent correctness/QA evidence linked and reviewed. All five
  correctness findings are closed; the final artifact records valid-state
  noninterference for the reviewed input/output and legacy-tool boundaries.
- [x] Security checks reject malformed or unsupported states named by the
  contract; absent optional coverage remains supported.
- [x] Direct unmocked successful output and rejected existing-output evidence
  reviewed on the final implementation.
- [x] Security review does not substitute for numerical, calibration, resolution,
  or user-experience acceptance.

### 1) Auth, Session, and Authorization

Not applicable: no changed service, session, JWT, role, CSRF, or authorization
boundary. The local CLI retains its caller's filesystem authority; it does not
claim run-root containment.

### 2) Secrets and Credential Handling

- [x] No new secrets, credential defaults, mounts, or token handling.
- [x] Wrapper argv carries only command inputs and settings; no new credentials.

### 3) Input Validation and Output Safety

- [x] Required/unknown/duplicate arguments, elevation declaration, raster
  dimensions/alignment/CRS, pointer codes, masks, nonfinite values, and cycles
  have explicit validation paths.
- [x] Output aliases resolve through canonical parent directories; existing
  destinations and symlinks are rejected, and final no-replace publication
  addresses creation after preflight.
- [x] Both bindings append each `--key=value` as one argv element and retain
  existing `Popen(..., shell=False)` execution. No shell interpolation,
  deserialization, rendering, URL fetching, or new execution language is added.
- [x] Final output error propagation regression evidence reviewed.

### 4) File System and Run-Tree Boundaries

- [x] Explicit caller-supplied paths are the local CLI contract; a server-side
  run-root authorization policy is outside this change.
- [x] Staging is in the output parent with Unix mode 0700. `hard_link` creates a
  new destination without replacing a file or following a destination symlink.
- [x] Staging cleanup is attempted on success/failure; cleanup errors are logged
  and returned. Previously published outputs can remain after a later failure.
- [x] Durable `weppcloud-wbt/docs/d8_upstream_relief.md` and the package terrain
  contract describe caller-controlled parents, hard-link filesystem support,
  individual publication, and partial-set recovery.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] No enqueue site, worker task, cancellation, or dependency edge changes.
- [x] Existing subprocess identity/environment and shell-free invocation retained.
- [x] `wctl check-rq-graph` is inapplicable because queue wiring is unchanged.

### 6) Agentic Tooling and MCP Surfaces

Not applicable: no product agent/MCP capability changes, token changes, or
delegated execution privileges. This bounded review is authorized by ExecPlan M5.

### 7) Network and External Integrations

Not applicable: no runtime network calls, downloads, exposed endpoints, retry
loops, or external services added.

### 8) CI/CD and Supply Chain

- [x] No dependency, workflow permission, runner, registry, deployment, or binary
  vendoring changes in scope. Existing owned raster I/O is used.

### 9) Data Integrity, Locking, and Concurrency

- [x] No NoDb, Redis, or shared application-state mutation changes.
- [x] Directed traversal rejects cycles before output publication and preserves
  within-domain output semantics for NoData/exterior termination.
- [x] Independent output publication is deliberate; the set is not transactional.
- [x] Existing-destination and I/O-error tests exercise the final publication
  boundary independently of preflight.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Explicit validation and publication errors reach the caller. Cleanup errors
  include the staging location; no broad exception fallback is added.
- [x] Raw DEM/pointer paths are intended local provenance. They are not secret
  material and no artifact download/publication endpoint is introduced.
- [x] Containment is to stop the local command, discard the partial output set,
  and retry with fresh names after correcting the reported error.

## Validation Evidence

- Reviewer executed `cargo test -p whitebox-tools-app d8_upstream_relief --
  --nocapture`: 5 passed, 147 filtered out; log
  `/tmp/staley-m3-security-unit.log`.
- Source review traced both Python methods to existing `run_tool` and
  `Popen(..., shell=False)`; compared both bindings' added methods.
- Source review traced preflight, canonical paths, validation, private staging,
  hard-link publication, writer flush, and cleanup/error propagation.
- Reviewer executed `/workdir/wepppy/.venv/bin/python -m unittest discover -s
  tests -p test_d8_upstream_relief.py`: 7 tests passed on the rebuilt release
  binary, including both real Python bindings, correct generated H/A/coverage,
  preserved source bytes on overwrite rejection, and malformed input rejection;
  log `/tmp/staley-m3-security-cli.log`.
- Final reviewer rerun of the same command against the final binary above:
  11 tests passed, log `/tmp/staley-m3-security-final-cli.log`. Expanded cases
  include single-row compressed/uncompressed output, metadata readback,
  NaN/BigTIFF inputs, invalid original TIFF tags, and preserved legacy
  `D8Pointer` georeferencing with strict terrain rejection of zero source scale.
- Reviewed executing-agent logs: `/tmp/staley-m3-final-cargo-test.log` reports
  152 app Rust tests passed; `/tmp/staley-m3-all-python-tests.log` reports all
  15 Python tests passed. The final correctness reviewer independently repeated
  all 15 Python tests and closed the five numerical/metadata/legacy findings.
- `publication_never_replaces_existing_destination_and_propagates_io_error`
  directly exercises successful staging plus rejected existing publication,
  missing parent, writer failure, and cleanup without mocks.
- Final source review checks original sample count and separate source pixel
  scale, single-strip inline TIFF fields, plain-text ImageDescription provenance,
  and explicit flush. No new execution, networking, credential, or rendering
  surface is introduced. The original pixel-scale field retains legacy decoder
  behavior. The metadata is plain text, not an executable or XML template.
- `wctl doc-lint --path` this artifact: 1 file, 0 errors, 0 warnings. Spelling
  preview used `diff -u <artifact> <(uk2us <artifact>)`.

## Residual Risk

- **Inherited raster decoder/resource boundary**: TIFF loading occurs before
  tool-level grid validation and may allocate memory proportional to raster
  dimensions. This package does not make the existing decoder safe for hostile
  uploads or establish process resource limits. Any future remote upload/worker
  integration requires its own input/resource and authorization review.
- **Caller-controlled filesystem**: Parent-directory replacement by a hostile
  principal is outside the supported threat model. Mode 0700 protects ordinary
  staging access on Unix; the code does not promise dirfd-based containment,
  Windows ACL hardening, or isolation from another process with the same identity.
- **Publication limitations**: Same-parent hard links require filesystem support.
  Unsupported filesystems fail explicitly. Process termination can leave staging
  directories or already published members of an incomplete set. Flush does not
  promise crash durability through `fsync`.
- **Follow-up boundary**: Future production WEPPpy wiring/deployment remains a
  separate package and must validate its real identities, mounts, permissions,
  run ownership, quotas, and output lifecycle before exposure.

These are scope limitations, not accepted unresolved medium/high findings.

## Sign-off

- **Security reviewer**: Independent Codex `security_reviewer`, 2026-09-08;
  final sign-off complete after correctness/QA evidence review.
- **Package owner**: Parent executing Codex agent acknowledged both remediations,
  documented the supported filesystem scope, and requested final review. No
  unresolved finding or risk-acceptance exception requires owner approval.
