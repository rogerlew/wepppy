# WEPPpy Test Suite

> Comprehensive testing infrastructure for wepppy using pytest, covering unit tests, integration tests, and NoDb serialization scenarios.

> **See also:** [AGENTS.md](../AGENTS.md) for Testing and Validation section and Quality Checklist.

## Overview

The wepppy test suite validates the erosion modeling stack across multiple dimensions:
- **Unit tests**: Individual function and class behavior
- **Integration tests**: NoDb controller interactions, Redis operations, WEPP model execution
- **Serialization tests**: JSONPickle round-trips for legacy compatibility
- **Module tests**: Climate data fetching, soils processing, watershed abstraction

The test suite is organized to match the source tree structure, with subdirectories mirroring `wepppy/` packages (nodb, climates, wepp, etc.).

## Quick Start

### Running Tests

**All tests**:
```bash
pytest tests/
```

**Specific module**:
```bash
pytest tests/nodb/
pytest tests/test_all_your_base.py
```

**With coverage**:
```bash
pytest --cov=wepppy --cov-report=html tests/
```

**Inside Docker container** (recommended for integration tests):
```bash
# Using wctl wrapper
wctl run-pytest

# Or manually
docker compose --env-file docker/.env -f docker/docker-compose.dev.yml exec weppcloud pytest tests/
```

**Verbose output**:
```bash
pytest -v tests/
```

**Stop on first failure**:
```bash
pytest -x tests/
```

## Test Organization

```
tests/
├── README.md                          # This file
├── conftest.py                        # pytest fixtures and Redis stub
├── test_0_imports.py                  # Smoke test ensuring core imports work
├── test_imports.py                    # Additional import validation
├── test_all_your_base.py              # Utility function tests
├── test_all_your_base_*.py            # Domain-specific utility tests
├── test_managements_module.py         # WEPP management file parsing
├── test_redis_settings.py             # Redis configuration
├── test_wepp_top_translator.py        # WEPP topology translation
├── nodb/                              # NoDb controller tests
│   ├── test_*.py                      # Per-controller test modules
│   └── integration/                   # Cross-controller scenarios
├── climates/                          # Climate data integration tests
├── wepp/                              # WEPP model tests
├── microservices/                     # Microservice API tests
├── query_engine/                      # Query engine tests
└── data/                              # Test fixtures and sample data
```

### Test Naming Convention

- **Files**: `test_<module_name>.py`
- **Functions**: `test_<behavior_description>`
- **Classes**: `Test<ComponentName>` (optional, for grouping)

Examples:
- `test_landuse_singleton_behavior()`
- `test_wepp_executor_parses_output()`
- `test_climate_cligen_station_selection()`

## Writing Tests

### Basic Test Pattern

```python
import pytest
from wepppy.module import function_under_test

def test_function_behavior():
    """Test that function_under_test handles valid input correctly."""
    result = function_under_test(input_value)
    assert result == expected_value
```

### Using Fixtures

**Temporary directory** (from pytest):
```python
def test_file_creation(tmp_path):
    """tmp_path is a Path object to a temporary directory."""
    file = tmp_path / "test.txt"
    file.write_text("content")
    assert file.read_text() == "content"
```

**Redis stub** (from conftest.py):
The test suite includes a Redis stub that intercepts Redis imports, allowing tests to run without a live Redis instance. NoDb controllers will use the stub automatically.

### Testing NoDb Controllers

**Round-trip serialization**:
```python
from wepppy.nodb.core import Landuse

def test_landuse_persistence(tmp_path):
    wd = str(tmp_path)
    cfg_fn = "project.cfg"
    
    # Create instance
    landuse = Landuse(wd, cfg_fn)
    with landuse.locked():
        landuse.mode = LanduseMode.Gridded
        landuse.dump_and_unlock()
    
    # Reload and verify
    landuse2 = Landuse.getInstance(wd)
    assert landuse2.mode == LanduseMode.Gridded
    assert landuse is landuse2  # Singleton behavior
```

**Locking behavior**:
```python
def test_nodb_lock_prevents_concurrent_writes(tmp_path):
    controller = SomeController.getInstance(str(tmp_path))
    
    with controller.locked():
        # Mutations inside lock
        controller.data = "value"
    
    # Lock automatically released
    assert not controller.islocked()
```

### Testing with Mock Data

Place test fixtures in `tests/data/`:
```python
import json
from pathlib import Path

def test_parses_climate_data():
    fixture = Path(__file__).parent / "data" / "climate_sample.json"
    data = json.loads(fixture.read_text())
    result = parse_climate(data)
    assert result["station"] == "EXAMPLE"
```

### Parameterized Tests

```python
@pytest.mark.parametrize("input,expected", [
    (0, 0),
    (5, 25),
    (-3, 9),
])
def test_square_function(input, expected):
    assert square(input) == expected
```

### Testing Exceptions

```python
def test_function_raises_on_invalid_input():
    with pytest.raises(ValueError, match="invalid"):
        function_with_validation("bad_input")
```

### Skipping Tests

```python
@pytest.mark.skip(reason="Feature not implemented")
def test_future_functionality():
    pass

@pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
def test_unix_paths():
    pass
```

## Test Categories

### Unit Tests

