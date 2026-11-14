# Close shape-converter security conformance gaps

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current. Update this
plan and `tracker.md` at every stopping point.

## Purpose / Big Picture

After this work, uploaded shapefiles are admitted through one unambiguous archive
and driver contract; native parsing occurs in an effective second sandbox; and
the parent accepts only bounded data-only parser output. A compromised or
malfunctioning parser cannot use its IPC channel to execute in the parent, read
parent-only files, write outside request output, use the network, signal the API
process, or evade timeout cleanup. Valid GeoJSON and GeoParquet conversions retain
their existing semantics.

The proof combines change-scoped hostile-boundary tests, valid-output semantic
readback, and production-equivalent runtime inspection. Do not run the full
repository suite or unrelated shape-converter/frontend/service suites. This plan
records current parser dependency evidence. The operator later authorized a
dedicated shape-converter image with an upgraded coherent GDAL/Fiona stack; the
common WEPPpy image remains unchanged.

## Progress

- [x] (2026-11-14 01:46 UTC) Scaffold package, tracker, failure-class assessment,
      active ExecPlan, and code/QA/correctness/security review gates.
- [x] (2026-11-14 01:46 UTC) Link severity-high issues #655 and #656 and record
      the operator's GDAL-upgrade deferral.
- [x] (2026-11-14 05:13 UTC) Run scoped baseline: 136 passed; reproduce IPC,
      Unicode/case-fold alias, and incomplete-prefix gaps with disposable probes.
- [ ] M0: finish full red inventory (driver, semantic, ratio, and error cases remain).
- [ ] M0: approve a sandbox mechanism. Bubblewrap startup prerequisite failed
      under existing restrictions; independent security review confirms stop gate.
- [ ] M0: approve a compression-ratio threshold ADR if the control is retained.
- [x] (2026-11-14) Independent slice contract reviewed and committed as
      checkpoint ancestor `6712ba631`; full sandbox/compression decisions pending.
- [ ] M1: retain focused failing tests at each confirmed boundary.
- [x] (2026-11-14) Independent M2: data-only JSON IPC, structural budgets,
      exact driver, and bounded fixed worker error mapping implemented.
- [x] (2026-11-14) Independent M3 slice: NFC/case-fold aliases and extra
      incomplete/optional prefixes rejected.
- [x] (2026-11-14 06:56 UTC) Implement and locally qualify the operator-approved
      minimal dedicated shape-converter image using GDAL 3.12.4 and Fiona 1.10.1.
- [ ] M3 remainder: compression decision and broader semantic matrix.
- [ ] M4: implement effective second sandbox and runtime-derived readiness.
- [x] (2026-11-14) M5 dedicated candidate: image identity,
      dependency/linkage, resolved Compose, artifact, and vulnerability-scan
      evidence captured; operator-approved one-worker command passed exact-image
      abuse-control, metadata, conversion, and cleanup requalification.
      Common-image source/config was unchanged; rollout evidence remains open.
- [x] (2026-11-14) Dedicated-image correctness, QA, and security re-reviews pass
      after the one-worker repair. This does not close broader M6, sandbox, or
      rollout gates.
- [x] (2026-11-14) Commit the reviewed dedicated-image implementation as
      `73ed430d4`; no image publication or deployment occurred.
- [ ] M6: validate, review, update GitHub issues, and prepare separate rollout.

## Surprises & Discoveries

- Starlette 1.3.1 removed the `@app.middleware` convenience decorator. The
  dedicated image caught this at startup even though the common runtime tests
  passed. Explicit `BaseHTTPMiddleware` registration is compatible with both
  runtimes; the rebuilt exact image passed health and real multipart conversions.
- Trivy's Python constraint matcher omits a known GDAL advisory and therefore is
  supplemental only. Pinned Syft 1.57.1 / Grype 0.121.3 inventory of exact image
  `sha256:d515d75ea603f174aa7b6b36c075f42fb0406cdb17901d60997aa0bbdbb0dff6`
  reports 0 Critical, 1 High, 315 Medium, 13 Low, and 3 Negligible package
  records. The 315 Medium records collapse to 105 unique advisory IDs because
  Ubuntu source findings repeat across binary packages. Grouped request-path
  non-reachability and immutable evidence hashes are retained in the image
  qualification artifact; independent security review remains required.
