# Tracker - Safe traceback and exceptional-path secret sanitization

## Quick Status

**Timezone**: UTC
**Started**: 2026-11-11 18:27 UTC
**Current phase**: queued behind Redis credential transport
**Last updated**: 2026-11-11 19:05 UTC
**Next milestone**: Redis prerequisite, then F5 contract checkpoint
**Finding**: F5 / SEC-05
**Security impact**: high
**Starting revision**: `f0df22e5f8d2ae6255c6aa0e718394ad69a41b51`
**Security artifact**: `artifacts/20261111_security_review.md`

The package is scaffolded and blocked by the Redis credential transport package.
No code, logging, API, secret or deployment behavior changed.

## Task Board

- [x] Record the revised F5 direction: filter, do not remove, tracebacks.
- [x] Record one representation, absolute-path preservation, exceptional-path
      secret snapshots, no registry and unchanged secret lifecycle.
- [x] Scaffold package, ExecPlan, contract, failure matrix and review gates.
- [x] Record mandatory full pytest, npm lint and full npm tests.
- [x] Review openwepp Kubernetes/SOPS handling and add process-owned source,
      compound decoder, container-log and production-equivalent mount gates.
- [ ] Prerequisite: Redis credential transport scoped checkpoint passes.
- [ ] M0: ratify safe traceback/source/sink contract and standalone checkpoint.
- [ ] M1: implement renderer, temporary snapshot and focused unit tests.
- [ ] M2: integrate API/error-factory and logging formatter sinks.
- [ ] M3: integrate run logs, RQ persistence and publication sinks.
- [ ] M4: focused canary/performance/UI compatibility validation and reviews.
- [ ] M5: run full pytest, npm lint and full npm tests; close SEC-05 from evidence.

## Decisions

- Operator decision: retain traceback observability; F5 is secret filtering, not
  trace removal.
- Preserve absolute paths and useful frame/source context.
- Use one sanitized representation; no audience-dependent traceback behavior.
- Preserve existing endpoint authorization and do not expose tracebacks on new
  surfaces merely because the renderer exists.
- No process-wide secret registry or cache. During traceback rendering only,
  read explicit configured secret sources, sanitize, then release references.
- Source metadata is selected per application/worker process; environment
  presence alone does not authorize opening a secret file. Metadata never stores
  values and is not the prohibited secret registry.
- F5 reads only files already mounted into a process. It does not decrypt SOPS,
  query Kubernetes Secret objects, read `flux-system/sops-age` or add RBAC.
- Decode every constituent of the comma-delimited authorization JWT key ring and
  include owning-process WEPPcloudR bearer/private-key/service-account sources.
- Leave current secret/client lifecycle unchanged; do not claim memory zeroization.
- Apply the same rendered string before every API/log/run-file/RQ/status sink.
- Fail closed to a generic diagnostic plus `error_id`; never raw fallback.
- Run Redis package first with scoped tests, then F5 with full Python/frontend
  suites.

## Starting Sink Inventory

- Flask/WEPPcloud `error_factory` and `exception_factory`, including
  `exception_factory.log`.
- rq-engine `error_response` and `error_response_with_traceback` call sites.
- query-engine exception handlers, validation responses and `exceptions.log`.
- browse/download exception handlers and run exception logs.
- RQ worker `handle_exception`, `handle_job_failure`, job `exc_info`/meta and
  task exception logging.
- Python logging handlers/formatters that receive `exc_info` from application
  and dependency loggers.
- WEPPcloudR control-plane reconciliation, framework/entry-point uncaught output
  and Kubernetes-captured container stdout/stderr.
- Status/error publishers that can forward traceback strings.

The implementation inventory must be repository-wide and disposition confirmed
peers; this list is not an exhaustive closure claim.

## Validation Matrix

| Input/state | Required result |
| --- | --- |
| Ordinary exception | Frames, paths, line/function and safe message retained |
| Mounted secret raw in message | Exact value absent in every sink |
| Percent-encoded/JSON-escaped secret | Derived value absent |
| Bearer/JWT/cookie/URI userinfo/PEM | Structurally redacted |
| Cause/context/note/ExceptionGroup | Bounded chain retained and sanitized |
| Locals/environment contain secret | Never captured or rendered |
| Configured file missing/unreadable during sanitization | Generic diagnostic + `error_id`; no raw fallback |
| Downstream-only or stale Kubernetes file setting | File is not opened by the current process profile |
| Comma-delimited authorization key ring | Every constituent key and encoding is absent |
| WEPPcloudR/Kubernetes token or TLS private key | Owning process redacts the synthetic canary |
| Mounted file replaced | Next exception redacts the new value without a cache |
| Container stdout/stderr | Final captured output contains no canary |
| No exception | No secret file read or sanitizer overhead path |
| Existing frontend stacktrace panel | Sanitized trace remains usable |

## Risks

- Missing sink leaks raw exception: inventory/failure matrix plus canary test at
  every write/serialize/persist boundary.
- Sanitizer becomes a secret registry: prohibit caching and inspect object/module
  state in tests.
- Secret-file failure hides all diagnostics: preserve error ID/type/frame summary
  only when it can be constructed without raw exception text.
- Exact-value redaction over-redacts useful text: only explicit configured values
  and bounded encodings; retain structural context.
- Global setting discovery opens a downstream/stale path: adapters select an
  explicit process profile and tests assert excluded paths are not touched.
- Logging formatter misses uncaught stderr: inventory entry points and capture
  final container output under production-equivalent synthetic mounts.
- Full suite duration/failure: required by operator; report exact outcome without
  converting segmented runs into a pass.

## Review Gates

- [ ] Redis prerequisite complete.
- [ ] Contract/source/sink matrix accepted.
- [ ] Correctness review passed.
- [ ] QA review passed.
- [ ] Dedicated security review passed.
- [ ] Focused canary and performance gates pass.
- [ ] Full pytest, npm lint and full npm tests pass.
- [ ] Audit board SEC-05 updated from evidence.

## Timeline

- 2026-11-11 18:27 UTC: scaffold and record design/order/test decisions.
- 2026-11-11 19:05 UTC: openwepp source review incorporated; no cluster access,
  SOPS decryption, implementation or deployment.
- Blocked: Redis package scoped acceptance.
- Pending: M0-M4 implementation/reviews.
- Pending: M5 full regression gates.

## Handoff

Continue from `prompts/active/implementation_execplan.md` only after the Redis
tracker records its green checkpoint. Start M0 from
`artifacts/20261111_kubernetes_secret_handling_review.md`; preserve its
process-owned source distinction and separate live-deployment boundary. Preserve
unrelated dirty work. No full suite or security closure has occurred.
