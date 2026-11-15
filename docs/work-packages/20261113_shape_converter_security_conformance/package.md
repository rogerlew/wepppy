# Shape-converter security conformance closure

**Status**: Rust CLI replacement, exact final-4 image, and all five independent
review lanes pass locally. #656 closure and production rollout remain separate
operator actions. See the
[final review](artifacts/20261114_rust_cli_final4_independent_re_review.md) and
[Rust dependency evidence](artifacts/20261114_rust_parser_dependency_evaluation.md).

**Started**: 2026-11-13 Pacific / 2026-11-14 UTC

**Issue status**: #655 closed as completed on 2026-11-14; independent review
accepts closing #656 as superseded by GDAL/Fiona removal, not as second-sandbox
conformance. #656 remains open pending the separately requested issue mutation.

**Timezone**: UTC

## Overview

Close the open conformance gaps in the public shape-converter security contract.
The 2026-11-13 review confirmed two high-severity boundary failures: executable
pickle deserialization from the hostile parser worker, and ineffective containment
of the GDAL/Fiona hostile parser. It also found narrower archive,
driver-identity, semantic-validation, adversarial-test, and dependency-evidence
gaps.

This package preserves the current API, request-scoped cleanup, output formats,
outer-container hardening, and independent inspect/convert uploads. The original
dependency freeze was superseded by the operator only for a minimal
shape-converter image. The common image remains unchanged. That dedicated image's
GDAL/Fiona linkage, immutable base/Ubuntu snapshot, and Syft/Grype disposition
remain parity-oracle evidence; M4 replaces its production parser with Rust.

## Objectives

- Replace parser-worker pickle IPC with bounded, schema-validated, data-only
  serialization.
- Assert that every native open resolves exactly to the ESRI Shapefile driver.
- Close archive admission gaps for Unicode-normalized path collisions,
  compression expansion policy, and ambiguous incomplete shapefile prefixes.
- Replace GDAL/Fiona hostile binary parsing with a lightweight service-local Rust
  CLI, strict JSON IPC, hard timeout/kill, bounded resources, and runtime-derived
  readiness.
- Add direct adversarial regressions for disguised formats, malformed payloads,
  worker boundary escape, semantic mismatch, timeout, resource exhaustion, panic,
  process-group termination, and cleanup.
- Record the unchanged common-image baseline and exact dedicated-image parser
  dependency versions, linkage, build origin, and reachable-vulnerability
  disposition.

## Scope

### Included

- `wepppy/microservices/shape_converter/archive_validation.py`, `inspect.py`,
  `convert.py`, `app.py`, and adjacent data-only IPC/provenance helpers.
- `wepppy/microservices/shape_converter/rust/shape_parser_cli`, plus its Cargo
  lockfile, dependency, test, image-build, and release-provenance updates.
- Shape-converter unit and integration tests, bounded hostile fixtures, and
  production-equivalent runtime inspection.
- Shape-converter image/Compose changes strictly required to install and invoke
  the Rust CLI and attest the effective parser path at readiness.
- The canonical shape-converter security contract, operator documentation, and
  review/evidence artifacts.