- Initial image review exposed two reproducibility gaps: mutable Ubuntu package
  resolution and an overridable base-image argument. The final Dockerfile uses
  the immutable GDAL base digest directly in both stages, resolves APT from
  snapshot `20261114T060000Z`, labels that snapshot, and asserts the final copied
  Fiona/GDAL runtime before completing the build.
- Exact two-worker QA exposed a preexisting cross-process contract defect that
  unit tests did not reveal. Rate/in-flight state and conversion metadata live in
  each Starlette application process. The service therefore admits limits once
  per worker and can return 404 for metadata created by the other worker. One
  worker is the smallest repair; shared state would violate the package's
  complexity budget without evidence that one worker misses acceptance needs.
- The one-worker requalification closed that defect without rebuilding the image:
  rate count one yielded 200/429/429, a held request forced a competing 503 and
  then released cleanly, twenty metadata reads all returned 200, and health,
  CORS, GeoJSON, GeoParquet, and scratch cleanup remained correct. Completing the
  held request also avoided the earlier disconnected-client traceback noise.
- Independent correctness, QA, and security re-reviews pass the dedicated-image
  slice. Security retains one Low package-closeout provenance item: persist the
  complete 105-unique-advisory scan appendix/raw reports outside `/tmp` and state
  the embedded-native vulnerability-matching limitation.

- Independent review identified real MultiPatch GeometryCollections. Removing
  Fiona's inactive null coordinates repairs a preexisting Shapely construction
  failure; both output formats now receive direct artifact readback coverage.
- Review also exposed uncaught CRSError/EmptyPartError/IndexError at post-decode
  construction. Narrow catches now return fixed canonical errors. Worker output
  pipes were replaced with DEVNULL plus fixed quota exit codes, removing parent
  diagnostic allocation and UTF-8 decoding exposure.

- (2026-11-14) Both user-namespace `unshare` and actual Bubblewrap startup
  failed with permission errors under current container restrictions. This is
  candidate-specific feasibility evidence, not proof that all sandboxes fail.
- Existing baseline passes despite a direct pickle canary being created before
  payload rejection. See the [M0 receipt](../../artifacts/20261114_m0_baseline_and_sandbox_probe.md).

- The outer container already has meaningful non-root, read-only, capability,
  resource, tmpfs, and internal-network controls. Preserve them; they do not
  constitute the required second parser boundary.
- The parser worker already receives `enabled_drivers=["ESRI Shapefile"]`, but
  the opened dataset's `driver` is not explicitly asserted.
- Archive admission already has absolute compressed/uncompressed/request quotas,
  yet path collision uses lowercase without Unicode normalization and no
  compression-ratio decision is recorded.
- Dataset selection rejects multiple complete prefixes but can select one
  complete dataset while leaving another incomplete shapefile prefix present.
- Inspect parses bounded headers/DBF/PRJ directly and does not use the Fiona
  worker. Sandbox claims must not be overstated for that endpoint.

## Decision Log

- Decision: change the production command from two Uvicorn workers to one.
  Rationale: exact-command QA proved that the current in-memory abuse controls
  and conversion metadata cannot satisfy service-level behavior across two
  processes. One worker preserves the isolated topology and avoids introducing
  a datastore, but command preservation was an explicit package constraint and
  therefore needed operator approval. The resolved Compose regression locks the
  complete one-worker command, and any future worker-count increase requires a
  reviewed shared-state contract.
  Date/Author: 2026-11-14, operator and Codex.

- Decision: refactor middleware registration and retain Starlette 1.3.1 in the
  dedicated image.
  Rationale: all Starlette versions before 1.3.1 are affected by the form-limit
  advisory, while 1.3.1 removed the decorator used by the service. Explicit
  `add_middleware(BaseHTTPMiddleware, dispatch=...)` is the former decorator's
  underlying behavior, preserves ordering, and works in both runtime versions.
  Date/Author: 2026-11-14, Codex; operator requested assessment.

- Decision: build a minimal dedicated shape-converter image and upgrade only its
  GDAL/Fiona stack.
  Rationale: the operator selected the bounded image split after reviewing the
  mitigation-versus-sandbox decision. GDAL 3.12.4 retains Ubuntu 24.04 and Python
  3.12 compatibility while advancing from the current GDAL 3.10.3 runtime;
  Fiona 1.10.1 will be source-built against that exact GDAL. The Compose service
  must stop inheriting common-image secrets, datastore settings, mounts, and
  dependencies. This is defense in depth and dependency risk reduction, not an
  effective second parser sandbox or release authorization.
  Date/Author: 2026-11-14, operator and Codex.

