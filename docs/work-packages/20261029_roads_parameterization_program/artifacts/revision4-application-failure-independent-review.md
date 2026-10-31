# Revision-4 application failure assessment

Independent Codex AI implementation review, 2026-10-31. This assessment changed
no production source, test, assertion, timeout, native executable or credential.

## Confirmed findings

**P2 — existing test isolation defect, unrelated to the native revision.**
The upload test's 503 is emitted by request admission before the upload handler.
The retained traceback is `redis.exceptions.AuthenticationError: Authentication
required`, not a model execution error. `wepppy/microservices/rq_engine/__init__.py:80`
captures `_LIFECYCLE_REDIS_CLIENT = redis.Redis` at import. The session fixture at
`tests/conftest.py:98` subsequently replaces `redis.Redis` but does not replace
that captured constructor. Its per-test secret isolation also removes
`REDIS_PASSWORD_FILE`. The preceding Redis configuration tests clear cached
connection URLs, exposing a real Redis connection without credentials.

The unchanged upload test passes alone (1 passed, 0.87 seconds). Running the
unchanged `tests/test_redis_settings.py` immediately before that test reproduces
the original authentication failure (17 passed, then 1 failed, 0.94 seconds).
This establishes an order-dependent test defect in baseline code. The route's
fail-closed 503 behavior must remain intact. The smallest prospective correction
is a test fixture that explicitly controls the middleware's captured constructor
alongside the Redis stub, with the retained two-module order regression. This
review does not authorize or implement that correction, and does not suggest
supplying real credentials to make a unit test pass.

**P2 — Roads coordination test deadline exceeded; persistent inversion disproved
for both retained failures.** `tests/wepp/interchange/test_roads_lifecycle.py:294`
waits at most ten seconds for the spawned publisher's result. Both failed runs
nevertheless produced a current catalog, zero pending requests, and a completed
archive containing exactly the published catalog bytes (11 entries). The
archive therefore acquired the guard and completed after the queue deadline.
The two original failures are retained, not reclassified as passing tests.

The actual code follows the documented catalog-before-Roads order:
`wepppy/wepp/interchange/_roads_lifecycle.py:83` acquires the catalog guard before
the exclusive Roads lock; nested catalog calls use the same process/thread's
reentrant ownership in `wepppy/query_engine/catalog_refresh.py:233`. This matches
`docs/schemas/roads-preparation-lifecycle-contract.md` and
`docs/schemas/query-engine-catalog-refresh-contract.md`.

The unchanged failing test passes alone (1 passed, 14.40 seconds), and the entire
unchanged lifecycle module passes (20 passed, 20.08 seconds). Catalog-to-archive
file modification time spans are 8.205 and 11.928 seconds in the original failed
runs, versus 0.011 and 0.012 seconds in the focused passing runs. Catalog
publication includes file and directory `fsync`. These observations support a
load-sensitive completion delay; they do not identify the exact scheduler or I/O
cause, because no syscall timing was captured during the original failures.
No timeout increase or lock change is justified by this review.

## Provenance and disposition

All implicated production and test files match committed baseline
`3cf0e331de17ab422c90b5711b2481387ad45b14` byte-for-byte. Neither failing path
launches a WEPP model binary. The Roads catalog scan uses the existing WEPPpyo3
catalog API, whose installed artifact was not changed by this release. Native
binary regression is therefore not supported by these failures.

Exact original and reproduction logs remain under
`out/roads-parameterization-program-20261031/revision4-promotion/`.
`review-lifecycle-retained/` preserves both failed attempts' completed artifacts
and the passing controls, with hashes and timestamps. The companion
`revision4-application-failure-independent-review.json` binds source, installed
binary and log identities, and the retained artifact readback.

This assessment is not complete application acceptance: unfinished shard tails
still require execution, and accepted node IDs must be accounted for exactly
once. The upload isolation defect needs a separately recorded disposition;
successful isolated tests must not silently erase either original failure.
