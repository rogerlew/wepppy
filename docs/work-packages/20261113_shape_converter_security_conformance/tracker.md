# Tracker - Shape-converter security conformance closure

## Quick Status

**Timezone**: UTC
**Last updated**: 2026-11-14 (M6 final-2 remediation qualified)
**Current phase**: M6 independent final-2 re-review required
**Security impact**: high
**Starting revision**: `ab205eacc5dc09e5920afa38df4c1fda50192f96`
**Dedicated-image implementation**: `73ed430d4`
**GitHub issues**: [#655](https://github.com/rogerlew/wepppy/issues/655),
[#656](https://github.com/rogerlew/wepppy/issues/656)
**Parser decision**: replace production GDAL/Fiona parsing with a bounded,
service-local lightweight Rust CLI; retain the dedicated GDAL image only as a
pre-cutover oracle

## Task Board

- [x] Scaffold package, active ExecPlan, failure-class assessment, and four
      independent review gates.
- [x] Cross-reference the two high findings against open, severity-tagged GitHub
      issues #655 and #656.
- [x] Record the operator decision to defer GDAL upgrades.
- [x] M0: run nine scoped baseline modules (136 passed) and direct IPC/alias/prefix probes.
- [x] M0: complete the remaining red matrix and Rust parser feasibility gate.
- [x] M0: evaluate the proposed Rust parser and resource-limit dependencies.
- [x] M0: reject a ratio threshold and retain existing absolute quotas; no
      parameter/default change means no ADR is required.
- [x] Independent slice contract checkpoint committed before code: `6712ba631`.
- [x] Full M0 parser/compression contract decisions recorded.
- [x] M1: add focused IPC, driver, archive, semantic, provenance, malformed
      binary, and resource-limit tests.
- [x] M2: replace pickle with bounded schema-validated data-only IPC.
- [x] M3 slice: exact driver, NFC/case-fold collisions, and extra prefixes.
- [x] Build and locally qualify the minimal shape-converter-only GDAL 3.12.4/
      Fiona 1.10.1 image; common WEPPpy image unchanged.
- [x] M3 remainder: compression policy and broader semantic validation.
- [x] M4A: evaluate the Rust `shapefile` crate, unsafe/transitive surface,
      semantic coverage, encoding behavior, malformed-input behavior, and CLI
      resource-limit strategy.
- [x] M4B: implement and test the service-local `shape_parser_cli` crate and its
      private parser modules.
- [x] M4C: implement `shape_parser_cli` plus the Python launcher, strict JSON
      contract, process-group termination, and memory/CPU/file/output limits.
- [x] M4D implementation: prove oracle parity and recovery and remove Fiona/GDAL
      from the production parser image/path. Independent residual-risk acceptance
      remains an M6 gate.
- [x] M5 candidate: dedicated image dependency/linkage/scan, resolved Compose,
      and exact-image artifact evidence captured; operator-approved one-worker
      command passes limiter, metadata, conversion, and cleanup qualification.
- [x] Dedicated-image correctness, QA, and security re-reviews pass after the
      one-worker repair; broader M6 and rollout gates remain open.
- [x] M6: run change-scoped shape-converter and production-equivalent gates; no
      full repository or unrelated suite.
- [x] M6: complete independent code, QA, correctness, security, and operations
      reviews of `fe5ac7c1c`.
- [ ] M6: remediate and independently re-review the retained findings; current
      verdict is FAIL/HOLD.
- [x] M6 remediation implementation: asynchronous cancellation-safe parser
      execution, exact SHP/SHX/DBF cardinality, startup canary, strengthened
      provenance/reproducibility, bounded aggregate resource envelope, and
      deploy-time fail-closed service takedown.
- [x] M6 exact-image requalification at `21a12c9d0`: provenance-identical build,
      output readback, single-flight near-ceiling recovery, cleanup, and pinned
      Syft/Grype evidence passed.
- [ ] M6 independent remediation re-review: FAIL/HOLD. Retained findings cover
      cancellation/event-loop ownership, effective resource enforcement, early
      Rust limits, executable takedown proof, clean release inputs, semantic/
      resource coverage, and Medium scan dispositions.
- [x] M6 second remediation: close every retained finding and requalify exact
      image `sha256:553a8a1c00468cdc28cc78bb98ef47382e6179be33a55b5c026d6605e7ff39a8`
      from committed revision `be7848eb7`; 264 shape tests and 50 deploy/Compose
      tests passed (3 environment skips), with no new scan advisory ID.
- [x] M6 independent second re-review of `be7848eb7` and its exact-image
      evidence returned FAIL/HOLD and supplied the final-remediation findings.
- [x] M6 final remediation: close repeated cancellation, remaining ASGI
      blocking phases, early fail-closed deployment, pre-allocation vertex
      enforcement, homogeneous MultiPatch parity, and retained QA gaps; qualify
      exact image `sha256:196e83b85b1c88e09999de481fdfc3aee03893e58f751ea6146c9776a99bb5bb`
      from `ec1916b23`.
- [x] M6 independent final re-review of `ec1916b23` and its exact-image
      evidence returned FAIL/HOLD and supplied the final-2 findings.
- [x] M6 final-2 remediation: close cancellation-error precedence, periodic
      janitor blocking, effective-Compose gate bypass, recovery exit precedence,
      multi-group MultiPatch parity, and multipart PolylineM coverage; qualify
      exact image `sha256:c1f1e84d6beec7562fc184ab9b5ed48398bb955d938aa139768fcea7da777361`
      from `f9b92459e`.
- [ ] M6 independent final-2 re-review of `f9b92459e` and its exact-image
      evidence.
- [x] Close #655 after its strict data-only IPC acceptance passed; comment on
      #656 with final local evidence and keep it open for independent residual-
      risk acceptance.
- [ ] Complete authorized rollout separately; do not imply deployment from local
      or forest1 validation.

## Decisions and Constraints

- Parser output is attacker-controlled after native parsing; executable
  deserialization is forbidden even if the worker normally writes the file.
- JSON is the first IPC candidate because it is data-only and already available;
  its decoder still requires explicit byte, nesting, primitive, finite-number,
  and schema validation.
- Production parsing will use a short-lived standalone Rust CLI in the existing
  hardened shape-converter container. Python must not import the parser through
  PyO3, and no parser service, socket, or new deployment topology is authorized.
- The CLI boundary provides bounded failure and recovery, not containment from
  arbitrary code execution: it retains the container UID, mounts, and network
  authority. Closure therefore requires explicit acceptance of that residual.
- Absolute compressed/uncompressed/member/scratch/parser-input ceilings are the
  expansion policy. No compression-ratio threshold or numeric default is added.
- The installed executable must have adjacent `shape_parser_cli.json`
  provenance. Build and readiness verify executable hash, size, and version
  against it; the immutable image digest remains the authenticity boundary.
- The dependency freeze is superseded only for the dedicated shape-converter
  image. The common WEPPpy image remains unchanged. Every reachable Medium,
  High, or Critical candidate finding requires remediation or explicit operator
  risk acceptance before rollout.
- The final runtime does not include pip. The remaining 37 unique Medium scan
  IDs are governed by the ID-by-ID request-path dispositions in
  `artifacts/20261114_rust_cli_medium_advisory_dispositions.md`; a changed
  command, linkage, input, privilege, mount, locale, or role invalidates them.
- Production rollout is out of scope until separately authorized.
- If build, activation, provenance, startup, or post-activation readiness cannot
  establish the approved parser state, the canonical deployment stops
  `shape-converter` and verifies it is not running. It must not restore
  GDAL/Fiona, PyO3, or another unreviewed parser fallback. This operator decision
  favors converter unavailability over an insecure service and does not affect
  other services.
- The 1.5 GiB cgroup resource model admits one active inspect or conversion
  request globally and per client. Increasing concurrency requires a revised ADR
  and exact-image concurrent near-ceiling evidence.
- Validation is change-scoped by operator direction. Do not run or claim the full
  repository suite; list every focused module and boundary probe that ran.

## Required Evidence

- Baseline source/runtime matrix and retained red tests for each failure class.
- Contract checkpoint SHA and recorded no-threshold compression decision.
- Rust parser dependency/unsafe/transitive evaluation and production-equivalent
  CLI/resource-limit receipt.
- Direct worker IPC rejection and no-side-effect evidence.
- Exact-driver and disguised-format rejection evidence.
- Unicode collision, ambiguous-prefix, compression, malformed-sidecar, semantic,
  timeout, cancellation, and cleanup evidence.
- Valid GeoJSON/GeoParquet semantic parity readback.
- Exact revision, image identity, runtime versions/linkage, and scan disposition.
- Completed code, QA, correctness, and security reviews.

## Timeline

- 2026-11-13 Pacific / 2026-11-14 01:46 UTC: package scaffolded from the
  2026-11-13 contract review; #655 and #656 linked; GDAL upgrade deferred.
- 2026-11-14 05:13 UTC: 136 baseline tests passed; direct IPC/alias/prefix
  gaps reproduced. Namespace prerequisite failed for unshare and Bubblewrap.
  Independent security review supports stopping at M0. See the
  [M0 receipt](artifacts/20261114_m0_baseline_and_sandbox_probe.md).

- 2026-11-14: independent slice approved by operator, contract checkpoint committed,
  184 consolidated tests passed plus 45 IPC-module tests after the last regression
  addition; four disposable-container semantic cases passed. Independent reviews
  approved the slice; full conformance remains open.

- 2026-11-14: operator selected a minimal dedicated image after reviewing whether
  the JSON IPC mitigation could replace sandbox conformance. GDAL 3.12.4 with
  source-built Fiona 1.10.1 is the bounded candidate; this does not waive the
  second-sandbox or deployment gates.

- 2026-11-14 06:56 UTC: reproducible dedicated candidate
  `sha256:d515d75ea603f174aa7b6b36c075f42fb0406cdb17901d60997aa0bbdbb0dff6`
  passed the then-preserved two-worker command, health, CORS, abuse-control,
  GeoJSON, GeoParquet, cleanup, and inert legacy-pickle rejection probes. The
  base digest and Ubuntu snapshot are immutable. Syft/Grype reports 0 Critical,
  1 High, 315 Medium, 13 Low, and 3 Negligible package records; grouped
  request-path non-reachability and evidence hashes are retained for independent
  security review. Trivy's smaller result is supplemental because its matcher
  omitted a known GDAL advisory.

- 2026-11-14: exact two-worker QA blocked the candidate. In-memory rate/in-flight
  limits apply once per worker, and conversion metadata can return 404 when the
  lookup reaches the other worker. The recommended bounded repair is one Uvicorn
  worker; this finding prompted the explicit operator decision recorded below.

- 2026-11-14: operator approved the recommended one-worker repair. Resolved
  Compose locks the full command. Exact-image requalification passed health,
  CORS, GeoJSON, GeoParquet, scratch cleanup, twenty consecutive metadata reads,
  rate outcomes 200/429/429, and held/competing/released inflight outcomes
  200/503/200 without disconnected-client tracebacks.

- 2026-11-14: independent correctness, QA, and security re-reviews passed the
  dedicated-image slice. Persisting complete scan evidence outside `/tmp` remains
  a Low package-closeout provenance item. The then-required second sandbox
  remained a release blocker.

- 2026-11-14: reviewed dedicated-image implementation committed as `73ed430d4`.
  No image publication or deployment occurred.

- 2026-11-14: operator selected replacement of GDAL/Fiona with one lightweight,
  service-local Rust CLI. The CLI remains in the existing container and
  is bounded by wall-time, process-group kill, memory, CPU, open-file, file,
  output, feature, vertex, and IPC limits. This supersedes the proposed second
  sandbox only after full cutover and independent residual-risk acceptance; it
  does not claim arbitrary-code containment. Issue #656 remains open until then.

- 2026-11-14: M4 implementation completed locally. The Rust CLI, strict launcher,
  OS/resource limits, executable-specific JSON sidecar, readiness fixture, and
  minimal no-GDAL/Fiona image are implemented. A 50,000-feature oracle benchmark
  matched normalized semantics; direct memory and CPU probes terminated without
  output. The malformed corpus found and closed SHP/SHX declared-length and
  reversed-ring compatibility gaps. Exact Syft/Grype JSON is retained in package
  artifacts, and the fixed Debian zlib security build replaces the vulnerable
  base version. Final exact image:
  `sha256:d3605b92360eaf65f8c1c2d72bac0c0d9c44a0c096776e4cb7edebbbde1fca41`.
  Independent final review and rollout remain open.

- 2026-11-14 19:28 UTC: independent code, correctness, QA, security, and
  operations reviews of `fe5ac7c1c` returned FAIL/HOLD. Confirmed blockers
  include synchronous parser execution on the sole ASGI worker, silent feature
  loss for mismatched SHP/SHX/DBF records, an unproven aggregate memory
  envelope, missing deploy-time readiness and rollback gates, incomplete
  semantic/resource coverage, and a qualified image not provenance-identical to
  the committed source. #656 remains open; no rollout is authorized.

- 2026-11-14: operator directed that an unsecurable converter be taken down.
  Remediation now uses asynchronous subprocess cancellation and descendant
  termination, validates complete SHP/SHX/DBF streams, tightens the aggregate
  resource envelope, validates provenance internals, runs the real parser canary
  during startup, and makes the canonical deploy path stop and verify the
  converter is down after candidate failure. Focused tests pass except where
  noted in current execution evidence; exact-image qualification and independent
  re-review are still required.

- 2026-11-14: release-mode image
  `sha256:ec4872021957fd5cb37b3a554537051bf5843be533dbb30276a014e328ab3921`
  was built from commit `21a12c9d0`. Provenance/source hashes, startup canary,
  hardening, GeoJSON/GeoParquet readback, empty scratch, and a 235,000-record
  bounded rejection/recovery probe passed. Peak cgroup memory was 453,931,008
  bytes; a competing request received 503; the service remained healthy and was
  not OOM-killed. Exact Syft/Grype reports retain the previously reviewed counts
  and dispositions. No production deployment occurred.

- 2026-11-14: independent code, correctness, QA, security, and operations
  re-review of `2bbf8498e` returned FAIL/HOLD. The exact-image evidence remains
  valid, but #656 and rollout remain blocked. See the consolidated and dedicated
  security re-review artifacts.

- 2026-11-14: second remediation committed as `be7848eb7` and rebuilt as exact
  image `sha256:553a8a1c00468cdc28cc78bb98ef47382e6179be33a55b5c026d6605e7ff39a8`.
  Cancellation ownership, event-loop responsiveness, effective-envelope
  enforcement, early Rust limits, malformed multipart rejection, deploy
  takedown execution, clean release inputs, semantic/resource fixtures, and all
  Medium dispositions are now evidenced. Pinned scanning reports 0 Critical,
  removes all pip findings, and adds no advisory ID. No publication or
  production deployment occurred.
- 2026-11-14: final remediation committed as `ec1916b23` and rebuilt as exact
  image `sha256:196e83b85b1c88e09999de481fdfc3aee03893e58f751ea6146c9776a99bb5bb`.
  Repeated cancellation, remaining ASGI blocking work, early deploy fail-closed
  behavior, pre-allocation vertex enforcement, homogeneous MultiPatch parity,
  and retained semantic/encoding/resource gaps are closed locally. The exact
  image passed GeoJSON/GeoParquet readback, live saturation/limits, cleanup,
  provenance, and pinned scanning. Independent final re-review remains; no
  publication or production deployment occurred.
- 2026-11-14: independent review of `ec1916b23` returned FAIL/HOLD. Final-2
  remediation `f9b92459e` closes cancellation-error precedence, periodic
  janitor blocking, effective-Compose release bypass, compound recovery status,
  multi-group MultiPatch drift, and multipart PolylineM coverage. Exact image
  `sha256:c1f1e84d6beec7562fc184ab9b5ed48398bb955d938aa139768fcea7da777361`
  passed local semantic, saturation, limit, cleanup, provenance, and pinned-scan
  qualification. Independent final-2 review remains; no production action
  occurred.

## Handoff

M4 implementation and final-2-remediation local validation are complete. See the
[dependency evaluation](artifacts/20261114_rust_parser_dependency_evaluation.md)
and final-remediation qualification artifact. No production deployment
occurred; do not infer approval for privileges, a parser service, or topology
changes.

Next checkpoint: obtain independent code, correctness, QA, operations, and
security re-review of `f9b92459e` and exact image `sha256:c1f1e84d6bee...` before
updating #656 or authorizing rollout.
Complete Syft/Grype JSON is retained in package artifacts, and the exact image
proves Fiona/GDAL absence. Keep the common image unchanged and do not deploy.
