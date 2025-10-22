# WEPPpy Test Suite

> Quick guide for humans who just want to run the tests or understand the layout. Agents should see [`tests/AGENTS.md`](AGENTS.md) for the deep dive.

## What's in `tests/`

```
tests/
├── README.md        # Human-friendly quick-start (this file)
├── AGENTS.md        # Agent playbook: fixtures, patterns, expectations
├── conftest.py      # Shared pytest fixtures (Redis stub, helpers)
├── nodb/            # NoDb controller checks
├── weppcloud/       # Flask routes, microservices, websocket glue
├── climates/        # Climate data integrations
├── wepp/            # WEPP executables, translators, soils utilities
├── query_engine/    # DuckDB/MCP tests
└── data/            # Static fixtures and sample payloads
```

Most files mirror the module they cover. For example, `tests/weppcloud/routes/test_climate_bp.py` targets `wepppy/weppcloud/routes/nodb_api/climate_bp.py`.

## Running Tests (recommended workflow)

1. **Ensure environment variables are available**
   - Keep `docker/.env` populated with the shared defaults (UID/GID, secrets, host paths).
  - Optionally create a project-root `.env` (gitignored) or point `WCTL_HOST_ENV` at a personal override.
  - Export anything ad-hoc (`export OPENTOPOGRAPHY_API_KEY=…`) before running tests; `wctl` will fold it in.

2. **Use the `wctl` wrapper so tests run inside the dev container:**

   ```bash
   # Fast feedback on a specific area
   wctl run-pytest tests/weppcloud/routes/test_climate_bp.py

   # Directory-level sweep
   wctl run-pytest tests/nodb

   # Final gate before you push or hand off work
   wctl run-pytest tests --maxfail=1
   ```

   Under the hood this expands to `docker compose … exec weppcloud pytest …`, but `wctl` handles the env file merging and keeps the command short.

3. **Helpful pytest flags**

   ```bash
   wctl run-pytest tests -k climate     # pattern match
   wctl run-pytest tests -vv            # verbose output
   wctl run-pytest tests --lf           # last failures only
   wctl run-pytest tests --cov=wepppy   # coverage (HTML report in htmlcov/)
   ```

## Tips

- The suite ships with a Redis stub (`tests/conftest.py`), so you never need a live Redis server for local runs.
- Tests assume no network access. If you must touch external services, stub the call or drop mock payloads into `tests/data/`.
- Mirror source layout when creating new tests—if you add `wepppy/foo/bar.py`, expect to create `tests/foo/test_bar.py`.
- Reach for the shared factories under `tests/factories/` instead of hand-rolling Redis/Queue stubs. `rq_environment` (auto-installed via `tests/conftest.py`) gives you a recorder-backed `RedisPrep` + `Queue` pair, while `singleton_factory` helps build NoDb-style controllers with locking/parse stubs.
- Disturbed blueprint coverage (`tests/weppcloud/routes/test_disturbed_bp.py`) demonstrates pairing `singleton_factory` with `rq_environment` to stub NoDb controllers cleanly while exercising `parse_request_payload` paths—use it as the playbook for similar route tests.
- Batch runner coverage lives in `tests/weppcloud/test_batch_runner_endpoints.py` (blueprint flows) and `tests/weppcloud/routes/test_rq_api_batch_runner.py` (queue wiring). Both rely on the shared factories—follow the pattern when expanding coverage.
- Example usage: `tests/weppcloud/routes/test_rq_api_debris_flow.py` demonstrates patching `_redis_conn`, `Queue`, and `RedisPrep` via `RQRecorder` + `singleton_factory` while driving the view function through `app.test_request_context`.
- Frontend helpers/controllers have their own tooling—run `wctl run-npm lint` and `wctl run-npm test` (or `wctl run-npm check`) before shipping JS changes.
- Finish by verifying stubs: `wctl check-test-stubs` ensures `sys.modules` shims match their real module APIs.
- Add or update pytest markers when you touch a test. Every test should declare a category (e.g., `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.routes`) and mark long-running cases with `@pytest.mark.slow`.
- Check [`tests/AGENTS.md`](AGENTS.md) for guidance on fixtures, NoDb serialization patterns, and expectations when adding new suites.

Happy testing! Keep the muscles fresh by running `wctl run-pytest tests --maxfail=1` early and often.
