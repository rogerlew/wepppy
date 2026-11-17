# Security Review - Vector upload normalization

**Status**: Independent M0 review complete; checkpoint held pending findings.

## Metadata

- **Package**: `docs/work-packages/20261116_vector_upload_normalization/`
- **Reviewer**: independent `dependency_security_resume` reviewer
- **Scope**: GeoParquet/Shapefile admission, Rust CLIs, shape-converter, four receiving workflows
- **Commit/image context**: Pending exact revision and image digest
- **Related correctness artifact**: `artifacts/20261116_correctness_review.md`

## Security Triage

- **Impact**: high
- **Dedicated review required**: yes
- **Rationale**: public/user-controlled compressed binary columnar data, metadata,
  geometry encodings, native/system resource boundaries, and cross-service file
  handling expand a high-cost hostile parsing surface.
- **Trust boundary**: the outer shape-converter service enforces admission,
  resource ownership, process lifecycle, cleanup, and response contracts. Each
  Rust CLI remains untrusted for malformed-input logic, panic, CPU, memory,
  descriptors, output expansion, and dependency failures. The sibling CLI does
  not claim arbitrary-code containment from the outer container.

## Threat Checklist

- [ ] Exact magic/extension and one-local-file admission; no traversal, symlinks,
      datasets, URLs, external `file_path`, encryption, or network fetches.
- [ ] Metadata/footer/schema/depth/row-group/row/decoded-byte budgets are enforced
      before attacker-controlled allocation or decompression where possible.
- [ ] Compression codecs are allowlisted and expansion is bounded by measured bytes.
- [ ] Arrow extension metadata cannot trigger class loading, object
      deserialization, code execution, or a permissive fallback.
- [ ] WKB length, geometry nesting, coordinates, vertices, types, bounds, and
      finite-number rules are directly enforced and recomputed.
- [ ] CRS handling is bounded, offline, and rejects explicit unknown CRS.
- [ ] CLI IPC is data-only, byte/depth/schema bounded, finite-number checked, and
      rejects extra fields or partial output.
- [ ] Wall time, CPU, memory, descriptors, scratch, output, concurrency,
      cancellation, process-group drain, and repeated-cancellation recovery pass.
- [ ] Raw uploads are private and ephemeral; logs/errors exclude raw metadata,
      paths, file content, and secrets; scratch cleanup passes after every outcome.
- [ ] Receiving endpoints preserve auth, CSRF, run scope, size, semantic, and
      persistence validation even if the converter is bypassed.
- [ ] Locked dependencies, binary provenance, exact-image identity, SBOM,
      vulnerability dispositions, readiness canary, rollback, and fail-closed
      behavior are verified.
- [ ] Concurrent valid/hostile requests cannot cross-contaminate files, metadata,
      results, limits, or cleanup ownership.

## Initial Findings

| ID | Severity | Surface | Finding | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | High | GeoParquet contract | Numeric resource ceilings and pre-allocation enforcement points are not ratified. | Complete ADR and hostile exact-image probes before implementation acceptance. | Open |
| SEC-02 | High | Dependency boundary | No Rust Parquet/Arrow/WKB/CRS dependency graph had passed evaluation. | Complete dependency artifact and independent review before adoption. | Resolved for graph selection: exact graph conditionally accepted behind owned preflight; implementation evidence remains VUN-SEC-M0-01 |
| SEC-03 | Medium | Workflow boundary | Converter and receiving-endpoint limits/error semantics are not yet unified. | Ratify the end-to-end normalization contract and retain bypass tests. | Open |

## Initial verdict (superseded by resumed M0 verdict)

- **Gate status**: fail
- **Unresolved findings**: High 2; Medium 1; Low 0
- **Release recommendation**: hold

Scaffolding records required controls but supplies no implementation or runtime
evidence. Accepted-risk status requires independent reviewer recommendation and
explicit package-owner acknowledgment.

## Daybreak resumed M0 verdict

The interrupted lane resumed on 2026-11-16. The exact dependency graph is
conditionally accepted behind an owned preflight; direct upstream decoding of
unpreflighted bytes is rejected. Full findings and allocation evidence are in
`20261116_m0_dependency_security_review.md`.

The M0 checkpoint remains on hold with two High and three Medium findings. The
High findings require promotion of the same-descriptor preflight invariant and
acceptance of ADR-0145's aggregate envelope. The Medium findings require the
operator's raw-input retention disposition, canonical endpoint/converter
amendments plus second contract review, and later executable enforcement-stage
coverage. No runtime, image or release approval is given.


## Historical review interruption

Independent `dependency_review` was started for M0. It retained an evaluation
lock/tree/advisory report and preliminary allocation findings, then the tool
terminated its turn because this session does not meet Daybreak Blue
account-security requirements. The tool directs the operator to
[security setup](https://chatgpt.com/cyber), Your eligibility, and sign-in with an
approved hardware security key. This was an external review blocker, not a
security pass. Daybreak was later enabled and the lane completed; the resumed
verdict above is authoritative. Runtime implementation remains gated by its
listed checkpoint findings.
