# Validation evidence

Date: 2026-10-27. Implementation and cross-platform validation; not deployed.

- Focused canonical container suite: **190 passed**, covering secret resolution,
  browse auth/routes, files, ordinary/dedicated downloads and D-Tale.
- Bootstrap Linux: **12 passed, 2 native-Windows tests skipped** (14 discovered).
  Includes real aria2c successful bytes and HTTP failures for ordinary, space and
  Unicode filenames; legacy ZIP bytes/extraction and truncated response behavior.
- Native Windows `blarhg`, Python 3.12.9 and repository-bundled `aria2c.exe`:
  **14 passed**. The unchanged batch wrapper returned 1 for manifest HTTP failure,
  22 for payload failure and 0 for successful bytes into a destination with spaces.
  A test-only urllib origin rewrite directs the fixed production URL to the
  disposable local HTTP fixture. No production project or host configuration was
  altered. The direct native aria tests also cover space and Unicode filenames.
- Real configured development-container probe invoked `get_run_owners_lazy` with
  SECRET_KEY/SECRET_KEY_FILE absent only in its subprocess. Lazy Flask startup
  raised the real configuration exception; the Starlette error boundary returned
  a response read over a real socket by the bootstrap client. Observed terminal:

      HTTP 500 Internal Server Error: Server configuration error: SECRET_KEY
      (or SECRET_KEY_FILE) is not configured. The service operator must correct
      this configuration before retrying.
      Error code: server_configuration_error
      Request ID: 14860c273f9448d697ab812e08522173

  The same ID appears beside the full server traceback. No aria2c launch followed.
  This uses a disposable route invoking the real lazy helper, not production TLS
  or routing certification. Default public response contains neither traceback
  nor secret filesystem path. Production explicit debug mode remains opt-in.

Correctness review reproduced and closed six issues before approval: real aria
session TAB syntax, false-empty indented error bodies, malformed secret encoding,
percent-encoded failed filenames, legacy error-code preservation and exception
pickle/process-pool compatibility. Security
review closed raw upstream 5xx disclosure and sanitization/redaction ordering.

The initial full-suite attempt was invalidated by implementation edits while
Python had earlier module versions cached: 631 passed/28 skipped, then stale
module ImportError. This was execution error, not a baseline defect.

The fresh serial attempt passed 2,630 cases with 48 skips before deliberate
interruption after 21m39s inside a slow, isolated soil matrix. An exact collection
inventory divides its 12,114 items into a completed 2,530-item prefix, 230 soil
cases, and a 9,354-item suffix. All 230 soil cases passed across eight disjoint
processes. Deduplicate the 147 soil cases already passed in the serial attempt.
Seven subsequently added GDAL/D-Tale and exception-pickle regression cases passed in the final focused
suite. This is segmented coverage, not a monolithic full-suite pass.

The suffix stopped with 4,084 passed/13 skipped at an unrelated Roads provenance
failure. `tests/roads/test_roads_publication.py::test_published_results_and_sources_are_current_or_explicitly_stale`
rejects an existing uncommitted `wepppy/nodb/mods/roads/roads.py` edit. The reviewed
hash is `25cbde5447e20110b52e3781a3046b4dda5bc026bc10f64fed68bba150a42201`,
which exactly matches `git show HEAD:wepppy/nodb/mods/roads/roads.py`. The unrelated
working-tree edit hashes to `bc58f90258044a34bf4614887276735f98256a8cfc5d7d868b68523d01d16978`.
No download-repair file appears in that provenance source inventory. Do not
update the scientific provenance record merely to silence this failure. Preserve
the unrelated edit; its owner must review/reconcile the artifact status.
The remaining 5,256 selected cases reached 4,943 passes/137 skips before a
browser-cache environment failure. The inherited PLAYWRIGHT_BROWSERS_PATH omitted
the internal `wepppy` directory. Rerunning the single browser case with the
already installed cache path passed (1 passed); no persistent configuration or
browser installation changed. The final tail passed 182 cases, including seven
previously passed reader tests; deduplicate those seven.

Final distinct coverage: **11,923 passed, 198 skipped, one unrelated Roads
provenance failure**. This includes the original 12,114 collected test items,
seven late regressions and one collection skip. No globally green suite is
claimed. Scoped publication proceeds with the unrelated blocker documented;
Roads provenance reconciliation belongs to that change's owner.

Browser rerun: `wctl docker compose exec -T -e PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers weppcloud bash -lc 'cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy MYPY_CACHE_DIR=/tmp/mypy_cache /opt/venv/bin/pytest tests/weppcloud/test_run_catalog_reader.py::test_real_file_sql_http_browser_chain --maxfail=1'`.

Native Windows Python also verified HTTPS against the public production landing
page: HTTP 200 and a response byte. This is TLS/transport evidence only; no token
was sent and no authenticated production project or new server deployment is
claimed. The actual failure-message contract was tested on disposable fixtures.

Reproduce with `wctl run-pytest tests/config/test_secrets.py tests/microservices/test_browse_auth_routes.py tests/microservices/test_dedicated_download_service.py tests/microservices/test_download.py tests/microservices/test_browse_routes.py tests/microservices/test_browse_dtale.py`;
in the bootstrap repository, `python -m unittest discover -s tests -v`.
Full sanity: `wctl run-pytest tests --maxfail=1`.

The retained [probe](lazy_flask_client_probe.py) reproduces this boundary in a fresh configured dev-container process. Pass a directory containing the two bootstrap helper modules; it removes the secret settings only inside that subprocess. Broad-exception enforcement passed (zero net new broad catches); stub-completeness passed; code-quality observation completed. Documentation lint and spelling preview pass.

The secret-reader API stubtest passes; an existing optional-value inference ambiguity was corrected with a local type annotation only (no runtime change), followed by seven passing secret-reader tests. The named `<run_id>_aria2c.spec` inventory remains inspectable after successful retrieval; native and Linux reruns assert that failed retrieval does not reuse or overwrite an earlier inventory.

Paired bootstrap source commit: `d765507` (`wepppy-win-bootstrap`). Server source and this evidence publish together; deployment remains held.