Test individual functions and classes in isolation.

**Characteristics**:
- Fast (< 1 second each)
- No external dependencies (files, network, Redis)
- Focused on single behavior

**Example**: `test_all_your_base.py` validates utility functions like `clamp`, `flatten`, `parse_units`

### Integration Tests

Test interactions between components.

**Characteristics**:
- May create temporary files/directories
- May use Redis stub or real Redis instance
- Test end-to-end workflows

**Example**: NoDb controller tests that verify serialization, locking, and cross-references

### Module Tests

Test specific subsystems (climates, soils, WEPP executables).

**Characteristics**:
- May require external data sources
- May invoke subprocess commands (WEPP, TOPAZ)
- May be slow (> 5 seconds)

**Example**: `tests/climates/` validates climate data fetching and interpolation

## Coverage Expectations

Aim for these coverage targets:

- **Core modules** (nodb, all_your_base): > 80%
- **Controllers**: > 70%
- **Utilities**: > 75%
- **Routes/blueprints**: > 60%
- **Microservices**: > 70%

Check coverage reports:
```bash
pytest --cov=wepppy --cov-report=html tests/
open htmlcov/index.html
```

## Continuous Integration

Tests run automatically on:
- **Push to main/develop**: Full test suite
- **Pull requests**: Full test suite + coverage report
- **Nightly**: Extended integration tests with real data sources

CI configuration lives in `.github/workflows/`.

## Common Patterns

### Testing WEPP Model Execution

```python
def test_wepp_run_produces_output(tmp_path):
    wd = setup_test_watershed(tmp_path)
    wepp = Wepp.getInstance(wd)
    
    wepp.run_wepp_watershed()
    
    output_file = Path(wd) / "wepp" / "runs" / "H1.out"
    assert output_file.exists()
    assert "HILLSLOPE" in output_file.read_text()
```

### Testing Climate Data Fetching

```python
@pytest.mark.integration
def test_cligen_station_fetch():
    """Integration test requiring network access."""
    client = CligenClient()
    station = client.get_station(lat=46.7, lon=-117.0)
    assert station.name
    assert station.elevation > 0
```

### Testing Redis Operations

```python
def test_redis_prep_timestamps(tmp_path):
    """Uses Redis stub from conftest.py."""
    prep = RedisPrep.getInstance(str(tmp_path))
    prep.timestamp(TaskEnum.build_landuse)
    
    timestamps = prep.get_timestamps()
    assert TaskEnum.build_landuse in timestamps
```

## Troubleshooting

### Import Errors

If tests fail with import errors:
1. Ensure you're in the repository root
2. Check that `PYTHONPATH` includes the repo root
3. In Docker, verify bind mounts are correct

### Redis Connection Errors

The test suite includes a Redis stub that intercepts imports. If you need a real Redis instance:
```python
import pytest

@pytest.mark.requires_redis
def test_with_real_redis():
    # Test code that needs actual Redis
    pass
```

Then run with:
```bash
pytest -m requires_redis tests/
```

### Slow Tests

Mark slow tests so they can be excluded:
```python
@pytest.mark.slow
def test_full_watershed_run():
    # Long-running test
    pass
```

Run fast tests only:
```bash
pytest -m "not slow" tests/
```

### Fixture Cleanup

Pytest automatically cleans up `tmp_path` fixtures. For custom cleanup:
```python
@pytest.fixture
def custom_resource():
    resource = setup_resource()
    yield resource
    teardown_resource(resource)
```

## Test Data Management

### Fixtures

Place reusable test data in `tests/data/`:
- Climate samples: `climate_sample.json`
- Soil profiles: `soil_example.sol`
- Management files: `management_example.man`

### Generating Test Data

Some tests require large datasets (DEMs, landcover rasters). Store these externally and document download instructions:

```python
@pytest.mark.requires_geodata
def test_with_dem():
    # Expects DEM at tests/data/dem.tif
    pass
```

## Developer Notes

### Adding New Tests

1. **Choose location**: Match source tree structure
2. **Follow naming**: `test_<module>_<behavior>.py`
3. **Write docstrings**: Explain what behavior is tested
4. **Use fixtures**: Leverage pytest fixtures for setup
5. **Keep tests focused**: One behavior per test function
6. **Add markers**: Use `@pytest.mark.*` for categorization

### Debugging Tests

**Run with output**:
```bash
pytest -s tests/test_module.py
```

**Run specific test**:
```bash
pytest tests/test_module.py::test_function_name
```

**Drop into debugger on failure**:
```bash
pytest --pdb tests/
```

**Show locals on failure**:
```bash
pytest -l tests/
```

### Test Maintenance

- **Review quarterly**: Remove obsolete tests, update fixtures
- **Refactor duplicates**: Extract common patterns to conftest.py
- **Update coverage**: Add tests for new features
- **Fix flaky tests**: Eliminate race conditions and timing dependencies

## Further Reading

- **pytest documentation**: https://docs.pytest.org/
- **AGENTS.md**: Testing patterns and quality standards
- **conftest.py**: Fixture definitions and Redis stub implementation
- **CI workflows**: `.github/workflows/` for automation configuration

---

**Maintained by**: AI Coding Agents (per AGENTS.md authorship policy)
