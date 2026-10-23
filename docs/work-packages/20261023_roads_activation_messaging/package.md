# Roads activation error messaging

Status: active. Owner: Roger. Scope: user-requested error wording revision only.

Replace the internal module/controller disagreement text with an explanation of
incomplete activation, server responsibility and an actionable support handoff.
Retain the existing exception type, HTTP handling, traceback diagnostics and
fail-closed guard. No activation repair, deployment, data mutation or logging
redesign. Canonical authority: Roads specification, Common API error messages;
shared response envelope remains governed by docs/schemas/rq-response-contract.md.

Validation: existing Roads route tests and direct execution of the actual guard
for both mismatch directions and agreeing states. This is a bounded text-only
production edit; a full repository rerun is disproportionate.
