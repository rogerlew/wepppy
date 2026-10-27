# Download error observability secondary QA

Reviewer: `pilot_qa`, October 27, 2026. Reviewed after independent
[correctness](correctness_review.md) and [security](security_review.md) PASS.
Scope: changed browse/download diagnostics, secret classification, bootstrap
clients/wrappers, regression tests, user/operator guidance and evidence quality.
Unrelated Roads, Usersum, binaries and downloaded manifests are excluded.
The reviewer made no runtime changes or production actions.

## Verdict and publication boundary

**QA PASS for the reviewed implementation and completed focused/platform
validation.** Two test-quality findings were repaired and rechecked below. No
unresolved runtime quality finding requires another implementation change.

Final [validation](validation.md), package, tracker and ExecPlan now retain
completed segmented coverage: **11,923 distinct passes, 198 skips and one
unrelated Roads provenance failure**. This is not a globally green or monolithic
full-suite result. The unrelated working-tree source/hash mismatch remains with
its owner's change; it is not waived or repaired by this scoped publication.
The first attempt invalidated by concurrent source edits remains excluded.
Deployment and ordinary-user smoke on the deployed revision remain separate;
paired bootstrap source is committed as `d765507`.

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| QA-01 | Medium | Bootstrap `tests/test_download_errors.py` patched `Path.home` only in the parent process. Legacy and CLI subprocess tests inherited the developer's real home and could read a real JWT or fail because of local token contents. | Resolved: subprocesses now receive a shared isolated `child_env` with temporary home/profile paths. Native HTTP wrapper execution already isolates those paths. Final Linux and Windows suites pass after this change. |
| QA-02 | Medium | The new `DownloadRedirect` credential boundary was documented but protected only by an ad hoc security check, leaving no retained regression for future edits. | Resolved: `test_redirect_auth_scope_and_successful_bytes` uses two actual local HTTP servers, verifies same-origin authorization retention and changed-origin removal, and reads exact successful bytes. It passes on Linux and Windows. |

### Final inspectable-inventory compatibility check

The package owner identified that the initial temporary-only approach removed
the established `<run_id>_aria2c.spec` output. The final client restores that
inspectable inventory only after successful HTTP retrieval, UTF-8 decoding and
manifest validation. aria2c still consumes the current response from its private
temporary copy. A failed retrieval preserves the previous inventory and cannot
launch aria2c with it. The README describes both artifacts' roles.

Rechecked the final implementation and inventory assertions; test working
directories now use disposable storage. Final reruns after this correction:
Linux **12 passed, two Windows-only skips**; native Windows **14 passed**.
No additional QA finding. Server sources were unchanged by this client correction.

### Final timeout and peer-consumer checks

The final `open_download` default is `None`, preserving initial manifest/archive
retrieval without the newly introduced 60-second socket timeout. Only failed-file
diagnostic requests set an explicit ten-second socket inactivity timeout. This
avoids imposing a new short deadline on a successful existing workflow; it does
not promise a bounded total elapsed time. The README uses the same distinction.
Final reruns again passed on Linux (12 passes/two skips) and Windows (14 passes).

The final transitive-consumer repair applies the same shared safe NoDir mapping
to GDAL and preserves authored auth messages in grouped GDAL/D-Tale routes. It
does not add a second error policy. Existing parameterized regressions now cover
five translators and twelve grouped routes; primary correctness/security reviews
independently approve those peers. That checkpoint recorded 189 focused passes.
The subsequent exception-pickle compatibility correction and regression increase
the final focused result to 190; correctness review closes it as COR-06.

## Maintainability and user-facing behavior

`wepppy/microservices/browse/errors.py` centralizes correlation, safe unexpected
failures and deliberately public operational messages. The five NoDir translators
share the same safe mapping, retaining established error codes. Typed secret
failures retain `RuntimeError` compatibility and private operator traceback
details without placing those details in default responses.

