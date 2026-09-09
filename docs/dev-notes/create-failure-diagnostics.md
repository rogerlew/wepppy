# Create failure diagnostics

The named-preset links on `/weppcloud/create/` submit to `/rq-engine/create/`.
Its `/rq-engine/api/create/` alias has the same error behavior. Failed requests
retain the canonical `error.message`, `error.details`, `error.code`, and
`error_id` envelope.

## What users see

Read `error.details` for the failed operation, recognized cause, and next action.
For example, an unavailable Portland module produces:

> Run initialization failed. Required module 'portland' is unavailable on this
> server. Check the configured module name, or ask the administrator to install
> or enable the required module before retrying.

Missing required files, denied permissions, full storage, missing Python
dependencies, Redis/database operation failures, and account identity failures
have distinct explanations. Repeating a request will not repair an unavailable
module or missing server data. An unclassified failure says that its cause
could not be safely identified and provides the error reference for support.

## Operator diagnosis

Every failed response, including validation/authentication failures, writes a
summary containing the same `error_id`, HTTP status, and error code to rq-engine
logs. Exceptions retain their original traceback with that ID. Search the
rq-engine service logs for the response's ID; the field appears in ordinary text
as well as exception metadata. Cleanup and reservation-release failures retain
the original diagnosis and correlation.

Forest reproduced `unknown mod portland`: the preset requires a module absent
from the runtime registry. Diagnostic improvements do not install that module.
The observed `Directory not empty` cleanup error was a secondary failure.
Optional TTL/README failures remain nonfatal and are logged separately.

## Developer maintenance

Keep public causes explicitly classified; never forward arbitrary exception
strings or scrub credentials with a general-purpose regex. The only dynamic
exception diagnostic is the contract-bounded unknown-module identifier.
Retain stage-specific error codes/statuses and existing lifecycle behavior.
Otherwise uncaught application failures return HTTP 500 `run_creation_failed`.
The outer boundary does not add compensating cleanup for previously unhandled
post-allocation errors; that existing lifecycle limitation is separate work.

Run `wctl run-pytest tests/microservices/test_rq_engine_project_routes.py tests/microservices/test_rq_engine_builder_routes.py`
and exercise the real create link when changing these diagnostics. Builder
imports the reservation-release helper, so preserve its two-argument call when
adding creation-specific logging context. Canonical rules:
[initialization diagnostics](../schemas/rq-response-contract.md#named-preset-creation-initialization-diagnostics)
and [all-failure coverage](../schemas/rq-response-contract.md#named-preset-creation-failure-coverage).
