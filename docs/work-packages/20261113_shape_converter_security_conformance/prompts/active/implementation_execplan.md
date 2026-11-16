# Close shape-converter security conformance gaps

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current. Update this
plan and `tracker.md` at every stopping point.

## Purpose / Big Picture

After this work, uploaded shapefiles are admitted through one unambiguous archive
contract and parsed by a narrow memory-safe Rust implementation instead of
GDAL/Fiona. The parser runs as a short-lived CLI with strict JSON IPC, hard wall-
time and process-group termination, directly proven CPU/memory/file/output
limits, and request cleanup. Valid GeoJSON and GeoParquet conversions retain
their existing semantics. This plan no longer claims containment of arbitrary
code execution inside the outer container; that residual risk is explicit.

The proof combines change-scoped hostile-boundary tests, valid-output semantic
readback, and production-equivalent runtime inspection. Do not run the full
repository suite or unrelated shape-converter/frontend/service suites. The
operator narrowed M4 to a service-local lightweight Rust parser CLI
after deciding that the goal is to remove GDAL/Fiona's hostile binary parsing
risk rather than contain arbitrary parser code execution. The locally qualified
GDAL/Fiona image remains a parity reference until the Rust path passes every
gate; it is not the final parser architecture.

## Progress

- [x] (2026-11-14 01:46 UTC) Scaffold package, tracker, failure-class assessment,
      active ExecPlan, and code/QA/correctness/security review gates.
- [x] (2026-11-14 01:46 UTC) Link severity-high issues #655 and #656 and record
      the operator's GDAL-upgrade deferral.
- [x] (2026-11-14 05:13 UTC) Run scoped baseline: 136 passed; reproduce IPC,
      Unicode/case-fold alias, and incomplete-prefix gaps with disposable probes.
- [x] (2026-11-14) M0: finish the red inventory, including malformed binary
      headers/counts, semantic drift, resource ceilings, and image dependencies.
- [x] (2026-11-14) M0 parser replacement selected: a service-local lightweight
      Rust CLI in the existing hardened container, with no Python extension or
      in-process native parser path. Dependency/limit evaluation remains before code.
- [x] (2026-11-14) M0 compression decision: retain absolute quotas and do not
      introduce a ratio threshold; no parameterization change or ADR is required.
- [x] (2026-11-14) Independent slice contract reviewed and committed as
      checkpoint ancestor `6712ba631`; full sandbox/compression decisions pending.
- [x] (2026-11-14) M1: retain focused tests at each confirmed IPC, archive,
      semantic, provenance, malformed-binary, and resource boundary.
- [x] (2026-11-14) Independent M2: data-only JSON IPC, structural budgets,
      exact driver, and bounded fixed worker error mapping implemented.
- [x] (2026-11-14) Independent M3 slice: NFC/case-fold aliases and extra
      incomplete/optional prefixes rejected.
- [x] (2026-11-14 06:56 UTC) Implement and locally qualify the operator-approved
      minimal dedicated shape-converter image using GDAL 3.12.4 and Fiona 1.10.1.
- [x] (2026-11-14) M3 remainder: absolute-quota compression policy and broader
      point/line/polygon/Z/null/MultiPatch/DBF/output semantic matrix validated.
- [x] (2026-11-14) M4A: evaluate and ratify the Rust `shapefile` dependency, single-crate CLI
      contract, and enforceable resource-limit mechanism.
- [x] (2026-11-14) M4B: implement Rust semantic parity and hostile-input limits in
      the service-local parser crate, backed by direct Rust tests and a bounded
      malformed-binary mutation corpus.
- [x] (2026-11-14) M4C: integrate `shape_parser_cli`, process-group timeout/kill, per-process
      resource limits, fail-closed Python launcher, and runtime-derived readiness.
- [x] (2026-11-14) M4D implementation: remove Fiona/GDAL parsing from the
      production API image after
      exact artifact parity, containment, dependency, and rollback gates pass.
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
- [ ] M6: scoped validation and exact-image evidence pass, but independent final
      review of `fe5ac7c1c` returned FAIL/HOLD. Remediation, requalification,
      re-review, GitHub disposition, and separately authorized rollout remain.
- [x] (2026-11-14) Implement the approved fail-closed remediation: asynchronous
      cancelable parser execution; exact SHP/SHX/DBF cardinality validation;
      startup parser canary; provenance/reproducibility checks; a conservative
      aggregate resource envelope; and deploy-time readiness with service
      takedown on failure. Focused requalification and independent re-review
      remain.
- [x] (2026-11-14) Rebuild release-mode candidate from committed revision
      `21a12c9d0`, validate exact-image provenance, hardening, output semantics,
      single-flight near-ceiling rejection/recovery, cleanup, and persist pinned
      Syft/Grype reports. Independent re-review remains.
- [x] (2026-11-14) Independent remediation re-review returned FAIL/HOLD. Code,
      correctness, QA, security, and operations retained cancellation/event-loop,
      effective-envelope, early-Rust-limit, deploy-execution, dirty-build,
      semantic/resource-matrix, and Medium-advisory disposition findings.
