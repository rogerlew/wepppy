# NoDb Agents Guide

This file captures the operational quirks of `NoDbBase` so debugging (and test
harnesses) stay consistent across agents.

## Locking & TTL Overrides

* Every NoDb controller serializes state to `<wd>/<controller>.nodb` and keeps a
  distributed lock in Redis (`nodb-lock:<runid>:<relpath>`). The default TTL is
  read from `WEPPPY_LOCK_TTL_SECONDS` (6 hours if unset) so long-running jobs do
  not lose their lock mid-operation.
* Tests often need a much shorter TTL to simulate expired locks. Instead of
  monkeypatching `LOCK_DEFAULT_TTL`, use the helper context manager:

  ```python
  from wepppy.nodb.base import temporary_lock_ttl

  with temporary_lock_ttl(1):
      controller = MyController.getInstance(wd)
      with controller.locked():
          ...
  ```

  The helper uses a `ContextVar`, so nested overrides automatically revert when
  the `with` block exits.
* `NoDbBase.lock()` now consults the override for every acquisition, and
  `_assert_lock_still_owned()` re-checks that the TTL has not expired before we
  persist. When the TTL is expired, the lock is forcefully cleared and the user
  receives a retryable error instead of corrupting state.

## Cache Refresh Semantics

* Instances are cached per working directory. A cache hit is only reused when
  all of the following match the on-disk file: `os.stat` signature (mtime +
  size) and SHA-256 digest (when available). Modifying the file out of band must
  update the mtime (the tests rely on `os.utime`) and the new digest for the
  change to be detected.
* When the `.nodb` file changes while a cached instance is still live, the cache
  object is updated in-place so any references held by callers (controllers,
  fixtures) now see the latest attributes.
* Redis caches store the serialized JSON; we compute a digest of the cached text
  and compare it against the current file digest. A mismatch causes the Redis
  entry to be ignored and refreshed to avoid stale state.

## Common Debug Hooks

* Set `WEPPPY_DEBUG_NODB_REFRESH=1` to trace cache decisions, TTL checks, and
  lock acquisitions.
* `temporary_lock_ttl(None)` clears any overrides and returns to the default.
* `redis_lock_client` is expected to exist for nearly every test that exercises
  locking; the test harness stubs the client when running without Redis.

## When Adding Features

* Make sure every new public helper is exported via `__all__` so tests can opt
  in explicitly.
* If you add behaviors that depend on environment variables, also expose a test
  override (similar to the TTL helper) so targeted pytest modules can simulate
  edge cases without rewriting global state.
