# RQ-WH-01 independent checkpoint reviews and disposition

Date: 2026-10-28. Base: `dd4e5381ba4e3fd66e82c0e14e8d82faa174ff47`.
Scope: proposed canonical webhook contract, ADR-0109, affected contract amendments,
dated decision matrix and source/probe evidence. Reviews were independently
read-only; primary author recorded this artifact from reviewer returns.

Correctness reviewer: `/root/contract_correctness` (reviewer role).
Security reviewer: `/root/contract_security` (security_reviewer role).
Both reviewed initial proposal and independently confirmed the post-fix text.
These are contract proposal reviews, not final implementation/security acceptance.

## Correctness review

User goal: receive whole-operation execution notifications without changing domain
results or computation. Canonical intended delta and affected contracts are named
in [the checkpoint](20261028_contract_decision.md). Absent/empty/populated/legacy/
malformed stored states and request combinations are separate matrices. Required
error/recovery, generated-artifact evidence and real-boundary tests are specified;
implementation evidence is pending, not replaced by substrate probes.

| ID | Severity at initial review | Finding | Author disposition / independent confirmation |
| --- | --- | --- | --- |
| COR-01 | High | Literal original culvert response replay would retain browse_token and could replay expired credentials, contrary to no bearer persistence | Fixed canonical Admission and recovery matrix: credential-free receipt, fresh authorized existing mint, explicit 202 accepted response with warning after mint failure; ADR aligned, A04 added. Reviewer confirmed resolved. |
| COR-02 | Medium | Unavailable admission tombstone had no exact status/body or safe new-key policy | Fixed canonical table with 410 webhook_admission_unavailable, planned job_id and proven-not-published versus unknown distinction; A05 added. Reviewer confirmed resolved. |

Post-fix verdict: **PASS for proposal readiness**, high 0, medium 0 unresolved.
Reviewer confirmed settlement versus failure, callback/producer closure obligations,
conditional event commit, execution/domain distinction and pending validation are
represented correctly. Quote from final return: “Proposal readiness passes; no
remaining medium/high contradiction found in this re-review.”

## Security review

Security impact: **HIGH**, dedicated review required. Threat model includes
untrusted callback URLs/receivers, lineage spoofing, cross-principal receipt access,
recording/playback leakage, shared Redis pressure and restored callback replay.
Valid no-callback workflows and existing auth/resource access must remain intact.
TLS/public-address pinning, no proxy/redirect, unsigned-hint semantics, quotas,
restricted intent and sanitized audits are proposed controls requiring real tests.

| ID | Severity at initial review | Finding | Author disposition / independent confirmation |
| --- | --- | --- | --- |
| SEC-01 | Medium | Credential-bearing original-response retention/replay | Same remedy as COR-01; no invented browse-renewal API. Reviewer confirmed canonical text/ADR/A04. |
| SEC-02 | Medium | Restore suppression appeared only in transient checkpoint, allowing copied/stale pending records to resend production URLs | Promoted environment binding and external disabled startup to canonical operator controls, explicit rearm and test-copy exclusion; R03 added. Reviewer confirmed resolved. |
| SEC-03 | Medium | “Verified principal” did not define collision-resistant stable receipt/quota identity across token classes/rotation | Added typed issuer-scoped account/session/integration identity, trusted delegation adapters, no jti/anonymous fallback, callback-only unsupported-identity error; S04 added. Reviewer confirmed resolved. |

Post-fix verdict: **PASS for proposal readiness**, high 0, medium 0 unresolved.
Read-only sign-off: `/root/contract_security`, 2026-10-28. Final return explicitly
limits approval to drafting remedies, not implementation or deployment acceptance.
No residual risk was accepted on behalf of the operator.

## Validation and remaining gates

Disposable real Redis/RQ probe assertions passed with retained source/output.
Scoped doc lint: package and six external contract/ADR files, zero errors/warnings.
Spelling preview: package Markdown plus new contract/ADR, no differences.
`git diff --check` passed. No production source edit, broad pytest, live API call,
model run, runtime restart, commit or deployment was performed.

Real sender/receiver security tests, writer/producer closure coverage, concurrency,
quota/performance and API-to-model-artifact parity remain unexecuted. Final correctness
and security reviews follow implementation. Exact operator matrix approval and
package commit authority are still missing; this review does not grant either.