- [x] (2026-11-14) Implement and qualify the second remediation at
      `be7848eb7`: cancellation-safe offload ownership, responsive event loop,
      startup envelope enforcement, early Rust limits and multipart validation,
      executable deploy takedown/clean-input gates, expanded semantic/resource
      fixtures, runtime pip removal, and all 42 prior unique Medium advisory
      dispositions. Exact image `sha256:553a8a1c00468cdc28cc78bb98ef47382e6179be33a55b5c026d6605e7ff39a8`
      passed local requalification; independent re-review remains.
- [x] (2026-11-14) Resolve the second re-review blockers at `ec1916b23`:
      repeated cancellation ownership, inspect/relay/cleanup event-loop
      offloads, fail-closed early provenance failure, pre-allocation vertex
      limits, Fiona-compatible homogeneous MultiPatch output, and the missing
      semantic/encoding/resource regressions.
- [x] (2026-11-14) Rebuild and locally qualify exact image
      `sha256:196e83b85b1c88e09999de481fdfc3aee03893e58f751ea6146c9776a99bb5bb`.
      GeoJSON/GeoParquet semantic readback, live aggregate-envelope behavior,
      hardening, child limits, cleanup, provenance, Syft, and Grype passed.
      Independent final re-review returned FAIL/HOLD with cancellation-error,
      periodic-janitor, effective-Compose, recovery-precedence, multi-group
      MultiPatch, and multipart PolylineM findings.
- [x] (2026-11-14) Resolve those findings at `f9b92459e`, expand the retained
      regressions, and requalify exact image
      `sha256:c1f1e84d6beec7562fc184ab9b5ed48398bb955d938aa139768fcea7da777361`.
      Parsed Point and multi-group MultiPatch GeoJSON/GeoParquet, live limits,
      saturation, cleanup, provenance, Syft, and Grype passed. Independent
      final-2 re-review returned HOLD with mutable-preset/orphan-takedown and
      parser-descendant-drain findings.
- [x] (2026-11-14) Close those findings at `4587308ff`: bind deployment intent
      to installed preset paths, stop/verify labeled orphan containers without
      the mutable service definition, promote exit-88 recovery guidance, and
      drain SIGTERM-ignoring parser descendants before releasing ownership.
- [x] (2026-11-14) Rebuild and locally qualify exact final-3 image
      `sha256:8c9acdd292a80355c708823f98d3651484667856abfd35b0a28af2b4a3cfc3cf`.
      Hardened runtime, provenance, Point conversion, cleanup, tests, Syft, and
      Grype passed. Independent final-3 re-review returned HOLD on repeated
      cancellation, full-preset render failures, and read-only preset-query
      mutation.
- [x] (2026-11-14) Close those findings at `a6be89141`: shield process-group
      drainage through repeated cancellation, fail closed on every full-preset
      render/contract failure, preserve read-only and targeted scope, retain
      real retry exit status, and catalogue exit-88 recovery.
- [x] (2026-11-14) Rebuild and locally qualify exact final-4 image
      `sha256:b9e78b16718911ff16dc213b27d719477d95880ebcdca500cc858cea13c05ae8`.
      Hardened runtime, provenance, Point conversion, cleanup, tests, Syft, and
      Grype passed.
- [x] (2026-11-14) Independent final-4 code, correctness, QA, operations, and
      security re-review passed with zero findings. #656 is ready to close as
      superseded by GDAL/Fiona removal, explicitly not as second-sandbox proof.
      Production rollout remains separately authorized.
- [x] (2026-11-14) At operator request, comment on and close #656 as not
      planned/superseded. The closure records the same-container residual and
      explicitly does not claim second-sandbox conformance.
- [x] (2026-11-14) Close #655 after strict JSON IPC acceptance; update #656 with
      exact Rust-CLI evidence and retain it open for independent residual-risk
      acceptance.

- [x] (2026-11-16) Recover the 20 commits dropped by rebase, preserving newer
      master history and unrelated working changes. Restore the accepted Rust
      implementation and documented second-sandbox decision.

## Surprises & Discoveries

- Cancellation of an `asyncio.to_thread` awaiter does not stop its decode/
  Shapely thread. The request can release its single-flight slot and remove
  scratch while that thread still consumes parent memory; single-flight must be
  retained through bounded thread completion.
- Setting concurrency/resource defaults is not an invariant while production
  environment overrides can exceed them. Readiness must validate the complete
  effective envelope.
- The Rust CLI applies resource limits after its preliminary hostile SHP scan.
  Limits must precede all attacker-controlled traversal, and the scan must stop
  at the feature ceiling rather than allocate before checking.
- A malformed multipart record whose first part offset was one passed the Rust
  crate and silently dropped point zero. Independent pre-parser part-table
  validation now requires offset zero followed by strictly increasing in-range
  offsets and rejects unknown MultiPatch part codes.
- The inherited system pip remained in the Python base even after pip was
  removed from the application virtual environment. Removing both system and
  venv pip from the final runtime eliminated five Medium and two lower-severity
  advisory IDs without changing request behavior.
