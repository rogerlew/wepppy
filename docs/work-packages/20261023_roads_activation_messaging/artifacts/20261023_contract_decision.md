# Contract decision

Starting revision: `fc3234efc6da58ff1da896dfab5b2dd5875988c2`.
Operator approval: Roger explicitly requested “revise the user-facing messaging”.
Task-scoped commit authority persists from this session.

Applicable contracts: Roads specification (Common API error messages), shared
RQ response contract (unchanged error envelopes), NoDb persistence/concurrency
contract (unchanged; no state writes). Intended delta: only the RuntimeError
message for disagreeing Roads/project activation flags. New message:

> Roads is unavailable because of a server configuration problem. This request could not be processed. Contact support and include this project's URL.

Rationale: identify the failed operation, place responsibility on the server,
and provide support with the project reference without suggesting that retrying,
changing GeoJSON or toggling the module repairs production's missing activation
call. The helper serves upload and other Roads operations, so say “request”.
Existing exception type, response status/envelope, traceback diagnostics and
read-only guard are preserved. No new fields, dependencies, auth changes or
production deployment. Security impact low; wording discloses no saved values.
Implementation conformance pending the reviewed ancestor commit.

State matrix: absent controller retains existing initialization error; agreeing
enabled and disabled flags retain existing behavior for empty/populated or legacy
controllers; either mismatch retains RuntimeError with the revised message.
Malformed input handling is unchanged because rejection precedes file parsing.
An activation mismatch remains an exceptional server-state failure. Verify the
real guard directly with supplied controller states; no persistence/filesystem
boundary is changed. Run existing Roads route tests; do not add a permanent test
that merely duplicates a literal string. Final independent review required.
