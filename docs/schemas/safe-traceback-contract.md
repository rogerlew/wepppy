# Safe traceback contract

Status: intended behavior approved by execution of the safe traceback plan;
implementation conformance pending. Scope: Python exception diagnostics only.

## Diagnostic compatibility

Existing HTTP statuses, response keys, authorization, error IDs, controlled-error
schemas and traceback field-presence decisions remain authoritative. Where a
trace is already exposed, one sanitized representation serves API, logging,
run-file, RQ persistence and publication consumers. Preserve ordinary absolute
paths, source lines, functions, line numbers, exception types, messages, causes,
contexts, notes and exception groups. Secrets in any of these fields take
precedence over preservation. Never capture locals or environment mappings.

“Full” or “original” traceback in the [RQ response contract](rq-response-contract.md)
means this sanitized diagnostic, never an unfiltered retained copy. Existing
controlled-error and [browse](browse-filesystem-contract.md) omissions remain:
filtering does not authorize adding diagnostics to responses that omit them.
Existing frontend stacktrace panels consume the same fields without changes.

## Source ownership and lifetime

Each process adapter explicitly selects immutable source metadata (setting name,
file setting, optional/required state and decoder). Values exist only inside one
render operation; there is no registry, cache, serialization, public snapshot API
or claim of zeroization. No secret files are opened on successful requests or
ordinary non-exception logging paths. Rendering an error/stack is exceptional
work, including expected validation failures that already construct diagnostics.

Prefer the configured file over the corresponding legacy environment value,
matching each consumer's whitespace/framing rules. A configured local file that
is unreadable, invalid, empty or oversized fails closed. An absent optional
source contributes nothing. A required source absent from both inputs fails
closed. Optional denotes optional configuration, never permission to ignore a
configured broken source. Do not scan directories or arbitrary environment
variables. Downstream-only settings are excluded even when present.

The following source families are explicit metadata, not mount discovery:

| Family | Settings / decoding |
| --- | --- |
| Redis | `REDIS_PASSWORD`; explicit legacy `REDIS_URL`, `RQ_REDIS_URL`, `SESSION_REDIS_URL` userinfo decoded into credential constituents |
| Database | `POSTGRES_PASSWORD`; `SQLALCHEMY_DATABASE_URI` and `DATABASE_URL` credential constituents (consumer precedence preserved) |
| Flask | `SECRET_KEY`, `SECURITY_PASSWORD_SALT` |
| Authorization | `WEPP_AUTH_JWT_SECRET`, `WEPP_AUTH_JWT_SECRETS` (each nonempty comma-separated stripped key) |
| Web authentication | `AGENT_JWT_SECRET`, `CAP_SECRET` |
| Mail/OAuth | `ZOHO_NOREPLY_EMAIL_PASSWORD`, `OAUTH_GITHUB_CLIENT_SECRET`, `OAUTH_GOOGLE_CLIENT_SECRET`, `OAUTH_ORCID_CLIENT_SECRET`; consumer-supported environment aliases `GITHUB_OAUTH_CLIENT_SECRET`, `GITHUB_OAUTH_SECRET_KEY`, `GOOGLE_OAUTH_CLIENT_SECRET`, `ORCID_OAUTH_CLIENT_SECRET`, `ORCID_OAUTH_SECRET_KEY` |
| Model service clients | `OPENTOPOGRAPHY_API_KEY`, `CLIMATE_ENGINE_API_KEY`, `OPENET_API_KEY`, `WC_TOKEN` |
| Query MCP | `WEPP_MCP_JWT_SECRET` |
| D-Tale | `DTALE_INTERNAL_TOKEN` |
| Discord | `weppcloud2/discord_bot/.bot_token` relative to the installed package; metadata lookup never imports the credential client |
| Profile playback | `ADMIN_PASSWORD` / `ADMIN_PASSWORD_FILE` |
| Wojak bootstrap | environment-only `AGENT_JWT_TOKEN`, `AGENT_JWT_SECRET` loaded by its Redis environment bridge |
| Batch render client | `WEPPCLOUDR_K8S_IDENTITY_TOKEN_FILE` (raw token) |
| Render control plane | `WEPPCLOUDR_CONTROL_PLANE_TOKEN_FILE`, `WEPPCLOUDR_TLS_KEY_FILE` (PEM), projected `/var/run/secrets/kubernetes.io/serviceaccount/token` |