- Linux truncates a process `comm` name to 15 characters. Exact-image limit
  observation must match `shape_parser_cl`, or use the executable path, rather
  than assume the full `shape_parser_cli` name appears in `/proc/*/comm`.
- The newer Grype database added Unknown CVE-2026-91094 for dpkg source-package
  unpacking. The image/package set did not add a High or Medium ID; dpkg is not
  invoked and attacker Debian source packages are not accepted by this service.

- Independent M6 review reproduced silent feature loss when SHP contains an
  extra valid record not represented by SHX/DBF. Zipping shape and DBF iterators
  hides the extra shape; exact stream cardinality and SHX entry validation are
  required.
- The synchronous child wait runs on the sole ASGI event loop. The child timeout
  bounds duration, but client cancellation, concurrent health, and request-level
  cleanup cannot execute while `communicate()` blocks.
- Individually valid scratch, parser, upload, payload, and container limits do
  not yet establish a safe aggregate memory invariant beneath the 1 GiB cgroup.
- Exact-image provenance exposed a useful distinction: the candidate passed its
  own binary binding but was built from worktree content whose `Cargo.toml` does
  not match commit `fe5ac7c1c`. Requalification must start from the committed
  tree and inject the released revision through the canonical deploy path.

- Fiona has no non-GDAL parser backend; Pyogrio also uses GDAL. The existing
  strict JSON payload means M4 does not require Fiona API compatibility: a Rust
  parser can preserve the internal payload contract instead. The Rust
  `shapefile` crate supports the required shape families, including Z/M and
  MultiPatch, and its current reader includes explicit malformed-allocation and
  record-size overflow hardening. This is candidate evidence, not dependency
  approval; WEPPpy fixture parity and hostile-input evaluation remain mandatory.
- A Python extension imported by the API would make parser panic, hang,
  allocation, and unsafe-code failures API-process failures. A small service-local
  Rust executable avoids that coupling while retaining a short-lived child,
  strict JSON result, and hard resource limits.
- The crate accepted a forged SHP file-length header and classified a
  counterclockwise first polygon ring as an inner ring. WEPPpy now validates
  SHP/SHX magic, version, and declared length before parsing, and consistently
  inverts ring classification when the first ring establishes reversed
  orientation. Both discoveries are retained as direct regressions.
- A low `RLIMIT_AS` probe terminated through allocation failure without
  publishing output. The CLI now also sets `RLIMIT_CORE=0` before hostile
  parsing so a panic/abort/resource kill cannot create a core artifact.
- The final Python slim digest contained two reachable zlib High findings with
  a fixed Debian security build. The runtime installs that exact fixed zlib;
  the remaining High scanner records describe command, privileged-local,
  SQLite extension, gettext environment, Perl document/archive, or unused C++/
  glibc function paths outside this service contract and require final security
  review rather than being hidden.

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

Recovery addendum (2026-11-16): the November 15 rebase retained the soils
commit but dropped the Rust-parser history after `19c0dc107`. The recovered
fail-closed parser shutdown also conflicts with newer full-stack rollback,
which otherwise restarts and checks every retained service.

## Decision Log

- Decision: retain the 37 post-removal unique Medium advisories only under the
  ID-by-ID request-path dispositions in the second-remediation evidence; remove
  runtime pip instead of accepting its five Medium findings.
  Rationale: the retained findings concern APIs, extensions, tools, services, or
  privileges absent from the fixed converter path. Pip has no runtime purpose,
  so removal is smaller and stronger than a non-reachability exception. Any
  command, parser-linkage, input, privilege, mount, locale, or role change
  invalidates the affected disposition.
  Date/Author: 2026-11-14, Codex pending independent security acceptance.

- Decision: if the candidate cannot satisfy its security, provenance, startup,
  or post-activation readiness gates, leave `shape-converter` stopped and verify
  that no instance is running.
  Rationale: the operator explicitly prefers loss of converter availability over
  restoring the GDAL/Fiona implementation or operating an unqualified Rust
  parser. The canonical deploy path therefore treats build/activation/readiness
  failure as a service takedown, not rollback. This authority applies only to
  `shape-converter`; it does not authorize production deployment or changes to
  other services.
  Date/Author: 2026-11-14, operator and Codex.

- Decision: admit one active inspect or conversion request per service and per
  client by default.
  Rationale: parser address-space, request scratch, retained input, decoded JSON,
  geometry, and serialized output ceilings form a conservative envelope only
  when requests cannot multiply them concurrently beneath the 1.5 GiB cgroup.
  Raising concurrency requires a revised resource ADR and exact-image concurrent
  near-ceiling proof; availability does not override the fail-closed invariant.
  Date/Author: 2026-11-14, Codex under the operator-approved secure-or-stop
  direction.

- Decision: implement M4 as one lightweight service-local Rust CLI crate, not as
  a `wepppyo3` component, Python extension, or new parser microservice.
  Rationale: the operator set the goal to replace GDAL/Fiona with a safer,
  narrow-format parser. A CLI preserves process isolation, timeout/kill, fixed
  exit codes, strict JSON IPC, and enforceable CPU/memory/file/output limits
  without adding a service, protocol, network, shared volume, or deployment
  topology. The crate preserves the current strict JSON response schema and may
  use ordinary internal modules without creating a separately published library.
  The existing dedicated GDAL image remains a parity oracle until the Rust
  candidate passes all gates.
  Date/Author: 2026-11-14, operator and Codex.

