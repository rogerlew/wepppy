# Download error observability correctness review

Reviewer: `pilot_review`, October 27, 2026. Scope: changed browse/download error
handling and the three bootstrap download entry points. Unrelated Roads changes
are excluded. The reviewer did not modify implementation or operate production.

**Correctness verdict: PASS.** All six reproduced findings below are fixed and
independently rechecked. Native Windows evidence closes the initial platform
gap. Full-suite and publication disposition belong in [validation](validation.md);
this review does not authorize deployment.

## Findings

1. **COR-01, medium, fixed and independently rechecked:** the first
   `scripts/download_with_aria2c.py:manifest_urls` implementation rejected the
   trailing tab that real aria2c writes after failed URLs in `--save-session`.
   Consequently a file HTTP 500 raised a manifest-format error instead of fetching
   its error body and request ID, and lost the original aria2c exit code. The
   original mocked fixture omitted that tab. After the parser and fixture change,
   real Linux aria2c returns 22 and the helper displays the configuration message,
   error code and request ID. Successful transfer preserves exact bytes.
2. **COR-02, medium, fixed and independently rechecked:** `manifest_urls` initially skips every indented
   line, including HTML/JSON error text and orphan options before any URL.
   Confirmed `  <html>Login</html>`, indented JSON and ` out=orphan.txt` each parse
   as no URLs. The caller then reports an empty project and returns zero. The
   repair rejects nonblank content/options before a URL while preserving empty
   and comment-only manifests; the new regressions pass.
3. **COR-03, low, fixed and independently rechecked:** `wepppy/config/secrets.py:get_secret` reads UTF-8 but
   classifies only `OSError` as an unreadable setting. A file containing byte
   `0xff` raises `UnicodeDecodeError`, bypassing the safe setting-specific message.
   The repair classifies decoding failure as unreadable configuration. Repeating
   the invalid-UTF-8 probe now produces the typed exception with the setting name
   and no private path. This issue did not permit false success or disclose the
   exception under the default handler.
4. **COR-04, medium, fixed and independently rechecked:** the failed-file diagnostic originally compared aria2c's
   saved URL against the original manifest using raw string equality. The server
   emits raw filenames; aria2c percent-encodes spaces in its saved session. With
   `/file name.txt`, real aria2c fails on `/file%20name.txt`, and the helper skips
   that URL, so its error body/request ID never reaches the user. The local HTTP
   fixture received only the original transfer request, with no diagnostic
   follow-up. The repair compares normalized original/saved URLs. Real Linux
   aria2c retests with both `file name.txt` and `café.txt` now make the diagnostic
   follow-up, display the server message/code/reference, and preserve exit 22.
5. **COR-05, medium, fixed and independently rechecked:** after restricting public 5xx text to
   `PublicHTTPException`, only the main browse NoDir translator was converted.
   The translators in `_download.py`, `dtale.py` and `files_api.py` still raise
   plain HTTP exceptions. Their `NODIR_INVALID_ARCHIVE`/500 and `NODIR_LOCKED`/503
   responses therefore become `internal_error`, violating the stable codes in
   `docs/schemas/nodir-contract-spec.md` and `nodir_interface_spec.md`. Direct
   execution of the shared handler with those exact translator envelopes
   confirmed both code losses. The repair applies one authored safe mapping to
   all five translators, including the later-discovered sibling `_gdalinfo.py`.
   Independently ran the final retained response regressions: **10 passed**
   (five translators by two statuses/codes); private messages remain absent and
   request IDs present.
6. **COR-06, medium, fixed and independently rechecked:** the initial shared
   `SecretConfigurationError` required constructor metadata that inherited
   exception pickling did not provide, so reconstruction raised `TypeError`.
   That could replace the intended configuration failure or break exception
   delivery from a process pool. The explicit reducer now reconstructs with
   message/setting/reason while preserving the original one-message `args` and
   instance state. Independently round-tripped a real `require_secret` failure
   through every supported pickle protocol, then transported it from a real
   `ProcessPoolExecutor` worker. Exception type, private diagnostic and safe
   metadata survived; a subsequent task in the same pool succeeded. No private
   path appeared in the restored public message. The retained regression uses
   real pickle serialization rather than a mocked transport.

## Reviewed behavior and evidence

- The typed secret exception remains a `RuntimeError`; existing callers and
  file-over-environment precedence retain their contract. Safe messages omit
  secret values and secret-file paths. Unexpected exceptions log full context
  with the same request ID returned in the response body/header.
  Real exception serialization and process-pool transport were independently
  checked after the final constructor/reducer repair; the focused aggregate log
  reports 190 passing tests for that revision.
