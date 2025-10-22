# tests/AGENTS.md
> Agent playbook for maintaining and extending the WEPPpy test suite.

## Authorship
**This document is owned by the AI agents maintaining the repository. Update it whenever you extend the test harness, add new suites, or change execution requirements.**

## Purpose
Human contributors rely on `tests/README.md` for the quick-start view. This file captures the deeper guidance agents need to keep the suite healthy: structure, fixtures, patterns, and expectations when authoring new tests.

## Test Taxonomy

| Area | Location | Focus |
|------|----------|-------|
| Smoke/import checks | `tests/test_0_imports.py`, `tests/test_imports.py` | Early detection of missing optional dependencies or circular imports |
| Utility modules | `tests/test_all_your_base*.py` | Core helpers used across controllers, raster IO, geometry utilities |
| NoDb controllers | `tests/nodb/` | Singleton behaviour, locking semantics, serialization |
| Climate/soils/wepp | `tests/climates/`, `tests/wepp/`, `tests/soils/` | Integration against data pipelines and WEPP executables |
| Microservices | `tests/microservices/` | Starlette/FastAPI endpoints, payload validation |
| Query engine | `tests/query_engine/` | DuckDB-backed analytics, MCP endpoints |

## Execution Strategy

- **Always run through the Docker wrapper.** `wctl run-pytest …` guarantees Redis stubs, optional dependencies, and env variables match production images.
- **Target first, then full sweep.**
  - Example focused run: `wctl run-pytest tests/weppcloud/routes/test_climate_bp.py`
  - Mandatory pre-handoff sweep: `wctl run-pytest tests --maxfail=1`
- **CI vs local parity.** Add new fixtures or stubs so tests pass with no network access and without real Redis/WEPP executables. If a test needs large artifacts, drop them under `tests/data/` and reference them relative to `Path(__file__).parent`.
- **Frontend harness.** When controller changes require Jest or other npm scripts, invoke them via `wctl run-npm <script>` so the `npm --prefix wepppy/weppcloud/static-src` prefix is handled consistently (for example, `wctl run-npm test`).

## Fixtures & Stubs

- `tests/conftest.py` installs a lightweight Redis stub that satisfies `redis`, `redis.exceptions`, and `redis.client.Pipeline` imports. Extend it rather than importing the real Redis client.
- Prefer `tmp_path`/`tmp_path_factory` for on-disk work. For NoDb controllers, pass `str(tmp_path)` to `getInstance`.
- Need a clean environment variable? Use `monkeypatch.setenv` and `monkeypatch.delenv` inside tests.
- Reuse the shared factories in `tests/factories/` whenever you need RedisPrep/Queue/NoDb stubs. `rq_environment` (imported in `tests/conftest.py`) provides recorder-backed helpers so blueprints can assert on queued jobs without copy/pasting mocks.

### Module Stub Management

**Critical**: When creating stubs for `wepppy` modules via `sys.modules` to isolate tests from heavy dependencies, follow these rules:

1. **Prefer shared fixtures over per-test stubs.** If multiple tests need the same stub, create a session-scoped fixture in `conftest.py` rather than duplicating stub logic.

2. **Match the full public API.** When stubbing a module, inspect its `__all__` export list and implement **every** public function/class that other code might import:
   ```python
   # Check the real module's exports first
   from wepppy.all_your_base import __all__
   print(__all__)  # ['isint', 'isfloat', 'isnan', ...]
   
   # Then ensure your stub covers all of them
   stub.isint = lambda x: ...
   stub.isfloat = lambda x: ...
   stub.isnan = lambda x: ...
   ```

3. **Document stub coverage.** Add a comment listing which functions the stub implements and why certain ones are omitted (if any).

4. **Centralize common stubs.** If `wepppy.all_your_base` stubs appear in multiple test files, extract them to `conftest.py` or a dedicated `tests/stubs.py` module that all tests can import.

5. **Avoid `sys.modules` pollution during collection.** If test modules execute stub creation at module level (outside fixtures), those stubs persist across the entire pytest session. This caused the `isint` import error when:
   - `test_wepp_soil_util.py` created an incomplete stub at import time
   - `test_disturbed_bp.py` later tried to import routes that need `isint`
   - The stub was still in `sys.modules` but missing `isint`

6. **Prefer fixture-scoped stubs when possible:**
   ```python
   @pytest.fixture(autouse=True)
   def stub_all_your_base():
       original = sys.modules.get('wepppy.all_your_base')
       stub = types.ModuleType('wepppy.all_your_base')
       stub.isint = lambda x: ...
       stub.isfloat = lambda x: ...
       sys.modules['wepppy.all_your_base'] = stub
       yield
       if original:
           sys.modules['wepppy.all_your_base'] = original
       else:
           sys.modules.pop('wepppy.all_your_base', None)
   ```

