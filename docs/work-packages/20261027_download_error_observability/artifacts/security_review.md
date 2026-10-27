# Download error observability security review

## Findings and verdict

| ID | Severity | Finding and evidence | Required remediation | Disposition |
| --- | --- | --- | --- | --- |
| SEC-01 | Medium | The initial shared HTTP handler copied arbitrary 5xx detail into public JSON. `browse/dtale.py` forwards upstream descriptions, including exception strings emitted by `webservices/dtale/dtale.py`, so an upstream I/O or parser failure could expose private paths or exception contents. | Default to a safe correlated response; expose only deliberately classified public messages. Cover raw upstream detail rejection. | Resolved: `browse/errors.py` now requires `PublicHTTPException` for public operational detail. Plain string and dictionary 500 details were independently checked; `test_upstream_http_500_detail_stays_in_correlated_log` covers the application boundary. |
| SEC-02 | Low | The initial bootstrap formatter redacted before removing terminal controls. An error containing a synthetic token split by ESC reproduced plaintext token output after sanitization. | Remove controls before final token replacement and add regression coverage. | Resolved: `scripts/download_http.py` now redacts last. Independent reproduction and `test_error_redaction_happens_after_control_sanitization` pass. |

**Security gate: PASS for the reviewed changes.** No unresolved high, medium or
low findings in this scope. No new risk acceptance is required. This does not
replace correctness, QA, platform validation or deployment approval.

## Scope and triage

- Reviewer: independent `security_reviewer` agent `pilot_security`, 2026-10-27.
- Package: `20261027_download_error_observability`.
- Context: working changes over WEPPpy `810d5b862` and bootstrap `38acc44`.
- Security impact: **high**; public error responses, secret configuration and
  authenticated download clients require this dedicated gate.
- Reviewed server files: `wepppy/config/secrets.py`, browse `errors.py`, `auth.py`,
  `browse.py`, `files_api.py`, `_download.py`, `dtale.py`, sibling
  `wepppy/microservices/_gdalinfo.py`, and dedicated download `app.py`; related
  regression tests and the browse filesystem contract.
- Reviewed sibling bootstrap files: `scripts/download_http.py`,
  `download_with_aria2c.py`, `download_weppcloud_project.py`, both retained
  `wget_download_weppcloud_project` wrappers, and `tests/test_download_errors.py`.
- Related assessments: [correctness](correctness_review.md), [QA](qa_review.md)
  and [validation](validation.md). Unrelated Roads, pure-controls, binaries and
  preexisting downloaded manifests are excluded.

The threat model includes unauthenticated callers, authenticated users requesting
their own files, hostile correlation headers, private backend exceptions, and
untrusted HTTP error bodies displayed in a terminal. Production HTTPS and the
existing server manifest are trusted to describe the requested project. No new
authorization, service, dependency, deployment or queue boundary is introduced.

## Surface checks

### Valid states and access controls

- Missing optional JWT state continues to request public projects anonymously;
  private projects retain their authentication and scope checks. Existing valid
  JWTs, browser navigation, grouped scope restrictions and non-500 denials stay
  on their existing paths.
- Secret file precedence remains authoritative. Missing, empty, unreadable and
  malformed-encoding secrets fail explicitly; a bad file cannot silently fall
  back to an environment secret. `SecretConfigurationError` remains compatible
  with callers catching `RuntimeError`.
- Successful downloads, HEAD/range behavior, containment and restricted-path
  guards are covered by the existing scoped service tests. Generic download
  eligibility does not acquire model-status restrictions.
- Final transitive review includes all five NoDir translators: browse, files,
  download, D-Tale and GDAL. Each retains established 500/503 codes through the
  shared authored-message mapping; private exception messages remain in logs.
  Grouped D-Tale/GDAL and other browse-family auth catches preserve the explicit
  safe classification through `BrowseAuthError.to_http_exception()` without
  changing authentication decisions. Raw upstream 5xx remains default-safe.
- An actually empty successful manifest remains valid. HTML/error-shaped
  manifests and orphan indented options fail before aria2c; fresh temporary
  manifests prevent stale-file reuse. This approval does not claim exhaustive
  format validation or replace the correctness state inventory.