- Decision: amend the #656 threat model rather than claim a second sandbox.
  Rationale: replacing the memory-unsafe, broad-driver GDAL/Fiona parser removes
  the failure class that motivated the second sandbox. The Rust CLI remains in
  the API container and therefore does not contain arbitrary code execution from
  that container's UID, mounts, or network. This residual risk is explicit and
  requires independent security review and operator acceptance before #656 may
  close as superseded by parser replacement. This authorization does not permit
  a queue, datastore, Docker socket, privileged launcher, new service, or silent
  Python/PyO3/GDAL fallback.
  Date/Author: 2026-11-14, operator and Codex.

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

- Decision: the original second-sandbox requirement is superseded for M4 only
  after the Rust cutover gates pass.
  Rationale: both user-namespace unshare and Bubblewrap failed under the exact
  non-root, capability-free, read-only, no-new-privileges constraints. That
  retained evidence rules out the smallest namespace mechanisms without weakening
  outer protections. The operator chose parser replacement plus bounded CLI
  execution instead of topology escalation. Until GDAL/Fiona is absent from the
  production parsing path, the existing second-sandbox finding remains open.
  Date/Author: 2026-11-14, operator and Codex.

- Decision: do not choose a compression-ratio threshold in this scaffold.
  Rationale: compressed-upload, total-uncompressed, member, scratch, parser-input,
  and output limits already bound the resource exposure. A ratio-only cutoff can
  reject small legitimate highly compressible datasets without lowering those
  ceilings. Because no numeric default/formula changed, no ADR is required; any
  future ratio remains a new governed decision.
  Date/Author: 2026-11-14, Codex under the operator-approved package execution.

- Decision: ship an adjacent executable-specific JSON provenance sidecar.
  Rationale: the operator requested provenance similar to the jimf-cligen532
  pattern. `shape_parser_cli.json` binds binary hash/size/version/ELF identity,
  source manifest and revision, Cargo lock, compiler, command, and build time.
  Build and readiness validate the pair. The sidecar is not a signature; the
  immutable image digest remains the authenticity boundary.
  Date/Author: 2026-11-14, operator and Codex.

- Decision: validation is limited to tests and runtime probes that exercise the
  changed boundaries; no full repository suite is required.
  Rationale: explicit operator direction and the package has a bounded service
  surface with direct security and semantic acceptance checks.
  Date/Author: 2026-11-13 Pacific, operator; recorded by Codex 2026-11-14 UTC.

- Decision: retain the final image only if early release-provenance failure uses
  the same secure-or-stop behavior as post-build qualification failure.
  Rationale: a dirty or unprovable candidate cannot justify leaving an older
  converter running. Stop failure and inability to verify stopped state both use
  distinct exit 88; no GDAL/Fiona fallback is restored.
  Date/Author: 2026-11-14, operator direction implemented by Codex.

Recovery decision (2026-11-16): merge the original reviewed history instead of
recreating its changes. During failed cutover, restore the other retained
services with an explicit service list and `--no-deps`; keep shape-converter
stopped. Retain the RQ fence if parser shutdown cannot be verified.

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
This outcome did not change the then-open second-sandbox or deployment gates.
The later Rust CLI amendment replaces the sandbox objective only after the full
GDAL/Fiona removal and residual-risk acceptance gates pass.

M4 is implemented and locally validated. The service-local Rust parser matches
the retained Fiona/GDAL oracle for the accepted semantic matrix; CPU, memory,
file, output, input, feature, vertex, timeout, and cleanup boundaries have direct
evidence; readiness validates the executable/sidecar pair and executes a real
fixture; and the exact image cannot load Fiona/GDAL. The package remains open
only for genuinely independent final review, GitHub disposition, and separately
authorized rollout. No production deployment occurred.

The first M6 independent review returned FAIL/HOLD. The remediation now makes
the parser wait asynchronous and cancellation-safe, rejects mismatched physical
SHP/SHX/DBF streams, validates sidecar source-manifest consistency, pins Debian
package resolution, reduces overlapping resource ceilings, runs its real parser
canary once at startup, and makes the canonical deployment stop the converter on
candidate failure. This is implementation status, not independent acceptance;
the package and #656 remain open pending independent re-review.

The remediation candidate at `21a12c9d0` has now passed local exact-image
requalification. See the
[receipt](../../artifacts/20261114_rust_cli_remediation_requalification.md).
This closes the local evidence portion only; independent re-review and rollout
authorization remain open, so the package is not complete.

The second remediation at `be7848eb7` closes every finding retained by that
re-review and passes local exact-image requalification. See the
[second-remediation receipt](../../artifacts/20261114_rust_cli_second_remediation_requalification.md)
and [Medium dispositions](../../artifacts/20261114_rust_cli_medium_advisory_dispositions.md).
The work exposed and fixed one additional silent multipart-offset data-loss
case. The final runtime removes pip, adds no scan advisory ID, and retains
explicit dispositions for all 37 remaining unique Medium IDs. Independent
second re-review, #656 disposition, and separately authorized rollout remain
open; no production action occurred.

