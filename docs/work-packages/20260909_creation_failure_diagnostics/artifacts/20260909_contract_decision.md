# Creation diagnostics contract decision

## Baseline and authorization

Starting revision: `c11941f9145a8e0473e2e3226d8834fe8ff5d34f`.
Operator instruction on 2026-09-09: "the error needs to inform the user why it
failed" after receiving `run_initialization_failed` for Portland creation.
This authorizes actionable creation diagnostics. The operator subsequently
instructed "commit and fix please. i want all create failures observable",
authorizing the scoped checkpoint commit and expanding coverage to every
failure from both named-preset create aliases. No implementation files have
been edited.

## Authority and exact delta

Amend the RQ response contract's creation-specific diagnostics and cross-link
the project creation policy's Error and Safety Contracts. Require a safe cause
and next action for recognized Ron initialization failures, keep the existing
HTTP status/code/envelope, and render correlation IDs in ordinary log messages.
The existing CSRF and project-owned configuration contracts apply unchanged:
authorization, materialization, publication, idempotency, and cleanup are not
changed. The generic log-only option remains available for unrelated endpoints.
The expanded coverage amendment adds a formatted response-summary log for all
4xx/5xx exits, safe cause/stage diagnostics for all creation infrastructure
failures, and a canonical HTTP 500 `run_creation_failed` envelope for otherwise
unhandled application exceptions. Redis/database unavailability and invalid
account identity join the safe cause categories. Request validation/auth
semantics and nonfatal TTL/README behavior remain unchanged. Scope excludes
Builder, fork, upload and batch, which are not the reported create-link path.

Recognized causes are unavailable NoDb module, missing required file, denied
filesystem permission, exhausted storage, and unavailable Python dependency.
Only an ASCII module identifier from Ron's exact whole-message
`unknown mod <identifier>` signature may be included dynamically, with grammar
`[A-Za-z0-9_][A-Za-z0-9_-]{0,63}`. This explicitly includes identifiers supplied
by supported config overrides; they are the sole exception to the prohibition
on reflecting arbitrary request values. Do not reflect raw exception text,
paths, import details, credentials, or tracebacks publicly.
Unclassified errors identify the actual failed stage (run initialization for
Ron failures, project creation at the outer boundary) and state that the cause
could not be safely determined, with the error ID.
For unavailable modules, users verify the configured module name or have the
administrator install/enable the requirement. This covers both shipped presets
and invalid `nodb:mods` overrides without assuming every case needs installation.

## Rationale and discrepancy

The current response makes even a diagnosed missing module opaque to users,
creating repeated support work. Correlation alone is insufficient user help.
Raw exception forwarding was rejected because this endpoint is public and
initializers may include host paths or credentials. Classifying known failure
conditions supplies useful information without claiming every unknown exception
can be explained safely. Missing rendered log IDs are an existing conformance
defect; richer public diagnosis is an intended behavior amendment.

## Compatibility and regression plan

No keys, existing handled status/error codes, project schemas, defaults, or
queue edges change. Otherwise unhandled 500 responses gain the canonical code
`run_creation_failed` rather than returning an opaque framework 500.
Clients must already treat diagnostic prose as display text. Verify both
`/create/` and `/api/create/`, the original exception when cleanup also fails,
and searchable text logs with matching error ID and traceback.

Input matrix: authenticated and existing CAPTCHA creation; both route aliases;
valid config and invalid config through their existing contracts; supported
legacy `nodb:mods` overrides, including an unknown bounded identifier and hostile
strings. State matrix:
absent required module/file/dependency and denied or exhausted storage are
exceptional infrastructure failures; an empty/never-used optional mod list is
valid; populated supported modules and legacy presets retain normal creation;
hostile diagnostic strings use the safe unclassified response. Do not claim
exhaustive initialization coverage. Real Ron execution must reproduce the
Portland signature independently of mocked route regression tests.

Expanded matrix: policy/writer misconfiguration; missing/invalid authentication
and request validation; Redis/database/identity exceptions containing private
paths or credentials; idempotency conflict/in-progress/replay; unexpected
exceptions before and after allocation; and nonfatal TTL/README exceptions.
Verify safe operation-specific details and matching response-summary log IDs,
statuses and codes. Preserve success/replay HTTP 303, in-progress Retry-After,
and existing lifecycle mutations. Do not call arbitrary SQLAlchemy errors a
service outage: use a database-operation diagnosis unless the exception proves
a connection failure. Unhandled post-allocation errors must become observable
without introducing cleanup/publication behavior beyond the existing path.

## Security impact and review disposition

High by public-route classification. Two independent read-only contract reviews
passed after COR-01 and SEC-C01 were resolved and confirmed; see
[review dispositions](20260909_contract_reviews.md). A dedicated implementation
security review must assess disclosure, bounded module
identifiers, preserved auth, and valid-state noninterference. Implementation and
deployment conformance are pending. Expanded coverage passed both independent
reviews after COR-02 and security documentation comments were resolved and
confirmed. The operator authorized this standalone checkpoint commit before
implementation.
