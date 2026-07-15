# Code Review - Fork Console Status Backpressure and Recovery

## Review Metadata

- **Reviewer**: Codex distinct code-review pass
- **Date**: 2026-07-15
- **Scope**: Worker telemetry, StatusStream buffering/rendering, fork-console lifecycle/storage, template, tests, and generated assets.
- **Disposition**: Pass; no unresolved findings.

## Findings

| ID | Severity | Finding | Resolution | Status |
| --- | --- | --- | --- | --- |
| CR-01 | Medium | A destination run ID restored from session storage could become an HTML-injection boundary if interpolated into markup. | All dynamic fork links now use DOM construction, text nodes/`textContent`, and URL-encoded paths. Added a malicious-storage regression test. | Resolved |

## Review Notes

- Rsync continues to use list arguments, `Popen` without a shell, a sanitized environment, concurrent pipe draining, and explicit return-code enforcement.
- Both stdout and stderr have hard 200-line tails; no per-line status publication remains.
- WebSocket terminal events only request an immediate poll. Only `controlBase` poll events with `source: "poll"` mutate terminal UI state.
- StatusStream preserves immediate append/trigger callbacks while batching only DOM replacement. Total retention remains hard bounded and ordinary messages are evicted before important lifecycle/error messages when possible.
- Session records are scoped by run/config, contain identifiers only, validate before use, and clear on terminal state.
- No route, authorization, queue, dependency, schema, or external-dependency contract changed; RQ graph validation is therefore not applicable.
- Generated `status_stream.js` is synchronized, and the generated-controller stale check passes.

## Residual Notes

The shared fork channel remains an architectural limitation, but idle disconnection plus authoritative job polling removes it as a terminal-state authority. Production observation, not additional code in this package, is the appropriate next check.