- Decision: proceed with the independent remediation slice before sandbox closure.
  Rationale: operator approved the recommended sequencing on 2026-11-14; the
  demonstrated executable IPC and admission gaps can be removed independently.
  Full conformance/deployment gates remain unchanged. This supersedes the earlier
  stop decision only for the named slice, not for sandbox or release acceptance.
  Date/Author: 2026-11-14, operator and Codex.

- Decision: stop at M0 after the namespace candidate failed its prerequisite.
  Rationale: M0 explicitly prohibits proceeding without a proven mechanism;
  independent security review agrees. No privilege/topology change is implied.
  Resume requires an operator decision on another bounded mechanism evaluation
  or amended sequencing for independent IPC/archive remediation.
  Date/Author: 2026-11-14, Codex and independent security reviewer.

- Decision: defer every GDAL/Fiona/PROJ/GEOS upgrade, rebuild, repin, or binary
  replacement.
  Rationale: explicit operator direction. Current runtime identity/linkage and
  vulnerability disposition remain required release evidence. A reachable
  Critical blocks closure and triggers a separate decision rather than an
  automatic upgrade.
  Superseded in part on 2026-11-14 only for the dedicated shape-converter image;
  the freeze remains in force for the common WEPPpy image.
  Date/Author: 2026-11-13 Pacific, operator; recorded by Codex 2026-11-14 UTC.

- Decision: use JSON as the first parser IPC candidate, with an explicit schema,
  byte/depth/type/cardinality/finite-number validation, and no object hooks.
  Rationale: it is data-only, standard-library, and sufficient for existing
  property/geometry primitives. The decoder alone is not the security control;
  validation before object construction is mandatory.
  Date/Author: 2026-11-14, Codex; pending M0 contract review.

- Decision: prototype one per-parser sandbox inside the existing hardened service
  container before considering a parser service.
  Rationale: it is the smallest topology-preserving path. Escalation requires
  retained production-equivalent evidence that it cannot satisfy the acceptance
  tests under the non-root container.
  Date/Author: 2026-11-14, Codex; pending dependency evaluation/operator review.

- Decision: do not choose a compression-ratio threshold in this scaffold.
  Rationale: a new workflow cutoff requires an ADR with valid-fixture and hostile
  evidence plus a named decision owner. Existing absolute quotas remain active.
  Date/Author: 2026-11-14, Codex.

- Decision: validation is limited to tests and runtime probes that exercise the
  changed boundaries; no full repository suite is required.
  Rationale: explicit operator direction and the package has a bounded service
  surface with direct security and semantic acceptance checks.
  Date/Author: 2026-11-13 Pacific, operator; recorded by Codex 2026-11-14 UTC.

## Outcomes & Retrospective

The authorized independent slice is implemented after reviewed contract checkpoint
`6712ba631`. See [slice evidence](../../artifacts/20261114_independent_slice.md)
for red/green tests, real-worker artifacts, disposable hardened-container probes,
and independent code/correctness/QA/security approvals. No parser dependency or
container protection changed. The sandbox/readiness gate, compression decision,
broader semantic matrix, current release evidence, and production deployment
remain pending; the package is not fully conformant or complete.

The dedicated candidate is now locally qualified. See
[dedicated-image evidence](../../artifacts/20261114_dedicated_image_qualification.md).
The image split removed common secrets, mounts, datastore coupling, and unrelated
source from the resolved service while preserving the outer container controls.
Exact-image health, GeoJSON, GeoParquet, cleanup, and hostile-IPC probes passed.
This outcome does not change the open second-sandbox or deployment gates.

## Context and Orientation

Work from `/workdir/wepppy`. Read root `AGENTS.md`, `tests/AGENTS.md`,
`docker/AGENTS.md`, the work-package standard, and the canonical shape-converter
contract before editing. Preserve unrelated dirty files and do not create or
switch branches.

