# F5 safe traceback contract decision

**Status**: Proposed; owner direction recorded, canonical contract pending
**Finding**: F5 / SEC-05
**Date**: 2026-11-11 UTC
**Starting revision**: `f0df22e5f8d2ae6255c6aa0e718394ad69a41b51`

## Owner Decisions

1. Do not remove traceback observability.
2. Preserve absolute paths and useful frame/source context.
3. Use one sanitized representation; no audience-dependent traceback policy.
4. Preserve existing endpoint authorization and current response-field presence.
5. Do not add a process-wide secret registry or cache.
6. Read explicit configured secret sources only while rendering an exception,
   sanitize all traceback sinks, then release references without claiming memory
   zeroization.
7. Leave the current secret/client lifecycle unchanged.
8. Complete Redis credential transport first with scoped validation, then run F5
   focused tests plus full pytest, npm lint and full npm tests.
9. Treat Kubernetes secrets exactly like existing mounted-file secrets. Do not
   add SOPS decryption, Kubernetes Secret API access or new workload RBAC.
10. Select secret-source metadata per process. An environment variable is not
    proof that its file belongs to or is mounted in the current process.
11. Include Kubernetes-captured stdout/stderr and the Python WEPPcloudR control
    plane in the traceback sink inventory; keep live cluster rollout separate.

## Proposed Rendering Contract

- Construct tracebacks with locals disabled and bounded exception-group/depth/
  output handling.
- Preserve exception type, safe message, cause/context/notes, frame function,
  line number, source context and absolute file paths.
- Read only a reviewed source profile selected by the current process adapter.
  Source metadata names canonical settings, file/env precedence,
  required/optional state and bounded decoding; it never retains values. Prefer
  the configured `_FILE` input and honor its current environment fallback.
  Never glob secret mounts or open arbitrary `*_FILE` values.
- Decode compound sources according to their existing consumer contract. The
  authorization JWT key-ring file contributes each comma-delimited key; PEM
  private keys and Kubernetes/service bearer tokens receive explicit coverage.
- Temporarily match raw values plus bounded percent-encoded and JSON-escaped
  variants. Structurally redact URI userinfo, Authorization/cookie credentials,
  bearer/JWT strings, PEM blocks and sensitive assignments.
- Produce one string before any API, log, run-file, RQ Redis or publication sink.
- If source loading or sanitization fails, return a fixed generic diagnostic and
  `error_id`; never return or log the raw exception as fallback.
- Do not read secret sources when no exception/stack is being rendered.

## State Matrix

| State | Required result |
| --- | --- |
| No configured secrets | Ordinary traceback preserved with structural redaction |
| Optional secret absent | Continue without it |
| Configured mounted secret readable | Exact/encoded value redacted |
| Configured source unreadable/empty | Fail-closed generic diagnostic |
| Declared downstream/pass-through path | Not opened by the current process |
| Unrelated or stale `*_FILE` setting | Not a source merely because it is set |
| Compound key-ring file | Every constituent key and bounded encoding redacted |
| Kubernetes service-account token in owning control plane | Current file value redacted per render call |
| Legacy environment fallback | Temporarily included in snapshot |
| Cause/context/note/group | Bounded and sanitized recursively |
| Secret only in local/environment mapping | Not exposed because locals/env are never captured |
| Sanitizer internal failure | Generic diagnostic; raw trace discarded |

## Alternatives Rejected

- Remove all API tracebacks: breaks current observability before the app is ready.
- Owner/admin versus anonymous/public variants: complexity has limited benefit
  because account creation and run ownership are broadly available.
- Strip absolute paths: not an owner concern and reduces diagnostics.
- Process-wide exact-value registry: aggregates and can extend secret lifetime.
- Global scanning of known `*_FILE` variables: confuses downstream-only and
  stale paths with locally consumed secrets and can destroy observability.
- Regex-only filtering: cannot reliably remove an unlabeled configured value.
- Redis cleanup inside F5: separate runtime/auth boundary and test policy.

## Required Checkpoint

- [ ] Explicit secret-source and sink inventories accepted.
- [ ] Process-owned Kubernetes source profiles and compound decoders accepted.
- [ ] Container stdout/stderr and uncaught-exception coverage accepted.
- [ ] Output/depth bounds and ADR disposition accepted.
- [ ] Logging formatter and RQ pre-persistence ordering reviewed.
- [ ] Correctness and security reviewers approve a standalone ancestor commit.

This artifact records owner direction but does not claim implementation.
