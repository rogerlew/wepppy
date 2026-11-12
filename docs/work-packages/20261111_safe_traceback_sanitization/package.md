# Safe traceback and exceptional-path secret sanitization

**Status**: Complete — locally verified 2026-11-12 UTC at `dfab59bb1`. Full Python/frontend gates and independent reviews pass. No production deployment.

**Timezone**: UTC

## Overview

Remediate security audit finding F5/SEC-05 without removing the traceback
observability on which WEPPcloud currently depends. Introduce one lightweight,
framework-neutral traceback renderer that preserves useful frames, exception
context and absolute paths while removing configured secret values and
credential-shaped data before a traceback reaches an API, service log, run log,
RQ failure record or status/error publication.

There is one sanitized representation, not separate public/owner/admin variants.
Existing endpoint authorization and existing decisions about which responses
contain diagnostic fields remain unchanged. Each production adapter selects
immutable metadata for the secret sources actually consumed by that process;
values are loaded only while rendering an exception and are never registered or
cached. This package begins only after Redis credential transport passes its
scoped gate, then runs focused tests followed by full pytest, npm lint and full
npm tests.

## Threat Model

- **Assets**: mounted/environment secret values, authorization headers/tokens,
  Redis/database/OAuth credentials, private keys and operational tracebacks.
- **Adversaries/failures**: an account holder or API caller who triggers a
  library exception containing a credential; a traceback written to multiple
  sinks before filtering; formatter bypass; and sanitizer failure that falls
  back to raw text.
- **Trust boundaries**: exception object to renderer; mounted secret file to
  temporary snapshot; Kubernetes projected file to non-root process; renderer
  to API/log/run file/RQ Redis/status/container stdout or stderr sink.
- **Assumption to prove**: every traceback sink consumes the same fail-closed
  sanitized text and no sink retains the raw configured canary.

## Objectives

- Define a canonical safe-traceback contract that preserves existing diagnostic
  schema, frames, source paths and exception chaining.
- Add a pure, lightweight module based on Python's `TracebackException` with
  locals disabled, bounded exception-group/output handling and no dependency.
- On each exceptional rendering call, temporarily load only the process-owned
  mounted/environment sources selected by its adapter, decode compound key-ring
  values, derive bounded encoded variants, redact, then release references
  without claiming memory zeroization.
- Apply structural redaction for URI userinfo, authorization/cookie values,
  bearer/JWT material, PEM blocks and sensitive key/value assignments.
- Route Flask, rq-engine, query-engine, browse/download, WEPPcloudR control
  plane, RQ worker/persistence, run-file, configured logging formatter and
  container stdout/stderr traceback paths through the module.
- Preserve current one-representation API behavior and existing frontend
  stacktrace panels.
- Pass focused canary/performance/sink tests, full pytest, npm lint and full npm
  tests.

## Scope

### Included

- A new canonical `docs/schemas/safe-traceback-contract.md` and amendments to
  `docs/schemas/rq-response-contract.md`, controller/error documentation and
  affected service/operator docs.
- A small module under `wepppy/observability/` providing temporary secret
  snapshots, text/structured redaction, safe traceback/stack rendering and
  logging formatter integration.
- Explicit process-to-secret source profiles, including file/env precedence,
  required/optional state and bounded decoders. Do not glob `/run/secrets` or
  infer ownership from arbitrary environment/file variables.
- Existing traceback-bearing API/log/persistence sinks in Flask/WEPPcloud,
  rq-engine, query-engine, browse/download, WEPPcloudR control plane and RQ
  workers, including Kubernetes-captured stdout/stderr.
- Direct canary tests for raw, percent-encoded and JSON-escaped mounted/env
  values, comma-delimited key rings, credential URLs, headers, JWTs, PEM,
  exception notes/chains/groups and sanitizer failure.
- Production-equivalent container tests using synthetic secret files at the
  Kubernetes paths, modes and non-root identities, without decrypting SOPS or
  contacting a live cluster.
- Full repository Python and primary frontend gates after focused acceptance.

### Explicitly Out of Scope

- Removing tracebacks, absolute paths, source locations or useful exception
  chaining solely as hardening.
- Different traceback content for anonymous, public, owner, collaborator, admin
  or other audiences. Existing authorization remains authoritative.
- A process-wide secret registry, cache, secret manager, rotation change or
  modification to how application clients retain credentials.
- Reading arbitrary mounted files or treating every `*_FILE` environment value
  as authorization to open a file.
- Kubernetes Secret API access, SOPS decryption, access to `flux-system/sops-age`
  or new workload RBAC. F5 reads only files already available to each process.
- Generic redaction of every non-exception INFO/debug log record. Existing
  structured logging rules remain; this package owns traceback/exception paths.
- Redis credential URL/argv removal, owned by the prerequisite package.
- Go traceback/error architecture. Go services must continue not to stringify
  secrets, but the new module is Python-specific.
- Production deployment without separate authorization.

## Complexity Budget

- **Existing mechanisms reused**: `get_secret` source names, Python
  `TracebackException`, logging `Formatter`, existing error factories,
  correlation/error IDs, RQ worker hooks and current response schemas.
- **New mechanisms permitted**: one pure-Python safe-traceback module, immutable
  source-profile metadata and one configured formatter integration; no external
  dependency, secret-value registry or persistent state.
- **Simplest plausible change tested first**: format one exception with locals
  disabled, read explicit secret sources for that call, replace exact/encoded and
  structural credential forms, then return one string to all sinks.
- **Real acceptance condition**: synthetic secret canaries never appear in any
  retained traceback sink while diagnostic frames and UI behavior remain.
- **Evidence required before escalation**: a retained sink-specific failure that
  the central renderer/formatter cannot intercept safely.