The final remediation at `ec1916b23` closes the blockers retained by the second
re-review and passes local exact-image qualification as
`sha256:196e83b85b1c88e09999de481fdfc3aee03893e58f751ea6146c9776a99bb5bb`.
The exact image preserves the 0 Critical result and unchanged unique High and
Medium sets. Independent final re-review is in progress; this local outcome does
not authorize publication, deployment, or #656 closure.

Independent review of `ec1916b23` returned FAIL/HOLD and identified late-worker
error precedence, blocking periodic janitor cleanup, effective-Compose release
gate bypass, recovery status precedence, multi-group MultiPatch drift, and a
multipart PolylineM coverage gap. Final-2 remediation `f9b92459e` closes those
paths and passes exact-image qualification as
`sha256:c1f1e84d6beec7562fc184ab9b5ed48398bb955d938aa139768fcea7da777361`.
Independent final-2 re-review remains; no production action occurred.

Independent final-2 review found that mutable Compose could still downgrade a
full preset before the release gate, that the damaged definition could not stop
an orphaned converter, and that leader exit could hide a SIGTERM-ignoring parser
descendant. Commit `4587308ff` closes all three paths and promotes the exit-88
operator runbook. Exact image
`sha256:8c9acdd292a80355c708823f98d3651484667856abfd35b0a28af2b4a3cfc3cf`
passes local final-3 qualification with unchanged advisory IDs. Independent
final-3 re-review remains; no production action occurred.

Independent final-3 review retained repeated-cancellation drainage, unguarded
full-preset render failures, and preset-query mutation during read-only/targeted
work. Commit `a6be89141` closes those paths and catalogues operator recovery.
Exact image
`sha256:b9e78b16718911ff16dc213b27d719477d95880ebcdca500cc858cea13c05ae8`
passes local final-4 qualification with unchanged advisory IDs. Independent
final-4 re-review was the remaining gate; no production action occurred.

Independent final-4 re-review passed in all five lanes with no findings. The
accepted residual is a bounded Rust parser process in the API container, not a
second sandbox. #656 may close as superseded by removal of the GDAL/Fiona
failure class. No image publication, issue mutation, or production action
occurred during review. The operator subsequently authorized #656 closure; it
was commented and closed as not planned/superseded. No production action
occurred.

Independent re-review of `2bbf8498e` returned FAIL/HOLD. See the
[consolidated review](../../artifacts/20261114_rust_cli_remediation_independent_re_review.md)
and [security review](../../artifacts/20261114_rust_cli_remediation_security_re_review.md).
The local exact-image receipt remains valid evidence, but it does not override
the retained findings. #656 and rollout remain blocked.

Recovery addendum (2026-11-16): source history and the accepted architecture are
restored. The parser, parser tests, and dedicated Dockerfile match the accepted
tip byte for byte. See `../../artifacts/20261116_history_recovery.md` for the
recovery receipt. This recovery does not deploy a production image.

## Context and Orientation

Work from `/workdir/wepppy`. Read root `AGENTS.md`, `tests/AGENTS.md`,
`docker/AGENTS.md`, the work-package standard, and the canonical shape-converter
contract before editing. Preserve unrelated dirty files and do not create or
switch branches.

`wepppy/microservices/shape_converter/archive_validation.py` validates and
extracts ZIP members into a request root. `inspect.py` selects a shared-prefix
`.shp/.shx/.dbf` dataset and reads bounded shapefile, DBF, and projection
metadata. `convert.py` invokes `convert_parser_worker.py` with a hard timeout and
process-group termination. The worker currently opens through Fiona/GDAL and
writes strict JSON through `parser_ipc.py`; the parent validates byte, depth,
value, schema, geometry, and quota constraints before object construction.
`app.py` readiness still compares declared sandbox-mode strings and
toolchain/scratch availability, which is not effective containment evidence.

The current production Compose definition hardens the whole service container
and attaches it to an internal network. The parser process still shares that
container's user, mounts, namespace, and service process context. M4 adds one
service-local Rust binary crate at
`wepppy/microservices/shape_converter/rust/shape_parser_cli`. The Python API
launches the binary against the already admitted request-local components, gives
it a single output path, enforces a hard wall-clock timeout, and validates the
existing strict JSON payload. The CLI is a reliability and resource boundary,
not a second security sandbox; arbitrary code execution would retain the outer
container's UID, mounts, and network authority.

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

## Rust parser CLI amendment (2026-11-14)

The operator selects a lightweight Rust CLI owned by the shape-converter service
instead of a `wepppyo3` component, second parser sandbox, or microservice. Add one
binary crate at `wepppy/microservices/shape_converter/rust/shape_parser_cli`.
Use private Rust modules or a crate-local library target only when they materially
improve direct testing; do not create a public Rust API or Python binding. The
production WEPPpy API must never import or call the parser in-process. No new container,
network protocol, socket, queue, datastore, daemon, shared volume, Docker socket,
or privilege is authorized.