Ordinary names use their corresponding `_FILE` input when supported by the
consumer. Environment-only aliases do not gain invented file inputs. Public
certificates, CA bundles, namespace files and `EXTERNAL_HOST` are not secrets.

The Flask-init set is Redis, database (including URL credentials), Flask,
`AGENT_JWT_SECRET`, mail/OAuth and the Discord client imported by NoDb core. Importing `weppcloud.app` resolves this entire
set, including when imported lazily by another process. This set does not by
itself include CAP, authorization key rings or model-service API keys.

| Process | Owned source families |
| --- | --- |
| Web | Flask-init, authorization, CAP, model service clients |
| rq-engine | Flask-init, authorization, CAP, model service clients used by routes |
| Browse | Flask-init, authorization, D-Tale |
| Download | Flask-init, authorization |
| Query | Flask-init, authorization, MCP |
| D-Tale | Flask-init, D-Tale (private-scope authorization imports web app but does not decode JWTs) |
| Elevation/metquery/wmesque/wmesque2 | Redis; no model service keys without a verified local consumer |
| Default/declarative RQ | Flask-init, model service clients |
| Batch RQ | Default RQ plus batch render client |
| Fork/archive RQ | Redis, Discord; database when project-commit mode is postgres (explicit mode-based metadata, not mount presence) |
| Scheduler | Redis, database, Discord |
| Render control plane | Redis, render control plane |
| Shape converter | None; stale Redis setting is excluded |
| Profile playback | Flask-init, ADMIN_PASSWORD; model execution is submitted over HTTP |
| Wojak bootstrap | Wojak environment token/signing secret only |

The implicit Discord file may be absent because its consumer disables notifications
on missing files. A present unreadable/invalid file fails closed. This exception
is explicit package-file metadata and does not weaken configured `_FILE` handling.
No directories or package modules are imported to discover values.

Sources absent in a deployment are optional unless the adapter's actual startup
contract requires them. The web profile excludes the downstream batch identity
token. Transitive imports must be audited before final acceptance: shared code
must use the calling process profile rather than installing a different app's
profile at import time. A startup adapter selects metadata before loading
secret-consuming application modules. Missing source coverage blocks acceptance.

## Rendering and failure

Use standard-library `TracebackException` with `capture_locals=False`. Sanitize
the complete diagnostic, including source context, notes and cached exception
text. Replace exact configured values longest-first, including raw, percent
encoding (upper/lower escape hex), form encoding, JSON escaped and Python repr
escaped forms. Decode key rings into members; PEM contributes the full key and
non-header body lines. Bounded URL decoding extracts legacy credentials even
when exceptions contain only the password.

Structural filtering additionally covers URI userinfo, Authorization and
Proxy-Authorization, Cookie/Set-Cookie values, bearer/basic credentials, JWTs,
PEM private-key blocks and secret/password/token/API-key assignments, including
quoted dictionary/JSON forms. This is a bounded credential grammar, not a claim
to identify arbitrary unknown secrets or arbitrary encodings.

Application-authored authentication errors must retain an actionable reason
after filtering. Use unambiguous prose such as “An access token is required in
the Authorization header.” for a missing credential, and “Access token missing
subject claim.” for invalid claims. Do not accept placeholder-filled boilerplate
as a usability fix or exempt raw exception text/credential-shaped strings from
filtering. This wording preserves useful diagnostics without guessing whether
an unknown value after a credential scheme is a secret. Status codes, response
fields and authentication decisions remain unchanged.

Resource ceilings are implementation safety bounds: 64 KiB per source, 256
source constituents, 1 MiB diagnostic input/output, 64 structured levels and
1,024 structured nodes, 100 traceback frames, 10 group levels and 15 group
members per level. Reject oversized source or diagnostic input before emitting
any fragment. Never truncate unsanitized input: a partial credential must not
escape because it straddles an output limit. Recursion/cycles, unsupported
structured objects, decoder, formatter or source failures return only
`Diagnostic unavailable (sanitization failed).` plus an existing server-generated
error ID when its provenance is trusted. Caller-supplied IDs are not echoed in
fail-closed diagnostic text when the snapshot cannot be loaded. Do not echo the failing source, exception or caller
supplied identifier based only on safe correlation syntax: a secret may itself
match that syntax. Outer response identifiers keep their established contract.

