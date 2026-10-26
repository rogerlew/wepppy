# Local implementation validation

Date: 2026-10-26 UTC. Deployment excluded by operator instruction.

1. `docker compose -f docker/docker-compose.prod.yml -f docker/docker-compose.prod.wepp1.yml config --no-interpolate --format json` passed.
2. Rendered the same composition with the HEAD version of the override and
   compared full parsed JSON. Only the two command tokens `--timeout`, `120`
   differ. Eight workers and all other service settings are unchanged.
3. Passed the resulting command to `gunicorn.app.wsgiapp.WSGIApplication`
   inside a separate Python process in the existing production container.
   Result: timeout 120, graceful_timeout 30, workers 8,
   worker_class uvicorn.workers.UvicornWorker. No server started or reloaded.
4. Targeted regression suite: 333 passed, 13 warnings in 22.48 seconds.
5. Changed-file broad-exception enforcement: PASS, net delta zero.
6. Canonical contracts and affected README documentation lint: zero errors/warnings.
7. Spelling preview: corrected canceled in new prose; retained unrelated existing
   PROJECT_TRACKER proper names. Whitespace check passed.
8. Observe-only code-quality report generated; no threshold-based failure.
9. Broad regression: `wctl run-pytest tests --maxfail=1 -q` stopped after
   9,931 passed, 155 skipped, 15 subtests passed in 3005.54 seconds. The sole
   failure was an obsolete expectation in test_diff_bp.py that archive-looking
   physical names must be forbidden. Updated that test to actual filesystem
   semantics, including real .nodir files/directories and no virtual traversal.
   No application source changed. The diff module then passed all six tests.
10. Resumed original pytest collection from the start of test_diff_bp.py using
    `wctl run-python` and a collection hook that removes only preceding items.
    Result: 1,863 passed, one skipped, 55 warnings in 163.62 seconds (exit 0).
    This segment overlaps the initial run's one passing diff test. The full
    command was not a single green invocation; remaining coverage passed after
    correcting the contract-obsolete regression.
    Set PLAYWRIGHT_BROWSERS_PATH for this process to the installed browser at
    /workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers; the default
    omits a wepppy component. No browser download or persistent setting changed.

Reproducible continuation (via `wctl run-python -c`):

```python
import os, sys, pytest
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers"
class Remaining:
    def pytest_collection_modifyitems(self, items):
        start = next(i for i, item in enumerate(items)
                     if item.nodeid.startswith("tests/weppcloud/routes/test_diff_bp.py::"))
        del items[:start]
sys.exit(pytest.main(["tests", "-q", "--maxfail=1"], plugins=[Remaining()]))
```

The existing live production command remains unchanged at implicit timeout 30.
HTTP load evidence was collected at that original setting, not at 120.
