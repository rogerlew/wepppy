# Single-file 7777 soil uploads

Status: closed 2026-09-28 (implementation and local acceptance). Owner: Codex. Operator request: “we need add single file upload support for 7777 formats”.

Add 7777 to the existing independent soil upload mode, preserving source values
and format through single and multiple overland-flow elements (OFEs). Scope:
strict validator, preserving serializer, soil help, tests and durable guidance.
Complexity budget: no dependencies, infrastructure, queue or schema changes.
Security impact: high (expanded untrusted parser admission); dedicated independent
security and correctness reviews required. Existing containment/auth/size limits stay.

Acceptance requires accepted upload publication, exact generated field comparison,
modifier propagation, and fresh wepp_260803 execution at 1, 2, 12 and 32 OFEs.
Existing absent/empty/populated/malformed source, failed/completed build and
archive/restore contracts remain unchanged. Deployment is separate.

Delivered strict 7777 admission, preserving single/MOFE serialization, guidance,
and exact supplied-file regression coverage. Full suite: 9,892 passed, 99 skipped,
12 subtests passed. Independent correctness/security reviews approved.
See [validation summary](artifacts/20260928_validation_summary.md). Not deployed.