The CLI accepts only the selected `.shp` path, its same-prefix admitted
components, one output path inside the same request scratch directory, and the
existing feature/vertex/payload limits. It returns no Python object. Success is
an atomically published strict JSON payload using exactly `properties`,
`geometries`, `source_bounds`, and `source_crs_wkt`; failure uses fixed exit codes
and generic bounded stderr. The parent discards diagnostics, validates the output
again through `parser_ipc.py`, and never falls back to Fiona/GDAL or PyO3.

The CLI applies ratified process limits before reading hostile component data:
address-space or equivalent memory, CPU seconds, output file size, open files,
and any other limit proven reliable in the production image. The Python parent
creates a new process group, enforces the existing wall-clock deadline, kills the
entire group on timeout/cancellation, rejects partial output, and removes request
scratch. The outer container retains its non-root UID, read-only root, dropped
capabilities, no-new-privileges, PID/memory/CPU limits, hardened tmpfs, no secrets
or host data mounts, and internal/no-egress network policy.

The external Rust `shapefile` crate and its DBF/encoding dependency graph require
the repository dependency-evaluation gates before adoption. The evaluation must
inspect unsafe code and transitive dependencies, malformed-input allocation and
overflow behavior, release/maintenance history, license, encoding behavior, and
all required geometry families. The retained Fiona/GDAL worker and exact d515
image are development parity oracles only until cutover. After activation,
rollback may select the last independently approved Rust-CLI image or disable
conversion; it must not silently restore GDAL/Fiona parsing.

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

Treat the retained unshare and Bubblewrap failures as the completed evidence for
not pursuing a nested second sandbox. Evaluate the Rust `shapefile` crate and the
single `shape_parser_cli` crate under
`docs/standards/dependency-evaluation-standard.md`. Prototype the standalone CLI
from the WEPPpy service-local crate in the exact hardened API image. Demonstrate process-
group timeout and descendant termination; enforceable wall-time, CPU, memory,
open-file, output, and payload limits; cleanup; API survival after parser panic,
abort, malformed input, and limit exhaustion; and exact shape/DBF/CRS semantics
against the retained oracle. Stop before production integration if dependency,
parity, resource, recovery, or residual-risk review fails; do not weaken outer
container protections to compensate.

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
- Add Rust CLI probes for allocation and CPU exhaustion, output/file/open-file
  limits, panic/abort, descendant timeout, partial output, API recovery, and
  cleanup. Retain the historical sandbox probes as evidence explaining why this
  plan explicitly accepts same-container authority rather than claiming it is
  denied.

Tests must invoke the actual changed serializer, archive extractor, Rust parser,
CLI launcher, and limit mechanism where those are the failure boundaries. The
retained oracle tests invoke Fiona/GDAL only for parity before cutover. Mocks may
isolate unrelated HTTP but cannot stand in for a claimed resource or parser
boundary.

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

### Milestone 4: Rust parser replacement and bounded CLI execution

M4A establishes the dependency and CLI contracts before integration. Add one
reviewed binary crate at
`wepppy/microservices/shape_converter/rust/shape_parser_cli`. Evaluate the Rust
`shapefile` crate and its full dependency graph under the WEPPpy dependency
standard. Freeze CLI arguments,
component and aggregate byte caps, fixed exit/error codes, process limits, and
the existing strict JSON success schema in cross-repository golden fixtures.
Record exact behavior for point, multipoint, polyline, polygon, Z/M variants,
MultiPatch, null shapes, DBF primitive/null/date/logical values, deleted records,
encodings, `.prj`, `.cpg`, bounds, ring orientation, record alignment, malformed
indexes, truncation, and unsupported values. A candidate that cannot preserve a
ratified behavior must fail the gate rather than silently normalize it.

M4B implements parsing inside the lightweight CLI crate without Python-extension
or service concerns. Private modules accept bounded component readers and return
Rust types that serialize exactly to the current parser JSON schema. Enforce
feature, per-feature vertex, nesting,
finite-number, allocation, and diagnostic limits during parsing, before large
allocation where possible. Add unit, property, and bounded fuzz-corpus tests for
valid parity and malformed length/count/offset/part/DBF inputs. Keep evidence
labels precise: Rust memory safety narrows the native attack surface but does not
prove freedom from denial-of-service, logic, dependency, or unsafe-code defects.

M4C integrates `shape_parser_cli` as a standalone Rust binary, not a Python
extension. It accepts the selected `.shp` and output paths plus explicit limits,
discovers only same-prefix admitted sidecars, applies per-process resource limits
before parsing, invokes its private parser modules, and atomically writes bounded JSON.
It never opens URLs, loads format plugins, spawns helpers, accepts arbitrary
driver names, or emits uploaded values/paths in diagnostics. Unit tests prove
that every limit is active rather than merely configured.

In WEPPpy, replace `convert_parser_worker.py` production invocation with a narrow
CLI launcher adjacent to `parser_ipc.py`. It creates a new process group, passes
only request-local paths and numeric limits, discards stdout/stderr, maps fixed
exit codes to canonical errors, enforces the wall-clock deadline, kills the whole
group on timeout/cancellation, validates the bounded JSON output, and cleans all
scratch. Do not retain a direct Fiona/GDAL or in-process PyO3 fallback. The
current Fiona/GDAL path may coexist only in test/parity tooling that cannot be
selected by production configuration or make readiness green.

