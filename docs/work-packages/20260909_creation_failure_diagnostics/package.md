# Creation failure diagnostics

## Status and scope

2026-09-09: contract checkpoint in preparation; implementation pending.
The operator requested an actionable explanation for Portland creation failure
`2a50c192697b4256a025be32c47a4f4d`, rather than an instruction to search logs.
Scope is every failure exit from both named-preset create aliases in
`wepppy/microservices/rq_engine/project_routes.py` and creation log correlation.
No authentication, configuration defaults, module installation, queue wiring,
cleanup behavior, or project artifact schemas change.

## Evidence and intended outcome

Forest's rq-engine log records `Exception: unknown mod portland` during Ron
initialization. The response discards that cause. `_log_creation_exception`
stores the error ID only as a LogRecord extra, which the deployed text formatter
does not render. A secondary cleanup failure must not replace the original
initialization diagnosis. The supplied ID is not searchable in these text logs,
so the matching Portland request is evidence of the failure signature, not
independent proof of correlation to that exact ID.

Users must see the unavailable module and the appropriate next action. Other
recognized initialization failures must explain their cause without reflecting
private paths or credentials. Unexpected failures must honestly identify the
failed stage and retain a usable support reference, without inventing a cause.
Ordinary text logs must include the same ID and full original traceback.

## Security and compatibility

Security impact: high because this changes a public error response. A dedicated
security review is required before closure. Use explicit safe classifications,
not arbitrary exception strings or regex-based credential scrubbing. Preserve
HTTP 500, `run_initialization_failed`, the envelope, and cleanup/idempotency
behavior. Success and auth failures retain their existing contracts.

## Acceptance and observation

Regress the actual unavailable-module signature, missing files, permissions,
storage exhaustion, missing imports, unexpected exceptions, hostile diagnostic
strings, and secondary cleanup failure. Verify both create route aliases and
that valid creation still redirects. Exercise real Ron initialization in the
running Compose image, then inspect the HTTP response and text-log correlation.
Run focused tests, the existing broad suite, and documentation lint. Independent
correctness and security reviews must close medium/high findings.

Health signal: the Portland failure names `portland` without requiring log
access. Danger signals: generic messages for recognized causes, leaked secrets,
missing correlation, or changed success/auth behavior. Observation is recurrence
based; this adds no temporary retry or fallback mitigation to sunset.

## Related authority

- [RQ response contract](../../schemas/rq-response-contract.md)
- [Project creation policy](../../schemas/project-creation-policy.md)
- [Contract-first standard](../../standards/contract-first-change-standard.md)
- [Hardening lifecycle](../../standards/hardening-lifecycle-standard.md)

The project-owned configuration contract remains applicable to materialization
and creation lifecycle; those behaviors are outside this response-only delta.
