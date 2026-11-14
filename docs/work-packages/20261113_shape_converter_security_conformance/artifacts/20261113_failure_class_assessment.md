# Shape-converter failure-class assessment

**Status**: Partial M0 reproduction; implementation evidence pending.
See [baseline and direct probes](20261114_m0_baseline_and_sandbox_probe.md) for
FC-01, FC-02, FC-05, and FC-07; full red matrix remains pending.

**Date**: 2026-11-14 UTC

## Scope

Assess every confirmed consumer of the broken assumption that process separation,
filename admission, or outer-container hardening alone makes hostile shapefile
parsing safe. The inventory is a starting point and must be re-run before the M0
checkpoint and final review.

| ID | Boundary / consumer | Confirmed current behavior | Risk | Required closure evidence |
| --- | --- | --- | --- | --- |
| FC-01 | `convert_parser_worker.py` to `convert.py` | Worker writes pickle; parent loads it before type checks. | Executable deserialization lets a compromised parser execute in the parent. | Data-only schema; malformed/object payload rejection; zero side effects; valid parity. |
| FC-02 | Parser subprocess runtime | Process group and timeout exist, but the worker shares the outer container's identity, mounts, namespaces, and network. | Native parser compromise reaches API-visible container resources. | Effective second sandbox; canary/mount/network/signal/process-limit tests; runtime attestation. |
| FC-03 | Readiness | Environment mode strings are compared for equality. | Configuration can claim containment that is not active. | Probe or attestation derived from the actual sandbox invocation and restrictions. |
| FC-04 | Fiona/GDAL open | Driver allowlist is supplied, but opened driver identity is not explicitly asserted. | Driver confusion or a future allowlist regression can parse a disguised format. | Exact `ESRI Shapefile` assertion and renamed VRT/HDF/other-format regressions. |
| FC-05 | ZIP duplicate/path admission | Path keys use lowercase without Unicode normalization. | Unicode-equivalent aliases can create ambiguous members or sidecars. | NFC plus case-fold collision checks, path-separator normalization, and deterministic rejection tests. |
| FC-06 | ZIP expansion | Absolute compressed/uncompressed/request quotas exist; no ratio policy is enforced. | A high-expansion member can consume resources below broad absolute caps. | Approved threshold ADR, per-member/aggregate behavior, valid high-compression controls, and quota tests. |
| FC-07 | Dataset selection | Multiple complete prefixes are rejected; an extra incomplete prefix can remain beside one complete dataset. | Ambiguous or dependency-like sidecars can be presented to the parser. | Reject every extra complete or incomplete prefix; preserve allowed same-prefix sidecars. |
| FC-08 | Shapefile semantic checks | Header/DBF checks and feature/vertex caps exist; the comprehensive semantic matrix is incomplete. | Record mismatch, invalid geometry/ranges, field collisions, or malformed sidecars can reach native conversion or yield ambiguous output. | Direct bounded fixtures and canonical rejections; valid controls retain output semantics. |
| FC-09 | Metadata/privacy sidecars | `.shp.xml`/`.qmd` removal exists and generic XML is denied. | Future parser or logging changes could expose sidecar content. | No-content response/log assertions and cleanup evidence remain green. |
| FC-10 | Parser dependencies | Historical runtime evidence exists but is not a current release receipt. | Version/linkage or reachable-CVE drift can be missed. | Unchanged common-image baseline plus exact dedicated candidate image/version/linkage/build-origin/scan record. |
| FC-11 | Inspect endpoint | Inspect performs bounded direct header/DBF/PRJ parsing rather than the Fiona worker path. | Archive/sidecar ambiguity and parser errors can diverge from convert. | Shared admission tests and explicit endpoint parity; do not misrepresent the worker sandbox as covering inspect parsing. |
| FC-12 | Error and cleanup paths | Canonical mapping and request cleanup exist, with boundedness gaps to re-check after IPC/sandbox changes. | Worker stderr/output or failed sandbox cleanup can leak data or persist hostile artifacts. | Length/sanitization limits, timeout/cancellation, partial-output rejection, and empty scratch readback. |

## Failure-Class Decision

All rows are in scope for assessment. FC-01 through FC-08 and FC-12 require code
or test closure. FC-09 must retain existing protections. FC-10 requires current
evidence and triage only: the operator explicitly deferred a GDAL upgrade.
FC-11 requires parity evidence but does not justify routing inspect through GDAL.

If discovery identifies another parser output consumer, native open, archive
extractor, or readiness claimant, add it before implementation continues. Closure
of only the originally reported call site is insufficient.

## Independent slice disposition - 2026-11-14

FC-01, FC-04, FC-05, and FC-07 have source fixes and focused local evidence in
[the slice receipt](20261114_independent_slice.md). FC-12 diagnostic ingestion,
decoder errors, and CRS/multipart error mapping are repaired; full resource and
containment acceptance remains pending. FC-02/03/06/08/10 remain open. FC-09/11
retain scoped baseline coverage. Shared archive consumers are assessed in the
receipt; this does not assert their full workflow validation.