`wepppy/microservices/shape_converter/archive_validation.py` validates and
extracts ZIP members into a request root. `inspect.py` selects a shared-prefix
`.shp/.shx/.dbf` dataset and reads bounded shapefile, DBF, and projection
metadata. `convert.py` invokes `convert_parser_worker.py` with a hard timeout and
process-group termination. The worker opens through Fiona/GDAL, accumulates
properties/geometries, and currently writes pickle; the parent currently
`pickle.load`s it before validating the mapping. `app.py` readiness currently
compares declared sandbox-mode strings and toolchain/scratch availability.

The current production Compose definition hardens the whole service container
and attaches it to an internal network. The parser process still shares that
container's user, mounts, namespace, and service process context. The required
second sandbox must be effective at every native parse, expose only the minimum
request-specific paths, and be observable through a real probe or attestation.

The canonical behavior and risk matrix live in
`wepppy/microservices/shape_converter/docs/specification.md`. Historical
work-package claims are evidence only; they do not override current code or the
living contract. GitHub #655 tracks executable IPC and #656 tracks the missing
second sandbox.

## Authorized sequencing amendment (2026-11-14)

Operator instruction: "proceed as recommended" authorizes independent IPC,
exact-driver, and archive remediation while sandbox conformance remains blocked.
Execute a reviewed contract checkpoint, focused red tests, M2, and the Unicode/
prefix portion of M3 now. The failed namespace candidate no longer blocks this
slice. Compression thresholds, broader semantics, M4 sandbox/readiness, M5 release
evidence, full closure, and deployment remain gated. No relaxation of container
protections or new topology is authorized. Record slice validation separately
from full package completion. The canonical specification's "Independent
remediation contract (2026-11-14)" holds the normative schema and rationale.

## Dedicated image amendment (2026-11-14)

The operator authorizes a new Dockerfile and minimal hash-locked requirements
set for the existing `shape-converter` Compose service. Use the official GDAL
3.12.4 Ubuntu-small base pinned by digest, retain Python 3.12, and source-build
Fiona 1.10.1 against the base image's `gdal-config`. Copy only shape-converter
and required observability source into the runtime image. Use a Dockerfile-
specific allowlist build context so repository secrets and unrelated source are
not sent to the builder. The resolved production service must contain no Compose
secrets, `env_file`, datastore dependency, host data mount, Docker socket, or
unrelated WEPPpy configuration. Preserve the existing fixed UID, read-only root,
dropped capabilities, resource limits, tmpfs, internal network, service name,
port, command, and Caddy route.

Build and inspect the exact image before any rollout. Prove imports and native
version/linkage, health endpoints, valid GeoJSON and GeoParquet readback, hostile
IPC rejection, absence of inherited secrets/mounts/configuration in resolved
Compose, final image files/history/config, and running-container environment,
mounts, secrets, identity, and networks. Record the exact base digest, resolved
package inventory, and final image ID. Every reachable Medium, High, or Critical
vulnerability requires remediation or explicit operator risk acceptance. A
`200` response produced only by matching `container/container` mode strings is
not sandbox evidence or release acceptance; production readiness remains
nonconformant until M4. A clean image split does not satisfy the second-sandbox
acceptance criterion, close issue #656, or authorize production deployment.

## Plan of Work

### Milestone 0: Baseline, decisions, and contract checkpoint

Re-run the failure-class inventory. Search all parser-worker launchers, pickle
loads/dumps, native Fiona/GDAL opens, archive extractors, dataset selectors,
readiness fields, container definitions, tests, and user/operator documentation.
For each row in `artifacts/20261113_failure_class_assessment.md`, record exact
code/config locations, current tests, and a direct red assertion or a reason the
row requires evidence rather than code.

Capture a pre-change green baseline for the directly affected archive, inspect,
convert, cleanup, readiness, runtime-hardening, and integration modules. Do not
run the whole shape-converter or repository suite. Build the current image and
record revision, image ID/digest where
available, user, mounts, namespaces, network, seccomp/AppArmor status, `ogr2ogr`
version, Fiona-linked GDAL, PROJ/GEOS versions, and native linkage. This is
baseline evidence, not permission to change a dependency.

Evaluate one in-container sandbox candidate under
`docs/standards/dependency-evaluation-standard.md`. Prefer a mechanism that runs
as the existing non-root user without a daemon, host socket, writable root,
privilege/capability increase, or new network service. Prototype it in the exact
production-equivalent container constraints. Demonstrate minimal read-only input,
write-only or narrowly writable output, no network, bounded processes/files/CPU/
memory/wall time, and termination of descendants. If no candidate meets these
conditions, stop and retain the failure evidence; do not create a parser service.

