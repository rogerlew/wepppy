# M0 independent contract reviews

Reviewed 2026-11-11 01:26 UTC against implementation base `b3786ae7e`.
Contract: `docs/schemas/query-engine-http-access-contract.md`.
SHA-256: `1a11b3c6af74cdb65d77bda3f69335667936b751c00ecaf2061f544688306c99`.
Reviews were read-only; neither reviewer authored amendments or ran live probes.
The primary agent prepared amendments and recorded the disposition below.

## Correctness review

Reviewer: `/root/contract_correctness`, independent `reviewer` agent.
Verdict: approve proposed contract for operator ratification and checkpoint;
no unresolved high/medium contract findings. This is not implementation or
release approval.

| Finding | Severity | Disposition |
| --- | --- | --- |
| Ordinary parent cookie does not reach Omni child URL | High | Closed: hashed query-prefix keys, exact parent/child resource and marker rules |
| Existing no-config bridge misses direct dashboard/viewer entry | High | Closed: actual admitted entry paths must issue credentials |
| Ownerless/private matrix conflicts with PCV legacy visibility | High | Closed: ordinary ownerless reads and exact current PCV membership grants retained; cross-link names query read surfaces |
| `get_wd` creates Omni links before guard | High | Closed: explicit side-effect-free resolution with unchanged defaults elsewhere |
| Body scenario follows symlinks before auto-activation | High | Closed: check before context/catalog work |
| Malformed derived cache repair could regress | Medium | Closed: preserve authorized automatic repair and readonly rules |
| Parent-backed landuse/soils omitted from sharing list | Medium | Closed: canonical parent-backed selection explicitly retained |
| Batch-base key missing from child cookie lookup | Medium | Closed: exact permitted `_base` alias lookup |
| Shared resolver now requiring config would break MCP | Medium | Closed: HTTP grammar separate from bare-ID MCP; unmocked resolver regression required |

Residual gates: real 100-run browser/ingress limits, actual profile workflow,
complete no-write/authorization matrix and genuinely non-creating canonical
metadata reads. No evidence currently justifies transport redesign.

## Security review

Reviewer: `/root/contract_security`, independent `security_reviewer` agent.
Verdict: pass design review, pending operator ratification and checkpoint;
no unresolved high/medium contract findings. SEC-F1 remains open at runtime.

| Finding | Severity | Disposition |
| --- | --- | --- |
| SEC-C1: auth may independently re-resolve a different mutable WD cache | Medium | Closed: every decision/recheck consumes the same checked parent/root |
| SEC-C2: unspecified metadata could manufacture ownerless anonymous admission | Medium | Closed: existing regular `ron.nodb`, successful non-creating canonical read and successful empty owner lookup; failure never public |
| Pre-auth Omni/WD cache writes | High | Addressed by pure resolution and link/cache denial evidence |
| Scenario symlink escape | High | Addressed by pre-context containment |
| Cross-contract authority conflict | Medium | Addressed by feature/session/CSRF/token/composite/PCV amendments |
| MCP bare-ID resolver compatibility | Medium | Addressed by separate HTTP parsing requirement |

Cookie header amplification remains a concrete acceptance risk, not a proven
failure: the 100-run real-browser/ingress test must pass before rollout. SQL
external-access disabling exists in current executor source and has a canary
test; the older README blocker text is not proof of a current vulnerability.
Preserve and run those tests; this package is not a whole-service security claim.

## Primary-agent disposition and remaining authority

All contract review findings are closed in the reviewed proposal. Implementation
and final correctness/security/QA review remain outstanding. The operator must
ratify the revised exact matrix, then the accepted contracts and these reviews
must become a standalone ancestor before implementation edits. Production
containment/deployment requires separate explicit authorization. No checkpoint,
implementation, environment validation, deployment or incident closure is claimed.