In the bootstrap repository, `scripts/download_http.py` owns bounded HTTP
formatting/redaction and redirects; `scripts/download_with_aria2c.py` owns manifest
validation and transfer orchestration. Thin shell/batch wrappers avoid duplicated
error handling. The repair retains aria2c and standard-library HTTP support;
no additional dependency or payload transfer engine is introduced.

The README now explains Python prerequisites, quoted destinations, empty successful
manifests, nonzero transfer results, delayed failed-file diagnostics and operator
recovery for server configuration failures. It directs users to share the message
and request ID rather than credentials. Canonical server guidance distinguishes
safe client text from full operator logs and requires an ordinary-user recovery
check. Successful files and archives remain byte-verified in the tests.

## Evidence inspected

- Final focused canonical container output: **190 passed**, six dependency warnings.
- Final bootstrap Linux output: **14 discovered, 12 passed, two native-Windows
  tests skipped**. Real aria2c transfers cover ordinary, space and Unicode names.
- Final native Windows output: **14 passed** after QA test changes. The actual
  batch wrapper, Python and bundled aria2c cover manifest failure, payload failure,
  successful bytes and a destination containing spaces.
- The retained [lazy-Flask probe](lazy_flask_client_probe.py) and execution output
  show the real missing-secret exception traversing a local HTTP socket into the
  actual bootstrap parser. The returned request ID matches the server traceback;
  the terminal message identifies `SECRET_KEY` and operator recovery. This is a
  disposable route invoking the real lazy helper, not production routing/TLS proof.
- Tests cover original failed-session TAB syntax, encoded filenames, false-empty
  error manifests, stable NoDir codes, bounded plain/large error bodies, interrupted
  archives, token sanitization and successful archive extraction. These check
  user-visible behavior and real transfer artifacts rather than only mocked calls.

The reviewer inspected the terminal logs and final test source; the implementation
owner executed the suites and native Windows session. No full-suite PASS is
inferred from focused counts. [Failure-class coverage](failure_class_matrix.md)
identifies the shared consumers and excluded boundaries.

### Final broad-assessment reconciliation

The retained validation ledger reconciles the original 12,114 collected items,
seven late regressions and one collection skip. The serial attempt stopped at
2,630 passes/48 skips; disjoint soil runs and the remaining suffix/tail provide
segmented coverage. The suffix recorded 4,084 passes/13 skips before the unrelated
Roads provenance failure. Its remaining selection recorded 4,943 passes/137 skips
before a browser-cache environment error; correcting only the invocation's
existing cache path passed that single browser case. The final tail passed 182
cases, including seven previously passed reader cases that are deduplicated.

Final distinct totals are **11,923 passed, 198 skipped and one unrelated failure**.
The earlier soil overlap is also deduplicated as described in validation.
Those counts are the package owner's reconciled broad evidence, not a new QA-run
suite. The historical interrupted/error attempts remain explicit. All scoped
download findings are closed; the Roads artifact-provenance blocker is retained
without modifying scientific provenance or unrelated code.

## Residual debt and nonblocking follow-ups

The server trusts authors to use `PublicHTTPException` only for deliberately safe
messages; future translators must retain the upstream-detail rejection tests.
The client still trusts server-authored manifest URLs/options and retains aria2c's
existing credential-in-arguments behavior, as recorded by security review.
Post-header stream failures cannot become replacement JSON responses. Those
existing boundaries are explicit and do not justify expanding this repair.

Diagnostic rechecks are bounded to ten requests with ten-second socket inactivity
timeouts; total elapsed time is not bounded by that setting. They can delay the
final exit and observe a later state than the original failure.
The README explains that a successful recheck never changes the failed transfer
result. A future progress indicator is optional usability work, not a release gate.

No broad refactor is needed. Keep the shared helpers small and preserve the
retained real-aria and cross-origin tests. Local package closeout is consistent
with the scoped PASS and documented unrelated broad-suite failure; production
deployment and ordinary-user smoke remain outstanding operational steps.

Validation: scoped `wctl doc-lint` passed with zero errors or warnings; the
`uk2us` spelling preview produced no changes.