Prepare a parameterization ADR before adding a compression-ratio cutoff. Measure
valid archive ratios from committed or approved fixtures and compare bounded bomb
fixtures. The ADR names the exact per-member/aggregate rule, zero-byte behavior,
units, decision owner, rollback trigger, and compatibility controls. If the owner
rejects a ratio as redundant to absolute quotas, amend the contract explicitly
instead of leaving a false requirement.

Amend the contract with the final IPC schema, sandbox mechanism/attestation,
archive rule, dependency-evidence rule, and the dedicated-image exception to the
common-image dependency freeze. Obtain independent correctness and security
reviews. Commit those decisions as a standalone checkpoint ancestor before
production code changes.

Milestone acceptance: complete baseline and red matrix, approved sandbox
evaluation, approved archive threshold decision/ADR or explicit contract change,
two contract reviews, and recorded checkpoint SHA.

### Milestone 1: Direct failing regressions

Replace helper-only assumptions with direct boundary tests:

- Feed the current parent a worker-controlled object-capable pickle whose only
  observable behavior is a disposable canary attempt. Retain the failing result,
  then remove executable payload bytes from the normal green corpus after the
  JSON decoder exists. The lasting regression should prove non-JSON/object bytes
  are rejected and the canary is absent.
- Add malformed JSON/schema cases for trailing data, invalid UTF-8, duplicate
  keys if the decoder can detect them, excess bytes/depth/items, non-finite
  numbers, wrong primitive types, unknown/missing fields, unequal property and
  geometry counts, and invalid bounds/CRS values.
- Add renamed/disguised non-shapefile fixtures and assert exact driver rejection.
- Add Unicode-equivalent/case-folded archive aliases, separator variants, extra
  incomplete prefixes, compression-policy edges, and valid controls.
- Add bounded semantic fixtures for DBF/SHP count mismatch, invalid/truncated
  sidecars, geometry validity/type/coordinates, field-name collisions, and
  record/value limits according to the ratified contract.
- Add sandbox probes for parent-canary read, out-of-root write, socket open,
  signal/process escape, descendant timeout, partial output, and cleanup.

Tests must invoke the actual changed serializer, Fiona/GDAL open, archive
extractor, and sandbox where those are the failure boundaries. Mocks may isolate
unrelated HTTP or slow infrastructure but cannot stand in for the boundary being
claimed safe.

Milestone acceptance: each test fails for the intended current gap and retains
bounded, non-secret red evidence.

### Milestone 2: Data-only IPC and exact driver

Create a narrow IPC module adjacent to convert/worker code. Encode UTF-8 JSON
containing only the ratified top-level keys and JSON primitives. Normalize Fiona
property scalar values in the worker; reject values outside the documented
primitive contract rather than stringifying arbitrary objects. Reject NaN and
infinities. Write atomically within the request output path and preserve the
existing maximum payload size.

In the parent, reject over-size bytes before decode, decode with no object hooks,
enforce depth/cardinality/type/finite-number limits, validate the exact schema,
then construct CRS/Shapely/output objects. Bound and sanitize decoder and worker
errors. Rename `.pickle` scratch filenames and remove production pickle imports.

After Fiona opens the dataset with the existing driver allowlist, require
`dataset.driver == "ESRI Shapefile"` before reading bounds, CRS, schema, or
features. Keep GDAL plugin/remote-source environment restrictions explicit and
do not inherit attacker-controlled plugin paths.

Milestone acceptance: #655 regressions pass; source search finds no parser IPC
pickle; disguised formats fail; valid conversion semantic readback matches the
baseline.

### Milestone 3: Archive, dataset, and semantic closure

Normalize member path separators and Unicode NFC before case folding and
collision comparison. Apply the ratified compression policy without weakening
absolute compressed, uncompressed, member, path, or request quotas. Treat stored
and empty members explicitly to avoid division ambiguity.

Make dataset selection require exactly one logical prefix across every admitted
shapefile-related member. Reject a second complete or incomplete prefix; keep
allowed optional sidecars only when they match the selected normalized prefix.
Preserve `.shp.xml`/`.qmd` removal and no-content logging/response behavior.