- Browse, manifest, individual-file and dedicated archive application boundaries
  share diagnostics. Existing non-500 authentication decisions, range handling
  and successful byte delivery remain in their existing paths. An HTTP response
  already streaming cannot be replaced by an error JSON response.
- A failed manifest request occurs before any temporary manifest or aria2c
  invocation; successful manifests use a fresh temporary file rather than an old
  run-named file. Positive aria2c failure codes are propagated; process signals
  map to nonzero exit. Failed-file diagnostics are bounded to ten requests and
  bounded error-body reads.
- Independently ran bootstrap unittest discovery: the initial six tests and the
  subsequent eight-test revision passed, including the legacy archive HTTP and
  interrupted-response CLI cases without tracebacks or partial archive writes.
  Then exercised installed Linux aria2c against the local HTTP fixture, without
  mocking the subprocess: success returned zero and exactly
  `exact-success-bytes`; file HTTP 500 produced the real trailing-tab session and
  exposed COR-01. After repair the same real transfer failure returned 22 and
  printed its safe body/code/request ID.

## Validation gaps and compatibility scope

Independently reviewed the implementation agent's native Windows execution log:
**14 tests passed**. The unchanged batch entry point, Python client and bundled
aria2c ran against a disposable HTTP fixture; only the fixed service origin was
redirected for the test. Manifest failure returned 1, file failure returned 22,
and success returned 0 with exact bytes in a destination containing spaces.
Bundled aria2c also passed ordinary, space-containing and Unicode filename cases.
Legacy archive success preserved ZIP/extracted bytes; HTTP failure and interrupted
responses exited nonzero without writing a partial archive.

The reviewer's Linux run selected 12 tests: 11 passed and the then-existing
Windows-only test was skipped. Subsequent native wrapper/redirect additions were
covered by the native 14-test log above; the package aggregate retains the final
Linux count. Real Linux aria2c was also exercised independently while reproducing
and closing COR-01/COR-04.

Reviewed the container HTTP harness and output for the original failure path:
real `get_run_owners_lazy` imports Flask, missing `SECRET_KEY` raises the typed
exception, the Starlette boundary returns its safe correlated HTTP 500, and the
bootstrap parser displays message/code/reference without starting aria2c. The
harness uses a disposable route calling that real lazy helper; production routing
and public TLS infrastructure were not exercised. Retained aggregate evidence
and shared consumer coverage belong in [validation](validation.md) and the
[failure-class matrix](failure_class_matrix.md).

### Final transitive-consumer sweep

Rechecked `browse.create_app` registration, not only files under its directory:
the sibling `wepppy/microservices/_gdalinfo.py` shares the changed handler. D-Tale
and GDAL group authorization now use `BrowseAuthError.to_http_exception`, retaining
the authored JWT recovery message. Five NoDir translators preserve stable
500/503 codes through the shared safe mapping. Report routes already delegate to
`handle_auth_error`; browse flow delegates to the main browse NoDir translator.
Raw GDAL stderr/JSON-decoding HTTP 500 detail remains unclassified, so the default
handler logs it and returns only a safe reference.

Independently ran `wctl run-pytest tests/microservices/test_browse_auth_routes.py -k
'runtime_path_5xx or group_jwt_configuration_error' --maxfail=1`: **22 passed**
(ten NoDir cases and twelve actual culvert/batch route cases, including D-Tale
and GDAL). This closes the additional transitive-consumer masking gaps.

Query-engine `feature_access.py` also imports `BrowseAuthError`, but its separate
HTTP handler already publishes explicit detail and does not use the newly
restrictive browse handler. No new masking regression is introduced there. Its
existing stacktrace/privacy behavior is outside this download package and is
not certified by this review.

The initially proposed same-origin rejection would restrict behavior: server manifest generation
in `wepppy/microservices/browse/_download.py:_resolve_external_origin` supports
configured external hosts. The fixed production bootstrap origin normally
matches those URLs. The implementation agent removed that rejection to preserve
configured manifest origins; cross-origin urllib redirects strip the
Authorization header. Dedicated security review owns credential-forwarding
assessment.

No production deployment or successful production download is certified by this
review. The first full-suite attempt was invalidated by implementation edits
during collection; its partial result is not a release gate. The package owner
must retain the stable full-suite result before publication. Explicit browser
debug mode remains outside the default safe-response guarantee.