- **Explicitly prohibited expansion**: secret registry/service, new datastore,
  telemetry backend, audience policy, dependency or logging-topology redesign.

## Generated Artifact Validation Gate

- **Applicable**: no for scientific/user artifacts. API bodies, log files and RQ
  failure strings are diagnostic outputs and require direct semantic readback.
- **Direct unmocked boundary**: raise canary exceptions through each real error
  factory/handler/worker hook and read the resulting API body, captured handler,
  run log, RQ record and publication.
- **Actual environment gate**: production deployment is separate; local
  production-equivalent service processes/handlers and synthetic container
  secret mounts are required before closure.
- **Highest completion claim currently supported**: scaffolded/diagnosed.

## Stakeholders

- **Decision owner**: WEPPpy maintainer/security owner.
- **Primary implementers**: observability, WEPPcloud, rq-engine, query-engine and
  RQ maintainers.
- **Reviewers**: independent correctness, QA and security reviewers.
- **Security reviewer**: required and independent of implementation.

## Success Criteria

- [ ] Redis credential transport reaches its green scoped checkpoint first.
- [ ] Safe traceback contract and explicit secret-source/sink inventories are
      reviewed and committed before implementation.
- [ ] Every Python process profile identifies only its locally consumed sources;
      downstream-only and stale `*_FILE` paths are never opened.
- [ ] One sanitizer preserves frames, absolute paths, exception type/message,
      chaining and current response field compatibility after redaction.
- [ ] Locals and environment mappings are never captured.
- [ ] Secret values are loaded only during rendering from explicit sources; no
      registry/cache/lifecycle change is introduced.
- [ ] Compound authorization key rings, WEPPcloudR tokens/private key and the
      control-plane service-account token are sanitized in their owning process.
- [ ] Raw, encoded and structured canaries are absent from every API/log/run/RQ/
      status traceback sink; sanitizer/source failure never emits raw text.
- [ ] Normal non-exception paths perform no secret-file reads and show no
      material throughput regression.
- [ ] Synthetic Kubernetes-path tests prove `0444` non-root reads, file
      replacement visibility and final container stdout/stderr sanitization.
- [ ] Existing stacktrace UI and error correlation continue to work.
- [ ] Focused tests pass, followed by `wctl run-pytest tests --maxfail=1`,
      `wctl run-npm lint` and `wctl run-npm test`.
- [ ] Independent correctness, QA and security reviews pass.

## Parameterization ADR Gate

- **Parameterization change present**: potentially, if output/depth/size limits
  become configurable defaults.
- **ADR required**: decide at contract checkpoint; required before implementing
  configurable thresholds.
- **Decision provenance captured**: this package and contract artifact.

## Dependencies

### Prerequisites

- [Redis credential transport hardening](../20261111_redis_credential_transport/package.md)
  must pass scoped validation and reviews first.
- Ratify the configured secret-source inventory and safe-rendering failure mode.

### Blocks

- Closure of F5/SEC-05 under the revised filtered-traceback contract.

## Related Packages

- **Depends on**: Redis credential transport, linked above.
- **Related**: [F4 status/preflight WebSocket authorization](../20261111_status_preflight_websocket_authorization/package.md),
  which already introduced bounded stream-message redaction.
- **Deployment compatibility evidence**:
  [Kubernetes secret handling review](artifacts/20261111_kubernetes_secret_handling_review.md).

## Timeline Estimate

- **Expected duration**: 4-8 focused working days after Redis acceptance.
- **Complexity**: high due to broad diagnostic sink coverage.
- **Risk level**: high security and observability impact.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **CWE/OWASP mapping**: CWE-200 and CWE-532; OWASP Top 10 2021 A02/A09.
- **Triage rationale**: the package handles raw exceptions and mounted secret
  values at API, log and Redis persistence boundaries.
- **Security review artifact**:
  [artifacts/20261111_security_review.md](artifacts/20261111_security_review.md).
- **QA review artifact**:
  [artifacts/20261111_qa_review.md](artifacts/20261111_qa_review.md).

## Hardening and Observation Model

- **Failure signature**: configured canary or credential-shaped material appears
  in any traceback sink, or useful diagnostic structure disappears.
- **Health signals**: zero canary occurrences; preserved frames/UI/correlation;
  no normal-path file reads; bounded exceptional-path performance.
- **Danger signals**: a global registry/cache, audience branching, raw fallback,
  arbitrary file reads, environment-presence source inference, swallowed errors
  or per-log-record secret file I/O.
- **Observation window**: focused and full-suite validation plus separately
  authorized environment observation before production.
- **Temporary calluses**: none planned.

## Testing Scope Decision

Focused tests drive implementation, but package closure requires the exact full
commands below even if frontend source is unchanged:

```bash
wctl run-pytest tests --maxfail=1
wctl run-npm lint
wctl run-npm test
```

Do not substitute segmented or patch-scoped results for these gates.

## References

- `wepppy/weppcloud/utils/helpers.py`
- `wepppy/microservices/rq_engine/responses.py`
- `wepppy/query_engine/app/server.py`
- `wepppy/rq/rq_worker.py`
- `wepppy/rq/exception_logging.py`
- `docs/schemas/rq-response-contract.md`
- `artifacts/20261111_kubernetes_secret_handling_review.md`

## Handoff

Redis prerequisite and F5 contract checkpoint passed before implementation.
M0-M5 are complete. See `artifacts/20261111_full_validation.md` for exact
full-gate results, candidate binding and the no-deployment boundary.
The implemented design preserves paths and one traceback representation,
loads configured secrets only during exception rendering, and leaves the current
secret lifecycle unchanged. Kubernetes source selection is process-owned and
uses mounted files only; live openwepp rollout remains a separate authorization.