Implement only semantic rules ratified in the M0 contract matrix. Every rule must
have a direct malformed fixture and a valid near-boundary control. Map failures
to stable canonical errors without exposing raw uploaded content or host paths.

Milestone acceptance: archive and semantic rows in the conformance table have
direct tests and no accepted valid-control regression.

### Milestone 4: Effective second sandbox and readiness

Wrap every native parser-worker launch with the approved sandbox. Expose only
the selected request input and the single output target/containing directory;
deny the service source, parent-only canary, unrelated scratch roots, credentials,
network, signals, and additional process creation beyond the ratified minimum.
Keep the existing outer container controls and process-group timeout escalation.

Do not fall back to direct worker execution if the sandbox is absent or fails.
Make readiness run or consume a freshness-bounded attestation from the same
sandbox launcher and policy used by real requests. The probe must demonstrate
effective restrictions, not compare caller-supplied labels. Avoid leaking mount,
host, image, or policy internals in the public readiness response; retain detailed
operator evidence in safe logs/receipts.

Milestone acceptance: #656 containment probes pass in the built container;
readiness fails closed for missing/ineffective policy; valid conversion parity,
timeout, descendant kill, and scratch cleanup pass.

### Milestone 5: Current dependency evidence without upgrade

Build the exact candidate with no GDAL/Fiona/PROJ/GEOS version edits. Record
image identity, package sources, `ogr2ogr --version`, Fiona's linked GDAL,
PROJ/GEOS versions, `ldd`/equivalent native linkage, and available SBOM/scan
results. Triage findings for reachability through the admitted Shapefile driver
and actual build configuration. Do not claim a static CVE list is current.

If a reachable Critical issue is confirmed, mark the package blocked at the
release gate, retain the evidence, and request a separate remediation decision.
Do not change dependency versions under this plan. High findings require the
security review's explicit disposition and operator decision under the package
closure policy.

Milestone acceptance: reproducible current-runtime receipt with no hidden version
change and an evidence-backed reachable-risk disposition.

### Milestone 6: Validation, review, and handoff

Run the directly affected unit and integration modules, broad-exception checks,
test-stub checks when imports/stubs change, and scoped documentation checks. Do
not run the full repository suite, full frontend suite, or unrelated service
tests. Build the candidate and exercise valid and hostile requests through the
proxied service. Parse returned GeoJSON and GeoParquet rather than relying on
HTTP status or file existence.

When separately authorized, validate the exact candidate on forest1 using the
canonical deployment entry point and record revision/container identity. Do not
deploy to production under this package. Complete independent code, QA,
correctness, and security reviews; close every Critical/High and disposition
Medium findings. Update the contract conformance table, package/tracker,
PROJECT_TRACKER, and #655/#656 with exact evidence. Close issues only when their
acceptance criteria are actually met.

Milestone acceptance: all required local and environment gates/reviews pass,
documentation matches effective behavior, the common image remains unchanged,
the dedicated dependency upgrade is exactly evidenced, and status language
distinguishes implementation, local validation, environment validation, and
deployment.

## Concrete Steps

Run from `/workdir/wepppy`.

Baseline and change-scoped iteration:

    wctl run-pytest tests/shape_converter/unit/test_archive_validation.py tests/shape_converter/unit/test_inspect_endpoint.py tests/shape_converter/unit/test_convert_endpoint.py tests/shape_converter/unit/test_cleanup_lifecycle.py --maxfail=1
    wctl run-pytest tests/shape_converter/unit/test_health_routes.py tests/shape_converter/unit/test_runtime_hardening.py --maxfail=1
    wctl run-pytest tests/shape_converter/integration/test_inspect_api.py tests/shape_converter/integration/test_convert_api.py tests/shape_converter/integration/test_runtime_hardening_api.py --maxfail=1

Source and hygiene checks:

    rg -n "pickle|fiona\.open|enabled_drivers|dataset\.driver|SANDBOX_MODE|subprocess\.Popen" wepppy/microservices/shape_converter tests/shape_converter docker
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

If and only if the implementation changes imports or test stubs:

    wctl check-test-stubs

