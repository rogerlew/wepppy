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