- GitHub issues
  [#655](https://github.com/rogerlew/wepppy/issues/655) and
  [#656](https://github.com/rogerlew/wepppy/issues/656).

### Explicitly Out of Scope

- Upgrading, downgrading, rebuilding, repinning, or replacing GDAL, Fiona, PROJ,
  GEOS, or their system packages outside the authorized dedicated image.
- Adding a parser service, queue, datastore, daemon, network protocol, new
  deployment topology, Docker socket, or privilege increase.
- Shape-converter UI/product features, cross-request staging, or changes to
  output-format semantics.
- Production deployment. Forest1 production-equivalent validation and any later
  production rollout require their normal separate authorization.
- Broad upload-boundary changes outside the shape-converter service.

## Complexity Budget

- **Existing mechanisms reused**: request scratch layout, parser subprocess,
  process-group timeout/kill, canonical errors, outer container hardening,
  Fiona driver allowlist, archive quotas, and the current test fixture builder.
- **New mechanisms permitted**: the existing explicit data-only IPC schema; one
  lightweight service-local Rust binary crate; directly enforced per-process
  resource limits; and runtime CLI attestation for readiness.
- **Simplest plausible change selected**: replace Fiona/GDAL with a bounded CLI
  while preserving the public API, existing container topology, and JSON schema.
- **Evidence required before cutover**: dependency evaluation, oracle parity,
  hostile-input/resource-limit probes, exact-image absence of Fiona/GDAL, API
  recovery, and independent acceptance of same-container residual authority.
- **Prohibited silent expansion**: parser service, in-process PyO3 production
  parser, privilege increase, writable root, host socket, broad mount, or
  permissive GDAL/Fiona fallback.

## Threat Model and Failure Signature

The service is public and accepts attacker-controlled ZIP and Shapefile bytes.
The outer container and API process are trusted to enforce admission, quotas,
cleanup, and response contracts. M4 removes the broad memory-unsafe GDAL/Fiona
parser from this path and substitutes a narrow memory-safe Rust parser CLI. The
CLI remains untrusted for malformed-input logic, panic, CPU, memory, file/output,
and dependency failures, but this amended threat model does not assume arbitrary
code execution must be isolated from the outer container.

The primary failure signatures are:

- worker-controlled bytes reach executable deserialization in the parent;
- malformed parser input can panic, hang, exhaust CPU/memory/files/output, evade
  timeout/cleanup, or produce an invalid/partial payload;
- a renamed non-shapefile driver is accepted as a shapefile;
- archive path aliases or compression expansion bypass admission policy;
- malformed sidecars, record mismatches, invalid geometry, or invalid
  coordinates reach conversion without a canonical rejection; or
- readiness reports a sandbox from environment strings that do not describe the
  effective runtime.

## Success Criteria

- [x] No production shape-converter path imports or calls `pickle` for parser
      worker IPC; malformed or object-capable payloads are rejected before data
      is constructed in the parent.
- [x] The IPC decoder enforces a byte cap, nesting/depth cap, primitive allowlist,
      finite-number rule, exact top-level schema, feature/geometry cardinality,
      and bounded sanitized errors.
- [x] Transitional Fiona opens only with the ESRI Shapefile allowlist and asserts
      the exact driver; this is oracle behavior, not the final parser.
- [x] Unicode NFC plus case-folded archive aliases collide deterministically;
      extra complete or incomplete shapefile prefixes are rejected.
- [x] Compression expansion uses the existing absolute compressed,
      uncompressed, member, scratch, and parser-input ceilings. No ratio
      threshold is adopted, so no threshold ADR is required.
- [x] Production hostile parsing uses only the service-local Rust CLI; the image and
      source contain no Fiona/GDAL or in-process PyO3 parser path.
- [x] The Rust CLI applies proven memory, CPU, open-file, file/output, payload,
      feature, and vertex limits before hostile parsing.
- [x] Readiness derives its claim from an actual bounded CLI parse, binary
      identity, JSON validation, and cleanup, not sandbox-mode label equality.
- [x] Timeout and cancellation kill the entire CLI process group and leave no
      request scratch residue; panic/abort/limit exhaustion has canonical recovery.
- [x] Valid point, line, polygon, multipart, null-geometry, GeoJSON, and
      GeoParquet controls retain semantic parity.
- [x] Exact dedicated-image GDAL/Fiona/PROJ/GEOS versions, native linkage, image
      identity, and request-path vulnerability dispositions are retained locally;
      independent review and rollout evidence remain open.
- [ ] Change-scoped shape-converter tests, production-equivalent runtime checks,
      documentation/static checks, and independent reviews pass.

## Parameterization ADR Gate

- **Parameterization change present**: no. The package retains the established
  absolute compressed, uncompressed, member, scratch, and parser-input ceilings.
- **ADR required**: no. A compression-ratio threshold was considered and rejected;
  no numeric default, formula, or fallback heuristic changed.
- **Decision rationale**: a ratio alone can reject small valid compressible files
  while the absolute ceilings already bound the relevant disk, memory, and parser
  work. Any future ratio threshold remains a new governed decision requiring its
  own ADR and representative-fixture evidence.

## Dependency and GDAL Decision

- The package may evaluate the Rust `shapefile` crate and the minimum resource-
  limit support needed by `shape_parser_cli` under the dependency-evaluation
  standard. Adoption requires precedent/capability/tax/maintenance/build, unsafe-
  code, malformed-input, license, encoding, and transitive-dependency evidence.
- The package must capture the running container's `ogr2ogr --version`, Fiona
  linkage, native-library linkage, image identity, package provenance, and
  vulnerability scan/triage.
- **Common-image GDAL upgrades remain deferred by operator direction.** The
  dedicated GDAL 3.12.4/Fiona 1.10.1 image is now a transitional parity oracle.
  The final shape-converter image must remove Fiona/GDAL parser dependencies.
- A confirmed reachable Critical dependency issue blocks conformance closure and
  is reported with evidence. It does not authorize an automatic upgrade; open a
  separate decision/package for remediation.

## Generated Artifact Validation Gate

This standard applies because the worker produces an IPC artifact and the service
produces GeoJSON/GeoParquet outputs consumed by clients.

- Record exact request intent and selected dataset.
- Hash and schema-parse the data-only IPC artifact in a disposable request root.
- Parse generated GeoJSON/GeoParquet and compare geometry, CRS, attributes, nulls,
  counts, and bounds with accepted controls.
- Exercise malformed/partial worker output and prove no successful or stale
  result is published.
- Use direct unmocked Rust CLI boundaries for valid, rejected, and resource-limit
  fixtures. Use Fiona/GDAL only as the retained pre-cutover artifact oracle.
- Retain the exact candidate revision and container identity for environment
  validation. Local tests alone support only "locally validated."

## Validation Scope Decision

The operator explicitly limited validation to the changed shape-converter
surfaces. Required automated checks are the directly affected archive, inspect,
convert, IPC, cleanup, health/readiness, runtime-hardening, and integration test
modules plus container probes and semantic artifact readback. Do not run the full
repository suite or unrelated frontend/service suites. Do not require the entire
shape-converter directory as a release gate when unchanged modules are outside
the failure class.

If implementation expands beyond the named surfaces, stop and update the package
with the new boundary and its narrowest direct tests; scope expansion is not
permission to default to a repository-wide run. Final evidence must list exactly
which tests ran and must not imply broader coverage.

## Security and Review Gates

**Security impact**: high. A dedicated independent security review is mandatory.

Closure requires:

- code review of serializer/schema, CLI/resource-limit invocation, cleanup, and
  configuration;
- QA review of red/green evidence, valid-data parity, errors, cancellation, and
  deterministic fixtures;
- correctness review of GeoJSON/GeoParquet semantic readback and API compatibility;
- security review of every parser trust boundary, resource-limit probe, oracle
  policy, archive alias/quota control, dependency disposition, and rollback; and
- zero unresolved Critical/High findings. Medium findings require explicit owner,
  rationale, target date, and operator acceptance.

Review scaffolds:

- [Code review](artifacts/20261113_code_review.md)
- [QA review](artifacts/20261113_qa_review.md)
- [Correctness review](artifacts/20261113_correctness_review.md)
- [Security review](artifacts/20261113_security_review.md)

Rust CLI implementation reviews (self-review; independent M6 signoff pending):

- [Code review](artifacts/20261114_rust_cli_code_review.md)
- [Correctness review](artifacts/20261114_rust_cli_correctness_review.md)
- [QA review](artifacts/20261114_rust_cli_qa_review.md)
- [Security review](artifacts/20261114_rust_cli_security_review.md)
- [Qualification receipt](artifacts/20261114_rust_cli_qualification.md)

Independent M6 reviews of `fe5ac7c1c` (FAIL/HOLD; remediation required):

- [Code review](artifacts/20261114_rust_cli_independent_code_review.md)
- [Correctness review](artifacts/20261114_rust_cli_independent_correctness_review.md)
- [QA review](artifacts/20261114_rust_cli_independent_qa_review.md)
- [Security review](artifacts/20261114_rust_cli_independent_security_review.md)
- [Operations review](artifacts/20261114_rust_cli_independent_operations_review.md)

## Hardening and Recurrence

- **Health signals**: data-only schema accepted; actual Rust CLI parse and binary
  identity attested; resource limits active; valid semantic parity; cleanup complete.
- **Danger signals**: any object-capable decoder, Fiona/GDAL or in-process PyO3
  fallback, caller-supplied readiness claim, unbounded error/output, limit bypass,
  or unexplained semantic drift.
- **Observation model**: stateless request boundary plus release-time dependency
  evidence. The first recurrence after closure opens a new incident package and
  reevaluates all consumers in the failure-class matrix.
- **Temporary calluses**: none permitted. A disabled resource boundary or
  permissive Python/GDAL fallback cannot be retained as a release mode.

## Dependencies and Related Work

- Canonical contract:
  [shape-converter security contract](../../../wepppy/microservices/shape_converter/docs/specification.md)
- High finding: [#655 executable parser IPC](https://github.com/rogerlew/wepppy/issues/655)
- High finding: [#656 effective second sandbox](https://github.com/rogerlew/wepppy/issues/656)
- Historical evidence:
  `wepppy/microservices/shape_converter/docs/work-packages/wp-09b_parser_containment_and_gdal_cve_remediation.md`
- Historical spec closeout:
  `wepppy/microservices/shape_converter/docs/work-packages/wp-10_spec_gap_closeout_and_production_alignment.md`
- [Failure-class assessment](artifacts/20261113_failure_class_assessment.md)
- [Active ExecPlan](prompts/active/implementation_execplan.md)

## Deliverables

- Reviewed implementation closing every in-scope conformance row.
- Direct red/green security and semantic regressions.
- Approved compression-policy ADR, if a numeric ratio is adopted.
- Rust parser dependency evaluation, unsafe/transitive audit, oracle parity, and
  runtime/resource-limit attestation evidence.
- Exact common-image baseline, retained oracle provenance, and final production
  image evidence proving Fiona/GDAL parser dependencies are absent.
- Code, QA, correctness, security, scoped local-validation, and
  production-equivalent-validation artifacts.
- Updated contract, package tracker, root tracker, and GitHub issue reminders or
  closure comments tied to the exact validated revision.

## Follow-up Work

- Common-image GDAL/Fiona/PROJ/GEOS upgrades remain separate. The operator-
  approved dedicated shape-converter image is part of this package.
- Production deployment and post-deployment smoke/monitoring remain separately
  authorized operations.
- A separate parser service or stronger containment boundary remains a future
  escalation only if retained evidence shows the bounded Rust CLI misses an
  acceptance condition. It is not authorized by this package amendment.