Dedicated candidate container and dependency evidence:

    docker compose -f docker/docker-compose.dev.yml build shape-converter
    docker compose -f docker/docker-compose.dev.yml up -d shape-converter caddy
    docker exec wepppy-shape-converter ogr2ogr --version
    docker exec wepppy-shape-converter /opt/venv/bin/python -c "import fiona, pyproj; print(fiona.__version__, fiona.__gdal_version__, pyproj.__version__, pyproj.proj_version_str)"

Compose image-split regression and merged-configuration checks:

    wctl run-pytest tests/docker/unit/test_project_config_rollout_contract.py --maxfail=1
    wctl docker compose config --format json

Scoped documentation checks:

    wctl doc-lint --path docs/work-packages/20261113_shape_converter_security_conformance
    wctl doc-lint --path wepppy/microservices/shape_converter/docs/specification.md

Do not run the full repository suite for this package. If implementation touches
a test module not listed above, add that module to the change-scoped commands and
record why. Any forest1 action must use the canonical deployment workflow and
requires separate authorization.

## Validation and Acceptance

The minimum valid matrix contains point, line, polygon, multipart, null geometry,
attributes with every allowed primitive/null value, known/unknown CRS behavior,
GeoJSON, GeoParquet, inspect, and convert. Compare parsed counts, geometry types
and coordinates, bounds, CRS, properties, nulls, warnings, filenames, and content
types with the pre-change baseline.

The hostile matrix contains object-capable/non-JSON IPC, over-size/depth/item
payloads, non-finite numbers, schema mismatch, Unicode aliases, extra prefixes,
compression edges, disguised drivers, malformed/truncated sidecars, semantic
mismatches, parent-canary read, out-of-root write, socket open, process/signal
escape, timeout, cancellation, and partial output. Each must fail at the expected
boundary with a canonical bounded error and empty request scratch after response.

An HTTP 200, a process exit code, a matching environment string, or an output
file's existence is insufficient. Read back the effective sandbox restrictions
and parse output semantics. Do not state "fixed" or close #655/#656 before the
exact candidate passes its required evidence boundary.

## Idempotence and Recovery

All tests and prototypes use disposable request roots, fixtures, containers, and
canaries. Re-running them must not mutate committed fixtures, shared projects, or
production data. Preserve useful failed-attempt logs/receipts without retaining
hostile uploaded content or secrets.

Serializer and sandbox changes must fail closed. Rollback cannot restore pickle
IPC or a direct unsandboxed parser path; if a broader application rollback is
necessary, retain equivalent guards or disable conversion until a safe candidate
is active. Archive threshold rollback follows its ADR. No data migration exists.

## Artifacts and Notes

Retain under this package:

- baseline and final source/runtime inventories;
- contract checkpoint and independent review dispositions;
- compression-policy ADR link and sandbox dependency evaluation;
- bounded red/green transcripts and fixture manifests/hashes;
- semantic parity report for GeoJSON/GeoParquet;
- sandbox policy, probe, denial, timeout, and cleanup receipts;
- exact revision, container identity, native versions/linkage, SBOM/scan, and CVE
  dispositions;
- completed code, QA, correctness, and security reviews; and
- forest1 validation and production rollout receipts only if separately
  authorized and actually performed.

Do not retain executable exploit payloads, uploaded private data, secrets,
production tokens, or raw metadata sidecar content.

## Interfaces and Dependencies

Preserve the existing public endpoints, multipart fields, response/error schema,
output media types, filenames, request-scoped cleanup, and independent uploads.
The worker IPC is private and may change to the ratified JSON schema. Use existing
`ShapeConverterError`, `ArchiveLimits`, `RequestScratchLayout`, process-group
termination, and safe logging/error utilities.

One sandbox dependency may be added only after the M0 evaluation and reviewed
contract checkpoint. No other runtime dependency is authorized. GDAL, Fiona,
PROJ, and GEOS versions are frozen for this package.

Revision note, 2026-11-14: initial scaffold created from the 2026-11-13 security
contract review. Added explicit GDAL-upgrade deferral, bounded topology, governed
compression-policy decision, direct artifact evidence, and #655/#656 closure
gates.

Revision note (2026-11-14): recorded scoped baseline, direct red observations,
failed sandbox prerequisite, and independent review; retained M0 stop gate.

Revision note (2026-11-14, independent slice): operator-approved sequencing is
implemented; record local evidence separately from remaining sandbox/release gates.
