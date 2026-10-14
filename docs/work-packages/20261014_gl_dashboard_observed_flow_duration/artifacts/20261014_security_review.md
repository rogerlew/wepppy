# Security review — observed flow-duration overlay

## Metadata

Reviewer: independent agent `/root/contract_security`, 2026-10-14 UTC.
Context: implementation after checkpoint `4e02ee2e0`, master working tree.
Scope: bootstrap file reader, controls, loader, renderer and direct boundary tests.
Related: [correctness review](20261014_correctness_review.md), [validation](validation.md).

## Security triage and threat model

High; dedicated review required because project file/path handling changed.
Existing run authorization remains the entry boundary. Uploaded CSV and area
parquet may be malformed or linked outside the project. Absent/empty/populated,
legacy numeric-string area and hostile state must preserve simulated graph access.
Canonical Omni lineage may use parent observations; arbitrary ancestors may not.

## Findings and disposition

| ID | Severity | Surface | Finding | Action and evidence | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Area parsing | LIST/STRUCT raised TypeError; BOOLEAN accepted as area | Strict DOUBLE conversion before MAX; BOOLEAN rejection; real parquet regressions and independent reproduction | Resolved |

Reviewer independently reran real-file checks after remediation: LIST, STRUCT and
BOOLEAN produce observed-unavailable without records; valid simulated metadata
survives. Numeric and legacy numeric-string area remain supported.

## Surface checks

Valid-state noninterference: pass, direct temporary-file tests cover valid and
hostile state without mocking the reader. Absence is normal; invalid present
artifacts have explicit isolated explanations.

Auth/session/CSRF: unchanged existing authorized page; no new routes or mutations.
Secrets: no new secrets or credential dependencies. Input/output: contained fixed
paths, parameterized SQL, existing Jinja tojson, textContent for errors/labels.
Filesystem: reject escaping CSV/parquet symlinks before opening; actual read limit
16 MiB +1 and 100,000-row limit reject rather than truncate. No project writes.
Queue/subprocess, agentic/MCP, network, CI and supply-chain surfaces: unchanged;
no new services, external requests, packages or privileges. Concurrency: read-only
page-session snapshot contract; no NoDb/Redis mutation. Logs contain source path
and failure reason; errors are not swallowed. Rollback removes additive reader/UI.

## Validation and observability

See validation.md. Source artifacts remain in observed/ and wepp/output/interchange/
and preserve existing inspection/archive behavior; no writer, new project artifact
or archive exclusion is introduced. Real-project readback hashes prove no mutation.
Browser harness consumes generated bootstrap values through actual graph modules.

## Verdict and sign-off

PASS. Unresolved High 0, Medium 0, Low 0. Independent security reviewer approved
2026-10-14 after SEC-01 reproduction passed. Package owner: Codex, same date.
Correctness/browser approval is separate. Existing concurrent-replacement snapshot
limitation remains: reload after uploads/output replacement; no new race guarantee.