M4D replaces sandbox-label comparison with effective parser readiness. The API
performs a freshness-bounded miniature parse through the exact CLI executable,
process limits, timeout, JSON validation, and cleanup path used by conversions.
The public response reports only ready/not-ready; detailed binary identity,
limit enforcement, timing, and failure evidence stays in safe logs/receipts.
Hostile probes demonstrate that malformed input, excessive allocation, CPU
exhaustion, oversize output, panic/abort, timeout, and cancellation do not leave
partial output or scratch and that the outer service recovers according to the
documented container restart/health contract.

Milestone acceptance: direct Rust and cross-language golden tests pass; the exact
image proves active wall-time, CPU, memory, open-file, output, payload, feature,
and vertex limits; timeout/cancellation kill the parser process group; readiness
fails closed for an absent, stale, incompatible, or failing CLI; valid GeoJSON
and GeoParquet artifact readback matches the retained GDAL/Fiona oracle; the
production image and source contain no Fiona/GDAL hostile parsing or in-process
PyO3 parser path; and independent correctness, QA, operations, and security
reviews approve the explicit same-container residual risk. Only then may #656 be
closed as superseded by removal of the GDAL/Fiona failure class, not as proof of
a second sandbox.

### Milestone 5: Exact transitional and Rust-CLI dependency evidence

Retain the already qualified GDAL/Fiona image identity, linkage, SBOM/scan, and
request-path dispositions as the transitional oracle. Build and inventory the
exact API image containing `shape_parser_cli` but no Fiona/GDAL parser libraries.
Record source revisions, Cargo lock identity, `shape_parser_cli --version`, crate
provenance, unsafe-code inventory, native linkage, image digest, SBOM, scan, and
runtime configuration. Triage findings against the actual parser, encoding,
JSON, CLI, and output paths. Do not claim that Rust, a clean scan, or absence of
GDAL proves security.

If a reachable Critical issue is confirmed, mark the package blocked at the
release gate, retain the evidence, and request a separate remediation decision.
Do not change dependency versions under this plan. High findings require the
security review's explicit disposition and operator decision under the package
closure policy.

Milestone acceptance: reproducible transitional and final receipts, no hidden
dependency or native linkage, complete reachable-risk dispositions, and evidence
that the production image cannot load Fiona/GDAL or the parser through PyO3.

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

Independent review result (2026-11-14): FAIL/HOLD. Retained review artifacts
identify High blockers in parser cancellation/event-loop availability and
deploy readiness/rollback, plus Medium correctness, aggregate-memory,
provenance, semantic-matrix, vulnerability-disposition, and reproducibility
findings. Do not close #656 or roll out until remediation and independent
re-review pass.

## Concrete Steps

Run from `/workdir/wepppy`.

Baseline and change-scoped iteration:

    wctl run-pytest tests/shape_converter/unit/test_archive_validation.py tests/shape_converter/unit/test_inspect_endpoint.py tests/shape_converter/unit/test_convert_endpoint.py tests/shape_converter/unit/test_cleanup_lifecycle.py --maxfail=1
    wctl run-pytest tests/shape_converter/unit/test_health_routes.py tests/shape_converter/unit/test_runtime_hardening.py --maxfail=1
    wctl run-pytest tests/shape_converter/integration/test_inspect_api.py tests/shape_converter/integration/test_convert_api.py tests/shape_converter/integration/test_runtime_hardening_api.py --maxfail=1

From
`/workdir/wepppy/wepppy/microservices/shape_converter/rust/shape_parser_cli`,
validate the service-local Rust parser:

    cargo fmt --check
    cargo test --locked
    cargo tree --locked
    cargo build --release --locked

Run the new cross-boundary WEPPpy tests from `/workdir/wepppy`:

    wctl run-pytest tests/shape_converter/unit/test_rust_parser_cli.py tests/shape_converter/unit/test_parser_ipc.py --maxfail=1
    wctl run-pytest tests/shape_converter/integration/test_parser_ipc_semantics.py --maxfail=1
    wctl run-pytest tests/docker/unit/test_project_config_rollout_contract.py --maxfail=1
    wctl run-pytest tests/scripts/test_deploy_production_execution.py --maxfail=1

Source and hygiene checks:

    rg -n "pickle|fiona\.open|enabled_drivers|dataset\.driver|SANDBOX_MODE|subprocess\.Popen|shape_parser_cli" wepppy/microservices/shape_converter tests/shape_converter docker
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

If and only if the implementation changes imports or test stubs:

    wctl check-test-stubs

