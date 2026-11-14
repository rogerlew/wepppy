# Shape-converter security conformance closure

**Status**: Independent IPC/driver/archive slice and dedicated image are locally
validated; sandbox and release gates remain open. See
[slice evidence](artifacts/20261114_independent_slice.md) and
[image evidence](artifacts/20261114_dedicated_image_qualification.md).

**Started**: 2026-11-13 Pacific / 2026-11-14 UTC

**Timezone**: UTC

## Overview

Close the open conformance gaps in the public shape-converter security contract.
The 2026-11-13 review confirmed two high-severity boundary failures: executable
pickle deserialization from the hostile parser worker, and the absence of the
required effective second parser sandbox. It also found narrower archive,
driver-identity, semantic-validation, adversarial-test, and dependency-evidence
gaps.

This package preserves the current API, request-scoped cleanup, output formats,
outer-container hardening, and independent inspect/convert uploads. The original
dependency freeze was superseded by the operator only for a minimal
shape-converter image. The common image remains unchanged. The dedicated image's
GDAL/Fiona linkage, immutable base/Ubuntu snapshot, and Syft/Grype
reachable-vulnerability disposition are required evidence.

## Objectives

- Replace parser-worker pickle IPC with bounded, schema-validated, data-only
  serialization.
- Assert that every native open resolves exactly to the ESRI Shapefile driver.
- Close archive admission gaps for Unicode-normalized path collisions,
  compression expansion policy, and ambiguous incomplete shapefile prefixes.
- Run native parsing inside an effective second sandbox with request-only mounts,
  no network, bounded processes/resources, and runtime-derived readiness.
- Add direct adversarial regressions for disguised formats, malformed payloads,
  worker boundary escape, semantic mismatch, timeout, cleanup, and sandbox
  containment.
- Record the unchanged common-image baseline and exact dedicated-image parser
  dependency versions, linkage, build origin, and reachable-vulnerability
  disposition.

## Scope

### Included

- `wepppy/microservices/shape_converter/archive_validation.py`, `inspect.py`,
  `convert.py`, `convert_parser_worker.py`, `app.py`, and adjacent data-only IPC
  helpers if needed.
- Shape-converter unit and integration tests, bounded hostile fixtures, and
  production-equivalent runtime inspection.
- Shape-converter container/Compose changes strictly required to install and
  invoke one effective per-parser sandbox and attest it at readiness.
- The canonical shape-converter security contract, operator documentation, and
  review/evidence artifacts.
