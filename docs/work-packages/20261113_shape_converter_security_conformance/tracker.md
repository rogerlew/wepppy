# Tracker - Shape-converter security conformance closure

## Quick Status

**Timezone**: UTC
**Last updated**: 2026-11-14 UTC (reproducible dedicated image locally qualified)
**Current phase**: Dedicated image re-review; sandbox/release gates open
**Security impact**: high
**Starting revision**: `ab205eacc5dc09e5920afa38df4c1fda50192f96`
**Dedicated-image implementation**: `73ed430d4`
**GitHub issues**: [#655](https://github.com/rogerlew/wepppy/issues/655),
[#656](https://github.com/rogerlew/wepppy/issues/656)
**GDAL decision**: dedicated shape image authorized; common image unchanged

## Task Board

- [x] Scaffold package, active ExecPlan, failure-class assessment, and four
      independent review gates.
- [x] Cross-reference the two high findings against open, severity-tagged GitHub
      issues #655 and #656.
- [x] Record the operator decision to defer GDAL upgrades.
- [x] M0: run nine scoped baseline modules (136 passed) and direct IPC/alias/prefix probes.
- [ ] M0: complete remaining red matrix and sandbox feasibility gate.
- [ ] M0: evaluate the proposed sandbox mechanism and approve any dependency.
- [ ] M0: author/approve the compression-ratio threshold ADR before code changes.
- [x] Independent slice contract checkpoint committed before code: `6712ba631`.
- [ ] Full M0 sandbox/compression contract decisions remain open.
- [ ] M1: add focused failing IPC, driver, archive, semantic, and sandbox tests.
- [x] M2: replace pickle with bounded schema-validated data-only IPC.
- [x] M3 slice: exact driver, NFC/case-fold collisions, and extra prefixes.
- [x] Build and locally qualify the minimal shape-converter-only GDAL 3.12.4/
      Fiona 1.10.1 image; common WEPPpy image unchanged.
- [ ] M3 remainder: compression policy and broader semantic validation.
- [ ] M4: implement and attest the effective second parser sandbox.
- [x] M5 candidate: dedicated image dependency/linkage/scan, resolved Compose,
      and exact-image artifact evidence captured; operator-approved one-worker
      command passes limiter, metadata, conversion, and cleanup qualification.
- [x] Dedicated-image correctness, QA, and security re-reviews pass after the
      one-worker repair; broader M6 and rollout gates remain open.
- [ ] M6: run change-scoped shape-converter and production-equivalent gates; no
      full repository or unrelated suite.
- [ ] M6: close code, QA, correctness, and security reviews.
- [x] Comment on #655/#656 with local implementation and bounded evidence;
      both remain open pending their remaining acceptance/disposition.
- [ ] Complete authorized rollout separately; do not imply deployment from local
      or forest1 validation.

## Decisions and Constraints

- Parser output is attacker-controlled after native parsing; executable
  deserialization is forbidden even if the worker normally writes the file.
- JSON is the first IPC candidate because it is data-only and already available;
  its decoder still requires explicit byte, nesting, primitive, finite-number,
  and schema validation.
- Prototype one local per-parser sandbox under the existing hardened container.
  A new service/topology requires retained failure evidence and a separate
  operator decision.
- Any compression-ratio threshold is a governed parameterization decision. No
  numeric default is authorized by this scaffold.
- The dependency freeze is superseded only for the dedicated shape-converter
  image. The common WEPPpy image remains unchanged. Every reachable Medium,
  High, or Critical candidate finding requires remediation or explicit operator
  risk acceptance before rollout.
- Production rollout is out of scope until separately authorized.
- Validation is change-scoped by operator direction. Do not run or claim the full
  repository suite; list every focused module and boundary probe that ran.

## Required Evidence

- Baseline source/runtime matrix and retained red tests for each failure class.
- Contract checkpoint SHA and compression-policy ADR link.
- Sandbox dependency evaluation and production-equivalent prototype receipt.
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
  a Low package-closeout provenance item. The second sandbox remains a release
  blocker.

- 2026-11-14: reviewed dedicated-image implementation committed as `73ed430d4`.
  No image publication or deployment occurred.

## Handoff

Independent slice proceeds under the operator-approved sequencing amendment.
Reviewed contract checkpoint: `6712ba631`. See
[slice evidence](artifacts/20261114_independent_slice.md) for implementation,
validation, independent reviews, and remaining risks. No production deployment
or dependency upgrade occurred. Continue with a separately selected sandbox
candidate under unchanged protections; do not infer approval for privileges or
topology changes. Compression-policy decision, broader semantic matrix, current
release dependency evidence, and full conformance review remain open.

Next checkpoint: continue the separately selected second-sandbox work. Before
full package closeout, persist complete scan evidence outside `/tmp`. Keep the
common image unchanged and do not deploy.
