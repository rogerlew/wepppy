# Security Review - native CSV integration

## Metadata

Package: `20261118_parquet_csv_wepppy_integration`. Reviewer:
`csv_contract_security`, independent read-only review, 2026-11-18.
Scope: native input/IPC/filter boundary, supervisor ownership, HTTP serving,
image/provenance and canonical preflight at `c433c6ee3`.
Related [correctness review](20261118_final_correctness_review.md).

## Security Triage Decision

Impact: high; dedicated review required. Public download input is treated as
untrusted even when produced by WEPPpy. Existing route authorization and approved
shared-root containment remain authoritative. Staging is private; native parser
and provenance are required. This is bounded data handling, not a claim of a full
arbitrary-code sandbox. Empty/populated/legacy states follow the correctness matrix.

## Findings

| Finding | Surface / required action | Status |
| --- | --- | --- |
| Timestamp panic/range | Validate every decoded field, including omitted indices | Resolved |
| Disconnect during conversion | Cancel/drain owned child and staged input | Resolved |
| Late thread error replaced cancellation | Drain thread, preserve cancellation and diagnostics | Resolved |
| Provenance work before admission | Bound work under shared two-slot admission | Resolved |
| Invalid Unicode in filter keys/values | Reject before shared errors serialize invalid scalars | Resolved |
| Cleanup errors hidden during disconnect | Correlated cleanup failure and retained capacity | Resolved |
| Rejected scratch directory deleted | Track ownership; preserve rejected canary | Resolved |
| Preflight fixture umask/runtime UID | Explicit fixture permissions and no build-owned runtime scratch | Resolved |
| Success diagnostics suppressed | Fixed INFO level; exact-image hash retention assertion | Resolved |

## Surface Checks

- Valid-state non-interference: empty, populated and supported legacy exports
  covered; invalid UTF-8 reduction explicitly operator-approved.
- Auth/session/secrets: unchanged checks precede conversion; 152 adjacent checks
  and actual private-project denial pass. No new credentials or secret mounts.
- Input/output: strict bounded JSON v2, independent AST validation, structural
  preflight and fixed native resource limits; no SQL or shell interpolation.
- Filesystem: private staged copies, no source mutation, inherited persistent
  flock admission and ownership-based recovery; no age/PID scavenging.
- Subprocess/concurrency: closed stdin, controlled environment, group reap,
  parent-death signal and independent wall alarm; two shared artifact-lifetime slots.
- Queue/NoDb/Redis: N/A, wiring and persistence contracts unchanged.
- Agent/MCP and outbound network surfaces: no new production surface; no new
  outbound conversion dependency or automatic download/build.
- CI/supply chain: pinned Rust builder and Cargo graph; source/binary provenance,
  test-image build and drift rejection. Audit has zero known vulnerabilities;
  existing Chrono maintenance warning remains recorded, not waived as healthy.
- Monitoring/recovery: typed errors, request-correlated hashes/sizes/resources;
  no cell/filter-value logs. Whole-release rollback is documented.

## Validation Evidence

213 focused and 152 adjacent checks; 13 Rust boundary checks; 46-file oracle parity.
Retained independent SIGALRM/serving-deadline probes, real parent-death/inherited
lease checks, hostile ZSTD and strict IPC tests. Final eight-worker image checks
exercise real large HTTP bytes, slow-reader busy admission, disconnect cleanup,
raw availability, private denial, tampered artifacts, two UIDs and operator umask077.
See validation.md for exact identities and broad-suite disposition. No frontend or
RQ graph gate applies. Changed docs, Rust formatting and exception enforcement pass.

## Residual Risk and Verdict

Gate: PASS; no unresolved high/medium/low findings or accepted-risk findings.
Finite tests do not prove all possible hostile inputs or target-host performance.
Native decoding remains subject to normal dependency maintenance; process/page/
decode/time limits remain mandatory. Kernel-uninterruptible I/O can retain a slot
until actual child exit, intentionally preventing unsafe reclamation.
Production configuration/proxy acceptance and deployment remain separately gated.

## Sign-off

Security reviewer: `csv_contract_security`, 2026-11-18; source and local image
acceptance only. Integrator: Codex. Owner's explicit retention and invalid-UTF8
approvals are recorded in the canonical contract; deployment is not approved.

## Artifact Observability Gate

Original project Parquet remains in normal authorized browse/download. Temporary
conversion copies/IPC/CSV are excluded by the explicit operator-approved exception
in the canonical integration contract. Actual failure/serving cleanup and success
hash logging are proven. Archive/restore of new project members is N/A because no
project artifact is added; neither hidden project outputs nor a CSV cache exists.