These fixed bounds are not configurable model/workflow parameterization and do
not change scientific values or task admission, so no parameterization ADR is
required. Retain performance and representative long-trace evidence before
closure; revisions to these bounds require contract review.

Structured sanitation preserves JSON keys/types for supported dict/list/tuple
and scalar diagnostic values; sanitize strings and keys. If sanitation fails,
replace diagnostic content with the generic text while preserving outer response
schema/status/error-code/error-ID. Snapshots never cross an output boundary.

## Logging, startup and persistence ordering

Each production handler uses a safe formatter for exception records. Format the
entire output with a copied LogRecord, clearing stale `exc_text`, and sanitize
message, arguments, exception, stack and formatter extras together. Do not mutate
the record into a raw cached exception for a later handler. Explicit error
writers sanitize preformatted exception strings even without `exc_info`.
Ordinary non-exception records do not load sources. A filter alone is insufficient.

NoDb QueueHandler must sanitize before `prepare()` formats and clears exception
provenance; downstream handlers cannot infer that lost provenance. Exception
records are those with `exc_info`, cached `exc_text`, `stack_info`, explicit
diagnostic marking, or exception objects in arguments. Plain preformatted
exception strings require producer sanitation/marking; severity alone is not
sufficient and must not cause ordinary log records to load sources.

Handlers that bypass `format`, especially `StatusMessengerHandler.emit`, must
sanitize exceptional records before publishing. Retain ordinary progress syntax.
Every direct run-file writer sanitizes before opening/writing diagnostic content.

RQ 2.12 constructs a raw local exception string before worker hooks. Sanitize
`handle_job_failure` input before superclass persistence (including result-store
and failure metadata). Sanitize `handle_exception` logging and meta without
changing exception-handler/failure-callback type/value/traceback semantics.
Audit callbacks and webhooks independently; raw callback inputs are in-process
control flow, never authorization for raw external output. Preserve retry,
dependency, status, controlled-error and cancellation behavior.

Inventory framework and interpreter output separately: gunicorn/uvicorn/RQ
logging, sys/thread/unraisable exception hooks, subprocess diagnostics and shell
Python startup probes. Install the earliest supported safe hook or prove no
secret has loaded before an unhooked bounded failure. No global stdout proxy,
secret registry, secret lifecycle change or raw fallback is authorized.

## Acceptance and operational meaning

Each API, final handler output, file, RQ Redis record and publication needs direct
canary readback. Include chains/groups/notes, encoded credentials, source-line
secrets, key-ring members, bearer/JWT/PEM and fail-closed cases. Verify file
replacement is observed on the next render without a cache. Current-source
snapshots cannot discover retired values still held by existing clients; this
package does not alter rotation/client lifecycles or promise historical scrubbing.

Synthetic container acceptance uses production-equivalent non-root identities,
paths, read-only 0444 mounts and captured stdout/stderr. Do not access SOPS or a
live cluster. A missing locally owned source fails closed, while downstream and
stale sources are never opened. Healthy execution must perform no snapshot reads.

Users retain stacktrace context and error IDs; `[REDACTED]` denotes removed
credential material. Operators investigate a generic sanitization failure using
the correlated failure and configured mount health, never enable raw diagnostics.
Existing logs and Redis records are not retroactively rewritten. Deployment and
live incident recovery remain separately authorized.

## Adapter maintenance

`wepppy/observability/secret_profiles.py` owns source metadata; additions require
a verified consumer. `safe_logging.install` selects the first process owner before
application imports, wraps existing/future handlers, and covers interpreter,
thread, unraisable and multiprocessing target failures. Verify those hooks when
upgrading Python or RQ. Spawn pools explicitly initialize their worker profile.

Persist exception-derived status/manifest/CSV fields through `safe_text` before
serialization; delayed plain strings lose logging exception provenance. Keep
original exception objects and messages for parsing, retry and callback decisions.
`safe_diagnostics` preserves adapter-owned names and the outer list/dict/None
shape on failure while discarding failed content. It does not make arbitrary
user-supplied dictionary keys into schema.

Standalone corpus, fuzzing, benchmark and data-preparation scripts are outside
production service acceptance. Generic agent transcripts/command output and
historical stored diagnostics are outside Python exception sanitization. The
production-invoked Wojak bootstrap catch and playback results are included.