- GitHub issues
  [#655](https://github.com/rogerlew/wepppy/issues/655) and
  [#656](https://github.com/rogerlew/wepppy/issues/656).

### Explicitly Out of Scope

- Upgrading, downgrading, rebuilding, repinning, or replacing GDAL, Fiona, PROJ,
  GEOS, or their system packages outside the authorized dedicated image.
- Adding a parser service, queue, datastore, daemon, network protocol, or new
  deployment topology without a separate operator decision.
- Shape-converter UI/product features, cross-request staging, or changes to
  output-format semantics.
- Production deployment. Forest1 production-equivalent validation and any later
  production rollout require their normal separate authorization.
- Broad upload-boundary changes outside the shape-converter service.

## Complexity Budget

- **Existing mechanisms reused**: request scratch layout, parser subprocess,
  process-group timeout/kill, canonical errors, outer container hardening,
  Fiona driver allowlist, archive quotas, and the current test fixture builder.
- **New mechanisms permitted**: one explicit data-only IPC schema; one
  per-parser sandbox mechanism proven under the existing non-root container; one
  runtime attestation path for readiness.
- **Simplest plausible change tested first**: JSON IPC plus a local sandbox
  executable that exposes only the request input/output paths.
- **Evidence required before escalation**: a retained production-equivalent
  prototype proving that the local mechanism cannot satisfy mount, network,
  syscall, process, or identity requirements under the existing container.
- **Prohibited silent expansion**: separate service, privilege increase,
  writable root, host socket, broad mount, or permissive fallback.

## Threat Model and Failure Signature

The service is public and accepts attacker-controlled ZIP and shapefile bytes.
The outer container and API process are trusted to enforce admission, quotas,
cleanup, and response contracts. The native Fiona/GDAL parser worker is
untrusted after it opens uploaded data. Its output, filesystem access, network
access, process tree, signals, and resource consumption must therefore be
contained.

The primary failure signatures are:

- worker-controlled bytes reach executable deserialization in the parent;
- the parser can read or write beyond its request boundary, open a network
  socket, signal the API process, or exceed declared process/resource limits;
- a renamed non-shapefile driver is accepted as a shapefile;
- archive path aliases or compression expansion bypass admission policy;
- malformed sidecars, record mismatches, invalid geometry, or invalid
  coordinates reach conversion without a canonical rejection; or
- readiness reports a sandbox from environment strings that do not describe the
  effective runtime.

## Success Criteria

- [ ] No production shape-converter path imports or calls `pickle` for parser
      worker IPC; malformed or object-capable payloads are rejected before data
      is constructed in the parent.
- [ ] The IPC decoder enforces a byte cap, nesting/depth cap, primitive allowlist,
      finite-number rule, exact top-level schema, feature/geometry cardinality,
      and bounded sanitized errors.
- [ ] Fiona opens only with the ESRI Shapefile allowlist and the opened dataset's
      driver is asserted to be exactly `ESRI Shapefile`.
- [ ] Unicode NFC plus case-folded archive aliases collide deterministically;
      extra complete or incomplete shapefile prefixes are rejected.
- [ ] Compression expansion policy is implemented only after its threshold ADR
      is approved, with stored/empty entries and valid high-compression controls.
- [ ] The native parser runs inside a second sandbox that cannot read a
      parent-only canary, write outside request output, open a socket, signal the
      API process, or spawn beyond its limit.
- [ ] Readiness derives its claim from an actual sandbox probe/attestation, not
      only `SHAPE_CONVERTER_*_SANDBOX_MODE` equality.
- [ ] Timeout and cancellation kill the entire sandbox/process group and leave
      no request scratch residue.
- [ ] Valid point, line, polygon, multipart, null-geometry, GeoJSON, and
      GeoParquet controls retain semantic parity.
- [x] Exact dedicated-image GDAL/Fiona/PROJ/GEOS versions, native linkage, image
      identity, and request-path vulnerability dispositions are retained locally;
      independent review and rollout evidence remain open.
- [ ] Change-scoped shape-converter tests, production-equivalent runtime checks,
      documentation/static checks, and independent reviews pass.

## Parameterization ADR Gate

- **Parameterization change present**: yes, if a new compression-ratio threshold
  is introduced.
- **ADR required**: yes, before the threshold merges.
- **Required provenance**: old behavior, proposed ratio and units, valid-fixture
  distribution, hostile-fixture evidence, decision venue, participants, decision
  owner, rollback trigger, and the package link.
- **No implied default**: this scaffold does not select or authorize a numeric
  ratio. Absolute compressed/uncompressed/request quotas remain enforced while
  the decision is pending.

## Dependency and GDAL Decision

- The package may evaluate one sandbox dependency under the dependency-evaluation
  standard. Adoption requires precedent/capability/tax/maintenance/build evidence
  and a production-equivalent non-root prototype.
- The package must capture the running container's `ogr2ogr --version`, Fiona
  linkage, native-library linkage, image identity, package provenance, and
  vulnerability scan/triage.
- **Common-image GDAL upgrades remain deferred by operator direction.** The
  dedicated shape-converter image is the sole authorized exception and uses the
  reviewed GDAL 3.12.4/Fiona 1.10.1 contract.
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
- Use direct unmocked Fiona/GDAL and sandbox boundaries for at least one valid and
  one rejected fixture; mocks may isolate unrelated HTTP plumbing only.
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

- code review of serializer/schema, subprocess/sandbox invocation, cleanup, and
  configuration;
- QA review of red/green evidence, valid-data parity, errors, cancellation, and
  deterministic fixtures;
- correctness review of GeoJSON/GeoParquet semantic readback and API compatibility;
- security review of every parser trust boundary, sandbox probe, driver policy,
  archive alias/quota control, dependency disposition, and rollback; and
- zero unresolved Critical/High findings. Medium findings require explicit owner,
  rationale, target date, and operator acceptance.

Review scaffolds:

- [Code review](artifacts/20261113_code_review.md)
- [QA review](artifacts/20261113_qa_review.md)
- [Correctness review](artifacts/20261113_correctness_review.md)
- [Security review](artifacts/20261113_security_review.md)

## Hardening and Recurrence

- **Health signals**: data-only schema accepted; effective sandbox attested;
  exact driver confirmed; valid semantic parity; cleanup complete.
- **Danger signals**: any object-capable decoder, sandbox fallback, caller-supplied
  readiness claim, unexpected driver, alias ambiguity, unbounded error/output, or
  unexplained semantic drift.
- **Observation model**: stateless request boundary plus release-time dependency
  evidence. The first recurrence after closure opens a new incident package and
  reevaluates all consumers in the failure-class matrix.
- **Temporary calluses**: none permitted. A disabled sandbox or permissive IPC
  fallback cannot be retained as a release mode.

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
- Sandbox dependency evaluation and runtime attestation evidence.
- Exact common-image baseline plus dedicated-image dependency, linkage, and
  vulnerability record.
- Code, QA, correctness, security, scoped local-validation, and
  production-equivalent-validation artifacts.
- Updated contract, package tracker, root tracker, and GitHub issue reminders or
  closure comments tied to the exact validated revision.

## Follow-up Work

- Common-image GDAL/Fiona/PROJ/GEOS upgrades remain separate. The operator-
  approved dedicated shape-converter image is part of this package.
- Production deployment and post-deployment smoke/monitoring remain separately
  authorized operations.
- If an in-container second sandbox is infeasible, prepare a separate architecture
  decision for a parser service; do not silently implement it here.
