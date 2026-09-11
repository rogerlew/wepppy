# Contract reviews

Independent read-only reviewers: contract_correctness and contract_security.

- Security: accepted additive public boolean/task with no metadata exposure.
  Require malformed-present timestamps to fail closed and best-effort projection.
- Correctness: require serializing fresh durable state read and projection so
  delayed notifications cannot restore an invalidated marker. Same-second ties
  must be documented as conservatively incomplete.
- Disposition: canonical contract now explicitly includes both requirements.
  Dedicated short run-scoped Redis projection lock serializes notifiers; no
  authenticated GET writes or automatic reconciliation. Correctness accepted with ownership check before writing; security accepted.
  Both reviewers require final implementation and live validation.

Final source review: both reviewers accepted. Correctness follow-ups (recovery
dump persistence and nonpositive dependency timestamps) were fixed and reviewed.
Required live evidence subsequently passed: real Redis/NoDb clear/restore probe,
current-result reconciliation, public WebSocket boolean, and browser/reload.
See validation.md for evidence.
