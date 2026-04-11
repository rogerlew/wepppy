# Security Review - RQ Operator Experience Hardening

**Package**: `20260411_rq_operator_experience_hardening`  
**Status**: Complete (independent security review closed)  
**Date**: 2026-04-11 UTC  
**Reviewer**: Codex (implementation owner)

## Scope
- Machine-safe bootstrap endpoint:
  - `POST /weppcloud/api/auth/rq-engine-operator-token`
- Controller-state revision coherence fields:
  - `run_state_domain`, `run_state_vector`
- Snapshot freshness semantics:
  - `updated_at`, `data_state`, `data_updated_at`
- Operator smoke evidence redaction and UTC traceability rules.

## Threat Model and Security Objectives
1. Prevent unauthorized token minting.
2. Prevent scope escalation during bootstrap.
3. Prevent replay/brute-force abuse of mint surface.
4. Prevent sensitive token leakage in logs/evidence artifacts.
5. Preserve run-scope authorization boundaries for service/operator tokens.

## Security Controls Implemented
- Strong caller boundary for machine-safe bootstrap:
  - bearer token required;
  - token decoded/validated for audience `rq-engine`.
- Token-class restrictions:
  - bootstrap accepts only `user`/`service` caller tokens.
- Scope minimization enforced server-side:
  - allowlist = `rq:read`, `rq:status`, `rq:enqueue`, `rq:export`;
  - unknown requested scopes -> `400`;
  - unauthorized requested scopes -> `403`;
  - no silent scope expansion.
- Replay/revocation checks:
  - source bearer token must include `jti`;
  - denylist (`auth:jwt:revoked:{jti}`) checked before mint.
- Short-lived bootstrap tokens:
  - default TTL 900s (env-tunable, lower-bounded).
- Abuse resistance:
  - in-memory rate limiter on machine-safe bootstrap endpoint.
- Revocation backend availability contract:
  - Redis revocation lookup uses explicit socket/connect timeouts;
  - revocation backend outages return explicit `503` (not ambiguous `500`).
- Auditability:
  - mint outcomes logged with requester metadata and granted/requested scopes.
- Cache-safety:
  - bootstrap responses use `Cache-Control: no-store`.
- CSRF boundary correctness:
  - endpoint is bearer-auth and explicitly CSRF-exempt by route-level registration.
- Run-scope preservation:
  - bootstrap passthrough preserves `runid`/`config`/`runs` claims where present.

## Validation Evidence
- Flask route tests:
  - `tests/weppcloud/routes/test_rq_engine_token_api.py` (pass)
  - `tests/weppcloud/routes/test_csrf_rollout.py` (pass)
- RQ-engine contract suites and guards (Phase A preflight):
  - consolidated 251-test microservice suite (pass)
  - endpoint inventory + route checklist checks (pass)
  - guard tests (pass)
- Operator acceptance evidence:
  - `docs/work-packages/20260411_rq_operator_experience_hardening/artifacts/2026-04-11_operator_smoke_evidence.md`
  - includes redacted bootstrap/session payload excerpts and UTC method/path/status trace.

## Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| SR-01 | Low | Rate limiter is in-process memory only; limits reset on process restart and are not shared across replicas. | Accepted for current deployment profile; follow-up can externalize rate-limit state if multi-replica/operator abuse pressure increases. |
| SR-02 | Low | JWT configuration errors are returned with explicit config text in some auth error responses. | Accepted for now (local/dev ergonomics); follow-up can switch to generic client-facing text with detailed server-side logs only. |

## Residual Risk Assessment
- No unresolved **medium** or **high** security findings identified in implementation-owner review.
- Accepted **low** residual risks (`SR-01`, `SR-02`) documented above.

## Independent Security Review Gate
- `security_reviewer` pass: **Complete**
  - Re-review confirmed **no medium/high findings remain**.
  - Findings: low-only (`SR-01`, `SR-02`) accepted with documented follow-up posture.
