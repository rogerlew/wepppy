# Security review — MRS-01

## Metadata

Package: `20261030_malformed_request_side_effects`.
Independent reviewer: `/root/flask_contract_review` (security_reviewer).
Date: 2026-10-30. Baseline: `e35d7a3e69497ddfd9709736af50107f56963584`.
Scope: shared Flask/RQ payload contract, public mutation/upload consumers and
planned rejection ordering. [Contract review](20261030_contract_reviews.md)
records checkpoint findings and disposition. Final code review is pending.

## Security triage decision

Impact **high**; dedicated security review required. Authorized requests with
malformed input can reach default destructive/external work. Input validation
changes public request handling and upload boundaries. Existing auth, roles,
run access, CSRF, request/admission locks and execution identities remain intact.
No new egress, secret handling or infrastructure is proposed.

Controls must preserve absent optional state, present-empty/default operations,
populated sources/results, legacy forms/aliases/null sentinels, active admission
and valid webhook replay. The repair must not turn normal absence into corruption
or reinterpret valid false values. Auth success does not make malformed input valid.

## Findings

| ID | Severity | Surface | Evidence / required action | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Shared/direct default fallback and truthy flags | Baseline HTTP probe plus source matrix; strict typed validation before business effects | Open implementation |
| SEC-02 | High | Early controller/source mutation and recovery | PATH CE/Geneva, Omni, landuse/soil/treatments/Ash matrix; stage validation before writes/promotion | Open implementation |
| SEC-03 | Medium | Local exception wrappers | Source audit; prove actual JSON 400 without tracebacks through registered routes | Open implementation |
| SEC-C01 | Medium | Contract null/blank ambiguity | Enumerated Flask/Bootstrap policies and compatibility rationale in canonical scalar table | Resolved in checkpoint; independent confirmation 2026-10-30 |
| SEC-C02 | Medium | Recorder structural ambiguity | Canonical contract now requires object envelope with nested events list | Resolved in checkpoint; independent confirmation 2026-10-30 |
| SEC-C03 | Low | Geneva native-only config flag policy | Explicit current specification citation prevents token widening | Resolved in checkpoint |

## Surface checks and verdict

Checkpoint design approved by independent reviewer after SEC-C01/C02/C03 fixes.
**Final implementation/release gate: hold.** SEC-01/02/03 remain open until repairs
and direct evidence exist. No risk acceptance or shipping recommendation is made.

Auth/CSRF: unchanged normative policy; actual rejection precedence tests pending.
Input/output: bounded error messages and allowlisted fields required; no body,
secret, filesystem path or traceback disclosure. Multipart: preserve existing
counted limits, source ownership and cleanup across client/parser/disconnect/cancel
failures. Persistence: real reload/cache follow-up and absent-state tests required.
Queue/external execution: no topology change; malformed input cannot reach enqueue
or worker cleanup. Callback: preserve identities/digests, replay and uncertainty;
no orphan new reservation. Valid-state noninterference and generated prepared-file
readback remain required; parser-only mocks are insufficient.

## Sign-off

Independent checkpoint verdict: “Checkpoint-only approval ... No remaining
medium/high findings in this contract review.” Final security approval is explicitly
pending real-route, persistence, multipart, WAM-01 and implementation review evidence.
Operator commit authority remains absent; no source changes or deployment authorized
by this review itself.