7. **Test stub completeness.** When adding imports to production code from stubbed modules, grep for existing stubs and update them simultaneously:
   ```bash
   # Added 'from wepppy.all_your_base import isint' somewhere?
   git grep "sys.modules\[\"wepppy.all_your_base\"\]"
   # Then update ALL stub sites with the new function
   ```

8. **Run the automated checker.** Execute `wctl check-test-stubs` (or `python tools/check_stubs.py`) before committing to ensure every stub matches the module's `__all__`.

**Recent example:** The `isint` import error occurred because:
- `/workdir/wepppy/wepppy/weppcloud/controllers_js/unitizer_map_builder.py` created a stub with only `isfloat` and `isnan`
- `/workdir/wepppy/tests/wepp/soils/utils/test_wepp_soil_util.py` created a stub with only `try_parse`, `try_parse_float`, and `isfloat`
- Both were missing `isint`, which `/workdir/wepppy/wepppy/weppcloud/routes/rq/api/api.py` imports

**Fix:** Added `isint` to both stubs to match the real module's `__all__` list.

### Test Marker Guidelines

- Treat markers as mandatory metadata. Every test should declare a category marker such as `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.routes`, or `@pytest.mark.microservice`. Pick the one that best matches the subsystem exercised.
- Add `@pytest.mark.slow` for tests that consistently exceed ~2 seconds. Combine with the category marker (`@pytest.mark.integration + @pytest.mark.slow`) as needed.
- Use environment markers (`@pytest.mark.requires_network`, `@pytest.mark.requires_docker`, etc.) when the test depends on optional services. Guard the body with `pytest.importorskip` or fixture checks so it skips cleanly if the requirement is missing.
- Place decorators directly above the test function or class. When an entire module shares the same requirement, set `pytestmark = pytest.mark.<marker>` at the top of the file.
- Avoid conflicting combinations (e.g., `unit` plus `slow`). Either refactor the test to be fast or promote it to an integration-style test.
- When editing legacy tests that lack markers, backfill them as part of the change. We want full coverage across the suite.
- Until the planned `wctl check-test-markers` helper lands, reviewers should manually verify marker usage. Running targeted selections like `pytest -m "not slow"` should still leave a healthy subset of tests.

## NoDb Test Patterns

```python
from wepppy.nodb.core.landuse import Landuse, LanduseMode

def test_landuse_serialization(tmp_path):
    wd = str(tmp_path)
    landuse = Landuse(wd, "project.cfg")

    with landuse.locked():
        landuse.mode = LanduseMode.Gridded
        landuse.dump_and_unlock()

    clone = Landuse.getInstance(wd)
    assert clone is landuse
    assert clone.mode == LanduseMode.Gridded
```

- Always wrap state mutations with `with controller.locked():`.
- Call `dump_and_unlock()` before assertions that require persisted state.
- When testing error handling, patch `controller._logger` to confirm telemetry if relevant.

## Flask Route Tests

- Use `pytest.importorskip("flask")` near the module import to skip neatly when Flask is unavailable.
- Patch `load_run_context`, `get_wd`, and controller singletons to keep tests hermetic.
- Prefer Flask’s test client from a locally constructed app to avoid pulling in the full WEPPcloud factory.

Example from `tests/weppcloud/routes/test_climate_bp.py`:
```python
app = Flask(__name__)
app.config["TESTING"] = True
app.register_blueprint(climate_module.climate_bp)
```

- When routes enqueue Redis jobs, use monkeypatch to replace queue objects with sentinel collectors.

## Microservice & Query Engine Tests

- Import guards (`pytest.importorskip("starlette")`, etc.) keep optional dependencies from breaking the run.
- Stub network calls with `responses` or `httpx.MockTransport`. Never hit real upstream APIs.

## Adding New Tests

1. Mirror the package path: e.g., new module `wepppy/weppcloud/routes/foo.py` → `tests/weppcloud/routes/test_foo.py`.
2. Put fixtures under `tests/data/<area>/` to avoid collisions.
3. Update `tests/__init__.py` or `tests/README.md` only if new top-level directories are added.
4. Document the new suite in this file under “Test Taxonomy”.
5. Run:
   ```bash
   wctl run-pytest tests/<path>/...
   wctl run-pytest tests --maxfail=1
   ```

## Quality Expectations

- Deterministic tests only—no reliance on system locale, timezone, or network.
- Keep runtimes fast: integration tests should wrap heavy processes in fixtures that cache generated artifacts.
- Record common gotchas and required fixtures here for future agents.

---

Keep this document aligned with the suite. When you add new categories or fixtures, update the appropriate sections so the next agent knows the ground truth.