Transitional oracle and Rust-CLI candidate evidence:

    docker compose -f docker/docker-compose.dev.yml build shape-converter
    docker compose -f docker/docker-compose.dev.yml up -d shape-converter caddy
    docker exec wepppy-shape-converter /usr/local/bin/shape_parser_cli --version
    docker inspect wepppy-shape-converter
    docker exec wepppy-shape-converter /opt/venv/bin/python -c "import importlib.util; assert importlib.util.find_spec('fiona') is None"

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
mismatches, malformed Rust record lengths/counts/offsets/parts/DBF values,
allocation exhaustion, CPU exhaustion, output growth, panic/abort, timeout,
cancellation, descendant survival, and partial output. Each must fail at the
expected boundary with a canonical bounded error and empty request scratch after
response; the API must remain healthy or recover through the documented outer-
container restart contract.

An HTTP 200, a process exit code, a matching environment string, a Rust
implementation, or an output file's existence is insufficient. Exercise every
CLI and outer-container resource limit, verify that no GDAL/Fiona or in-process
parser path exists, and parse output semantics. Do not state "fixed" or close
#656 before the exact Rust-CLI candidate passes its amended evidence boundary and
the residual-risk review is accepted.

## Idempotence and Recovery

All tests and prototypes use disposable request roots, fixtures, containers, and
canaries. Re-running them must not mutate committed fixtures, shared projects, or
production data. Preserve useful failed-attempt logs/receipts without retaining
hostile uploaded content or secrets.

Serializer and Rust-CLI changes must fail closed. Rollback cannot silently restore
pickle IPC, direct Fiona/GDAL parsing, or an in-process PyO3 parser path. If the
last approved Rust-CLI image cannot be restored, disable conversion until a safe
candidate is active. Archive threshold rollback follows its ADR. No persisted
run-data migration exists.

## Artifacts and Notes

Retain under this package:

- baseline and final source/runtime inventories;
- contract checkpoint and independent review dispositions;
- compression-policy ADR link and Rust parser/resource-limit dependency evaluation;
- bounded red/green transcripts and fixture manifests/hashes;
- semantic parity report for GeoJSON/GeoParquet;
- CLI identity, limit, denial, timeout, process-group kill, and cleanup receipts;
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
Use existing `ShapeConverterError`, `ArchiveLimits`, `RequestScratchLayout`,
strict `parser_ipc.py` validation, and safe logging/error utilities.

Add one binary crate at
`wepppy/microservices/shape_converter/rust/shape_parser_cli`. It owns
Shapefile/DBF parsing, bounded semantic normalization, CLI validation, early
resource-limit application, fixed exit codes, atomic bounded JSON publication,
version reporting, and self-test behavior. Keep parser modules private to the
crate unless a crate-local library target is justified for tests. It is not a
WEPPpy-wide Rust API and is not installed as a Python module.

The API owns process-group creation, wall-clock deadline, cancellation/kill,
scratch cleanup, and validation of every success response through the existing
Python decoder. The CLI receives only request-local paths and numeric limits. The
Rust `shapefile` crate and any new resource-limit dependencies require explicit
dependency-evaluation evidence and lockfile review before merge.

The current GDAL/Fiona versions remain frozen in the transitional oracle. They
must not be copied into the final production image. PyProj/Shapely may remain in
the API for validated CRS/output operations, but raw Shapefile bytes must reach
only `shape_parser_cli`.

Revision note, 2026-11-14: initial scaffold created from the 2026-11-13 security
contract review. Added explicit GDAL-upgrade deferral, bounded topology, governed
compression-policy decision, direct artifact evidence, and #655/#656 closure
gates.

Revision note (2026-11-14): recorded scoped baseline, direct red observations,
failed sandbox prerequisite, and independent review; retained M0 stop gate.

Revision note (2026-11-14, independent slice): operator-approved sequencing is
implemented; record local evidence separately from remaining sandbox/release gates.

Revision note (2026-11-14, Rust M4): replaced the failed second-sandbox plan with
an operator-selected service-local lightweight Rust CLI. The revision
sets parser replacement, not arbitrary-code containment, as the goal; prohibits
production in-process PyO3/GDAL fallback; defines CLI/resource/readiness gates;
and retains the qualified GDAL image only as a parity oracle before cutover.

Revision note (2026-11-14, ownership correction): removed `wepppyo3` and a
separate parser-core crate from M4. The parser is one shape-converter-owned Rust
binary crate with private modules, minimizing release and repository coupling.

Revision note (2026-11-14, M4 implementation): implemented the CLI and adjacent
JSON provenance sidecar, removed the Fiona worker/runtime, proved resource and
semantic behavior, patched the final image's fixed zlib build, and retained exact
SBOM/scan evidence. Independent signoff and rollout remain outside local proof.

Revision note (2026-11-14, M6 remediation): recorded the operator's explicit
fail-closed availability decision and implemented asynchronous cancellation,
record cardinality checks, startup-cached readiness, reproducible provenance,
aggregate resource limits, and deployment takedown behavior. Exact candidate
evidence and independent re-review remain required.

Revision note (2026-11-14, M6 second remediation): preserved thread ownership
through cancellation, moved blocking conversion work off the event loop,
enforced the effective startup envelope and early Rust limits, rejected malformed
part tables, execution-tested deploy takedown and clean provenance, completed the
semantic/resource matrix, removed runtime pip, and retained all Medium advisory
dispositions plus exact-image evidence.