### Secrets, output and correlation

- Classified configuration messages expose setting names and recovery guidance,
  without values or secret-file paths. Unexpected failures and unclassified
  HTTP 5xx details use a generic message; full exceptions remain in operator logs.
- Correlation IDs use the existing bounded character grammar, are cached per
  request, and appear consistently in the response and log message. Invalid
  caller IDs are replaced. IDs provide correlation, not authentication or proof
  of a unique trusted caller.
- Browser error text is escaped. Default machine responses do not contain raw
  stack traces. Error-body reads are bounded to 8 KiB, terminal controls are
  removed, and the active JWT is redacted after formatting/sanitization.
- No credentials or production identifiers were used in review fixtures or
  written to this artifact.

### Network, subprocess and filesystem behavior

- Standard-library redirect handling preserves same-origin authorization and
  removes Authorization on a changed origin. Direct local HTTP checks exercised
  both cases and preserved successful response bytes.
- aria2c is invoked with an argument list, without a shell. Existing concurrency,
  destination arguments and transfer implementation remain. The current transfer
  manifest and failed-session files live in a temporary directory cleaned on
  exit. The established inspectable `<run_id>_aria2c.spec` is retained after
  successful retrieval and validation; it is never consumed as a fallback.
- Failed manifest requests stop before transfer. Positive aria2c failures remain
  nonzero; failed-file diagnostics examine only URLs from the fetched manifest,
  with at most ten Range requests. A successful diagnostic recheck cannot turn
  the original transfer failure into success.
- This patch does not alter archive extraction semantics, run-tree writes,
  NoDb/Redis locking, queue wiring, MCP authority, CI/CD permissions or dependency
  trust. Those unchanged surfaces require no new gate here.

## Validation evidence

Independently executed:

- `wctl run-pytest tests/config/test_secrets.py tests/microservices/test_browse_auth_routes.py tests/microservices/test_dedicated_download_service.py tests/microservices/test_browse_dtale.py --maxfail=1`:
  **143 passed**, six dependency deprecation warnings.
- Final expansion: `wctl run-pytest tests/microservices/test_browse_auth_routes.py -k 'runtime_path_5xx_codes or group_jwt_configuration_error or upstream_http_500_detail' --maxfail=1`:
  **23 passed**, including ten NoDir translator/code cases, twelve grouped-route
  configuration cases, and raw-upstream-detail suppression.
- Bootstrap `python3 -m unittest discover -s tests -v`: **9 passed**. One fixture
  emitted an HTTPError resource-cleanup warning; assertions passed.
- Direct production-helper checks: arbitrary exception text and plain/dictionary
  HTTP 500 details absent from responses; invalid correlation ID replaced;
  returned ID identical in body/header; reconstructed-token redaction passes.
- Two real local HTTP servers: same-origin redirect preserved the synthetic
  Bearer token; cross-origin redirect delivered the response without forwarding
  Authorization. Both returned the exact fixture bytes.

The correctness review separately records real Linux aria2c success and failure
checks. The server-to-client and full-suite evidence remain owned by package
validation; this review does not claim to have executed them all.

## Residual scope and sign-off

Native Windows batch execution and bundled Windows aria2c were **not validated by
this reviewer**. The package owner and QA record fourteen passing native Windows
tests and twelve passing Linux tests with two Windows-only skips in the linked
validation artifacts; those are separately attributed platform evidence.

Existing aria2c credential-in-argv behavior and trust in server manifest URLs and
options remain; this patch does not claim to remove local process-list exposure
or sandbox arbitrary manifests. Existing explicit browser debug mode can expose
additional exception details; the default-response guarantee assumes it is off.
Full operator logs remain sensitive and should be shared accordingly. A response
whose headers have already streamed cannot be replaced by a new error envelope.
The separate query-engine feature-access error handler is outside this changed
browse response boundary; this review does not certify that handler's existing
exception-detail privacy contract.

Security reviewer sign-off: `pilot_security`, 2026-10-27. No production mutation
was performed. Package-owner closeout must retain correctness/QA disposition and
accurate platform/deployment status; this is approval of the scoped security
changes only.
