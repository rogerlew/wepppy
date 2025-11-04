# Test Tooling Specification

> Specification for additional test infrastructure tooling to improve test reliability, performance, and developer experience.  
> **Status:** Proposed (October 2025)  
> **Context:** Following resolution of `test_disturbed_bp.py` import failure caused by incomplete `sys.modules` stubs.

## Motivation

The wepppy test suite (259 tests as of October 2025) exhibits several maintainability challenges:

1. **Test isolation issues** - Module-level stub creation pollutes `sys.modules` across the entire pytest session, causing order-dependent failures
2. **Singleton pollution** - NoDb controllers maintain class-level `_instances` dictionaries that aren't consistently cleared between tests
3. **Performance opacity** - No systematic way to identify slow tests or track performance regressions
4. **Coverage gaps** - Ad-hoc coverage workflows make it difficult to maintain test coverage standards
5. **Marker compliance** - No enforcement of test categorization (`@pytest.mark.slow`, `@pytest.mark.integration`, etc.)

This document specifies four high-priority tools to address these issues.

---


## 1. Test Isolation Checker (`wctl check-test-isolation`)

### Purpose
Expose order-dependent failures and lingering global state. The checker should flag issues like the October 2025 `sys.modules` stub pollution before unrelated tests start failing.

### Scope
- Persistent `sys.modules` entries created during tests
- Singleton caches (`_instances`, `_cache`, `_singleton`, `_registry`, etc.) left populated
- Environment variable drift
- Files or directories created outside pytest-managed temporaries
- Stray background threads/processes (best-effort detection)
- Inconsistent outcomes when run order changes

### CLI Usage

```bash
# Balanced defaults across the suite
wctl check-test-isolation

# Narrow scope
wctl check-test-isolation tests/weppcloud/routes/
wctl check-test-isolation tests/wepp/soils/utils/test_wepp_soil_util.py::test_modify_kslast

# Fast pre-commit run
wctl check-test-isolation --quick

# Thorough sweep with logs
wctl check-test-isolation --strict --verbose --log-dir reports/isolation

# JSON output for CI dashboards
wctl check-test-isolation --json > isolation-report.json

# Report-only mode (never exits non-zero)
wctl check-test-isolation --allow-failures
```

#### Flags & Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `PATH...` | `tests` | Pytest targets (dirs/files/node ids). |
| `--iterations N` | `5` (`2` in quick, `10` in strict) | Number of random-order runs. |
| `--shuffle-scope {module,node}` | `module` | Randomize module order only or individual tests. |
| `--random-plugin {pytest-randomly,pytest-random-order}` | auto | Select randomization plugin; warn if unavailable. |
| `--quick` | – | Shortcut: `--iterations 2 --shuffle-scope module --skip-state-scan`. |
| `--strict` | – | Shortcut: `--iterations 10 --shuffle-scope node --enable-state-scan --enable-fs-scan`. |
| `--enable-state-scan / --skip-state-scan` | enabled | Toggle global state diffing. |
| `--enable-fs-scan` | disabled | Enable filesystem diffing outside temp dirs. |
| `--baseline FILE` | none | Ignore issues already recorded in baseline JSON. |
| `--json` | off | Emit JSON summary. |
| `--log-dir DIR` | none | Persist per-run stdout/stderr and diff artifacts. |
| `--allow-failures` | off | Always exit 0 (useful for nightly reports). |
| `--max-workers N` | CPU count | Concurrency for per-file runs. |
| `--keep-temp` | off | Do not delete temp dirs (debugging). |
| `--pytest-args "..."` | none | Extra pytest arguments appended to every invocation. |

Exit codes: `0` (clean), `1` (issues detected), `2` (tool error).

### Implementation Plan (`tools/check_test_isolation.py`)

1. **Argument parsing & plugin detection** – resolve targets, confirm randomization plugin availability, warn/fallback when missing.
2. **State tracker** – capture/diff `sys.modules`, environment variables, singleton caches (discover via reflection), and optionally filesystem state (configurable ignore lists in `tools/check_test_isolation.toml`). Provide context manager to restore state where possible.
3. **Phase A – random-order fuzzing** – run pytest `iterations` times with deterministic seeds (default `[42, 123, 999, 1337, 8675309]`) and `--json-report` enabled. Divergent failure sets signal order dependence.
4. **Phase B – per-file isolation** – collect test files via `pytest --collect-only`; run each file individually (parallel when `--max-workers>1`) and compare failure signatures against suite run.
5. **Phase C – pollution diff** – unless `--skip-state-scan`, diff captured state after each run to highlight new modules, singleton entries, environment changes, and filesystem mutations. Provide actionable suggestions (e.g., “move stub into fixture”).
6. **Baseline handling** – optional `--baseline` JSON suppresses known issues. Future `--update-baseline` can append new findings after manual review.

   Baseline files follow a lightweight schema:
   ```json
   {
     "suppressions": [
       "order-failure|seed=999",
       "file-isolation|tests/weppcloud/routes/test_disturbed_bp.py",
       "pollution|module|tests/weppcloud/routes/test_disturbed_bp.py|wepppy.all_your_base"
     ]
   }
   ```
   Each entry is a pipe-delimited key (`type|context|…`) that matches the identifiers emitted by the checker. Keeping the structure flat makes it easy to hand-edit and share across branches.

   Filesystem scanning honours `tools/check_test_isolation.toml` when present. Add `ignore_patterns = ["path/glob/*"]` under the `[filesystem]` table to exclude generated artifacts or known-good outputs from pollution reports.
7. **Reporting** – produce terminal summary, optional JSON (`--json`), and artifact bundle in `--log-dir`. Include per-seed results, divergent files, and pollution details.
8. **wctl integration** – add command branch:
   ```bash
   check-test-isolation)
     shift
     compose_exec_weppcloud "cd /workdir/wepppy && python tools/check_test_isolation.py $*"
     exit 0
     ;;
   ```
   Document in `wctl/README.md` during implementation.
9. **Performance targets** – default run ≈2 minutes on dev hardware; `--quick` <1 minute (pre-commit), `--strict` reserved for nightly CI (~5+ minutes).
10. **Future enhancements** – integrate with the planned marker checker (skip certain categories by default), allow custom ignore lists, optional `psutil` integration for orphaned subprocess detection.


### Output Format

```
🔍 Test Isolation Check
=====================================================================

Running 5 iterations with random ordering...
  ✓ Seed 42: All tests passed
  ✓ Seed 123: All tests passed
  ✗ Seed 999: 1 test failed
  ✓ Seed 1337: All tests passed
  ✓ Seed 8675309: All tests passed

⚠️  Order-dependent failures detected!

Checking file isolation...
  ✓ tests/test_0_imports.py - Isolated OK
  ✓ tests/test_all_your_base.py - Isolated OK
  ✗ tests/wepp/soils/utils/test_wepp_soil_util.py - ISOLATION ISSUE

Pollution Report:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tests/wepp/soils/utils/test_wepp_soil_util.py:
  • sys.modules pollution:
    - wepppy.all_your_base (stub, missing: isint, isnan, isinf)
  • Behavior difference:
    - Passes in isolation
    - Fails in full suite when run after test_unitizer_map_builder.py

Recommendation:
  Move stub creation to a session-scoped fixture in conftest.py
  or use autouse fixture with proper cleanup.

Failed tests by seed:
  Seed 999:
    - tests/weppcloud/routes/test_disturbed_bp.py::test_has_sbs_endpoint

Total issues: 1 file with isolation problems
```

### Integration

Add to `wctl/wctl.sh`:

```bash
check-test-isolation)
  shift
  QUICK_FLAG=""
  VERBOSE_FLAG=""
  TEST_PATH="tests"
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --quick) QUICK_FLAG="--quick"; shift ;;
      --verbose|-v) VERBOSE_FLAG="--verbose"; shift ;;
      *) TEST_PATH="$1"; shift ;;
    esac
  done
  
  compose_exec_weppcloud "cd /workdir/wepppy && python tools/check_test_isolation.py ${QUICK_FLAG} ${VERBOSE_FLAG} ${TEST_PATH}"
  exit 0
  ;;
```

### Success Criteria
- Detects the October 2025 `sys.modules` stub issue when run against the broken test suite
- Identifies order-dependent failures within 5 random-order iterations
- Reports specific pollution types (modules, env vars, singletons)
- Runs in <2 minutes for full suite on development hardware
- Zero false positives on current passing tests

---

## 2. Coverage Report Helper (`wctl test-coverage`)

### Purpose
Streamline coverage workflow and enforce coverage standards. Currently coverage is ad-hoc; this standardizes the process.

### Scope
- Generate coverage reports (terminal, HTML, JSON)
- Enforce minimum coverage thresholds
- Compare coverage between branches
- Identify untested code paths in specific modules
- Exclude generated/vendored code from coverage metrics

### Usage

```bash
# Generate coverage report for full suite
wctl test-coverage

# Coverage for specific area
wctl test-coverage tests/nodb/

# Generate HTML report
wctl test-coverage --html
# Opens: htmlcov/index.html

# Fail if coverage below threshold
wctl test-coverage --check --min=80

# JSON output for CI integration
wctl test-coverage --json > coverage.json

# Coverage diff vs master branch
wctl test-coverage --diff=master

# Focus on specific module
wctl test-coverage --module=wepppy.nodb.core
```

### Implementation Strategy

#### Phase 1: Basic Coverage Runner
Wrap pytest-cov with standardized configuration:

```python
import subprocess
import json
from pathlib import Path
from typing import Optional

def run_coverage(
    test_path: str = "tests",
    html: bool = False,
    min_coverage: Optional[float] = None,
    json_output: bool = False,
    module_filter: Optional[str] = None
) -> int:
    """Run pytest with coverage."""
    
    cmd = [
        "pytest",
        test_path,
        "--cov=wepppy",
        "--cov-report=term-missing",
    ]
    
    if html:
        cmd.append("--cov-report=html")
    
    if json_output:
        cmd.append("--cov-report=json")
    
    if min_coverage:
        cmd.append(f"--cov-fail-under={min_coverage}")
    
    if module_filter:
        cmd.append(f"--cov={module_filter}")
    
    result = subprocess.run(cmd, cwd="/workdir/wepppy")
    return result.returncode
```

#### Phase 2: Coverage Configuration
Create `.coveragerc` for consistent excludes:

```ini
[run]
source = wepppy
omit = 
    */tests/*
    */migrations/*
    */__pycache__/*
    */static/*
    */vendor/*
    */deps/*
    */.venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
    @abc.abstractmethod
    
precision = 2
show_missing = True

[html]
directory = htmlcov
```

#### Phase 3: Coverage Diff Tool
Compare coverage between branches:

```python
def coverage_diff(base_branch: str = "master") -> dict:
    """Compare coverage against another branch."""
    
    # Get coverage for current branch
    subprocess.run([
        "pytest", "tests",
        "--cov=wepppy",
        "--cov-report=json:coverage-current.json"
    ])
    
    # Stash changes and checkout base
    subprocess.run(["git", "stash"])
    subprocess.run(["git", "checkout", base_branch])
    
    # Get coverage for base branch
    subprocess.run([
        "pytest", "tests",
        "--cov=wepppy",
        "--cov-report=json:coverage-base.json"
    ])
    
    # Return to original branch
    subprocess.run(["git", "checkout", "-"])
    subprocess.run(["git", "stash", "pop"])
    
    # Load both reports
    with open("coverage-current.json") as f:
        current = json.load(f)
    with open("coverage-base.json") as f:
        base = json.load(f)
    
    # Calculate diff
    current_pct = current["totals"]["percent_covered"]
    base_pct = base["totals"]["percent_covered"]
    diff_pct = current_pct - base_pct
    
    return {
        "current": current_pct,
        "base": base_pct,
        "diff": diff_pct,
        "improved": diff_pct > 0
    }
```

### Output Format

#### Terminal Report
```
🔬 Test Coverage Report
=====================================================================

Running coverage analysis...

Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
wepppy/__init__.py                          8      0   100%
wepppy/all_your_base/__init__.py           15      2    87%   45-47
wepppy/all_your_base/all_your_base.py     156     12    92%   89, 134-142
wepppy/nodb/base.py                       423     28    93%   156, 234-241, 389-394
wepppy/nodb/core/climate.py               567     45    92%   
wepppy/nodb/core/landuse.py               389     23    94%
wepppy/nodb/core/soils.py                 445     38    91%
wepppy/nodb/core/wepp.py                  678     56    92%
---------------------------------------------------------------------
TOTAL                                   12,456    876    93%

✓ Coverage: 93.0% (exceeds minimum of 80%)

Top 5 modules needing coverage:
  1. wepppy.climates.gridmet.client       67%  (234 untested lines)
  2. wepppy.wepp.management               71%  (189 untested lines)
  3. wepppy.soils.ssurgo.client           74%  (156 untested lines)
  4. wepppy.topo.peridot.runner           78%  (123 untested lines)
  5. wepppy.rq.wepp_rq                    82%  (98 untested lines)

HTML report: htmlcov/index.html
```

#### JSON Output
```json
{
  "totals": {
    "percent_covered": 93.02,
    "num_statements": 12456,
    "missing_lines": 876,
    "covered_lines": 11580
  },
  "files": {
    "wepppy/all_your_base/all_your_base.py": {
      "percent_covered": 92.31,
      "missing_lines": [89, 134, 135, 136, 137, 138, 139, 140, 141, 142],
      "num_statements": 156
    }
  },
  "timestamp": "2025-10-22T14:32:11Z"
}
```

#### Diff Report
```
🔬 Coverage Diff vs master
=====================================================================

Current branch:  feature/new-controller
Base branch:     master

Overall Coverage:
  Current: 93.0%
  Base:    91.5%
  Change:  +1.5% ✓

Module Changes:
  ✓ wepppy.nodb.core.climate   92% → 95%  (+3%)
  ✓ wepppy.rq.project_rq        88% → 91%  (+3%)
  ✗ wepppy.wepp.management      76% → 71%  (-5%)

New files (no baseline):
  • wepppy/nodb/mods/new_feature.py  87%

Summary: Coverage improved overall, but management module regression needs attention.
```

### Integration

Add to `wctl/wctl.sh`:

```bash
test-coverage)
  shift
  HTML_FLAG=""
  MIN_COV=""
  JSON_FLAG=""
  DIFF_BRANCH=""
  MODULE=""
  TEST_PATH="tests"
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --html) HTML_FLAG="--html"; shift ;;
      --check) shift ;;
      --min=*) MIN_COV="${1#--min=}"; shift ;;
      --json) JSON_FLAG="--json"; shift ;;
      --diff=*) DIFF_BRANCH="${1#--diff=}"; shift ;;
      --module=*) MODULE="${1#--module=}"; shift ;;
      *) TEST_PATH="$1"; shift ;;
    esac
  done
  
  CMD="cd /workdir/wepppy && python tools/run_coverage.py"
  [[ -n "$HTML_FLAG" ]] && CMD="$CMD --html"
  [[ -n "$MIN_COV" ]] && CMD="$CMD --min=$MIN_COV"
  [[ -n "$JSON_FLAG" ]] && CMD="$CMD --json"
  [[ -n "$DIFF_BRANCH" ]] && CMD="$CMD --diff=$DIFF_BRANCH"
  [[ -n "$MODULE" ]] && CMD="$CMD --module=$MODULE"
  CMD="$CMD $TEST_PATH"
  
  compose_exec_weppcloud "$CMD"
  exit 0
  ;;
```

### Success Criteria
- Generates reports in <30 seconds for full suite
- HTML reports viewable in browser with line-by-line coverage
- JSON output parseable by CI systems (GitHub Actions, GitLab CI)
- Diff mode accurately identifies coverage regressions
- Configurable thresholds per module (e.g., 95% for core, 80% for mods)

---

## 3. Test Performance Profiler (`wctl test-profile`)

### Purpose
Identify slow tests and track performance regressions. The 259-test suite should complete quickly; this tool finds bottlenecks.

### Scope
- Profile individual test execution time
- Identify slowest N tests
- Find tests exceeding time thresholds
- Track performance over time (regression detection)
- Generate performance reports for CI

### Usage

```bash
# Show slowest 10 tests
wctl test-profile --top=10

# Find tests taking >5 seconds
wctl test-profile --threshold=5

# Full performance breakdown
wctl test-profile --detailed

# Compare with baseline (previous run)
wctl test-profile --compare

# Save performance baseline
wctl test-profile --baseline

# CI-friendly JSON output
wctl test-profile --json

# Profile specific test directory
wctl test-profile tests/nodb/
```

### Implementation Strategy

#### Phase 1: Duration Tracking
Use pytest's built-in duration tracking:

```python
import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class TestTiming:
    """Test execution timing information."""
    nodeid: str
    duration: float
    outcome: str  # passed, failed, skipped
    
    @property
    def module(self) -> str:
        return self.nodeid.split("::")[0]
    
    @property
    def name(self) -> str:
        parts = self.nodeid.split("::")
        return parts[-1] if len(parts) > 1 else parts[0]

def profile_tests(
    test_path: str = "tests",
    top_n: int = 10,
    threshold: Optional[float] = None
) -> List[TestTiming]:
    """Profile test execution times."""
    
    # Run pytest with duration reporting
    result = subprocess.run(
        [
            "pytest",
            test_path,
            "--durations=0",  # Show all durations
            "-v",
            "--tb=no"
        ],
        capture_output=True,
        text=True,
        cwd="/workdir/wepppy"
    )
    
    # Parse durations from output
    timings = []
    duration_pattern = r"([\d.]+)s\s+(call|setup|teardown)\s+(.+)"
    
    for line in result.stdout.splitlines():
        match = re.match(duration_pattern, line)
        if match:
            duration = float(match.group(1))
            phase = match.group(2)
            nodeid = match.group(3)
            
            if phase == "call":  # Only track test execution, not setup/teardown
                timings.append(TestTiming(
                    nodeid=nodeid,
                    duration=duration,
                    outcome="passed"  # Would need to track outcomes separately
                ))
    
    # Sort by duration
    timings.sort(key=lambda t: t.duration, reverse=True)
    
    # Filter by threshold if specified
    if threshold:
        timings = [t for t in timings if t.duration >= threshold]
    
    # Limit to top N
    if top_n:
        timings = timings[:top_n]
    
    return timings
```

#### Phase 2: Performance Baseline
Track performance over time:

```python
class PerformanceBaseline:
    """Track test performance baselines."""
    
    def __init__(self, baseline_file: Path = Path(".test-baseline.json")):
        self.baseline_file = baseline_file
        self.baseline: Dict[str, float] = {}
        
        if baseline_file.exists():
            self.load()
    
    def load(self):
        """Load baseline from disk."""
        with open(self.baseline_file) as f:
            self.baseline = json.load(f)
    
    def save(self, timings: List[TestTiming]):
        """Save current timings as baseline."""
        self.baseline = {t.nodeid: t.duration for t in timings}
        with open(self.baseline_file, "w") as f:
            json.dump(self.baseline, f, indent=2)
    
    def compare(self, timings: List[TestTiming]) -> Dict[str, Dict]:
        """Compare current timings against baseline."""
        regressions = {}
        
        for timing in timings:
            baseline_duration = self.baseline.get(timing.nodeid)
            if baseline_duration is None:
                continue
            
            # Consider >20% slower a regression
            pct_change = ((timing.duration - baseline_duration) / baseline_duration) * 100
            
            if pct_change > 20:
                regressions[timing.nodeid] = {
                    "baseline": baseline_duration,
                    "current": timing.duration,
                    "change_pct": pct_change,
                    "slower_by": timing.duration - baseline_duration
                }
        
        return regressions
```

#### Phase 3: Category Analysis
Analyze performance by test category:

```python
def analyze_by_category(timings: List[TestTiming]) -> Dict[str, Dict]:
    """Group timings by test category."""
    categories = {}
    
    for timing in timings:
        # Determine category from path
        if "nodb" in timing.module:
            category = "NoDb Controllers"
        elif "routes" in timing.module:
            category = "Flask Routes"
        elif "microservices" in timing.module:
            category = "Microservices"
        elif "wepp" in timing.module:
            category = "WEPP Integration"
        elif "climates" in timing.module:
            category = "Climate Data"
        else:
            category = "Other"
        
        if category not in categories:
            categories[category] = {
                "tests": [],
                "total_duration": 0.0,
                "avg_duration": 0.0
            }
        
        categories[category]["tests"].append(timing)
        categories[category]["total_duration"] += timing.duration
    
    # Calculate averages
    for category, data in categories.items():
        data["avg_duration"] = data["total_duration"] / len(data["tests"])
        data["count"] = len(data["tests"])
    
    return categories
```

### Output Format

#### Terminal Report
```
⏱️  Test Performance Profile
=====================================================================

Slowest 10 Tests:
  1. tests/wepp/test_watershed_abstraction.py::test_peridot_run
     Duration: 12.45s
     
  2. tests/nodb/test_climate_build.py::test_gridmet_download
     Duration: 8.23s
     
  3. tests/microservices/test_elevation_query.py::test_large_watershed
     Duration: 6.78s
     
  4. tests/climates/test_daymet_client.py::test_fetch_tiles
     Duration: 5.92s
     
  5. tests/wepp/test_soil_interpolation.py::test_ssurgo_query
     Duration: 4.51s
     
  ... (5 more)

Performance by Category:
┌────────────────────────┬───────┬──────────┬─────────────┐
│ Category               │ Tests │ Total    │ Avg         │
├────────────────────────┼───────┼──────────┼─────────────┤
│ WEPP Integration       │  45   │ 123.4s   │ 2.74s/test  │
│ Flask Routes           │  89   │  67.2s   │ 0.76s/test  │
│ NoDb Controllers       │  67   │  45.8s   │ 0.68s/test  │
│ Microservices          │  23   │  34.1s   │ 1.48s/test  │
│ Climate Data           │  18   │  28.9s   │ 1.61s/test  │
│ Other                  │  17   │  12.3s   │ 0.72s/test  │
└────────────────────────┴───────┴──────────┴─────────────┘

Total suite time: 311.7s
Target: <300s
Status: ⚠️  Slightly over target

Recommendations:
  • Consider mocking WEPP executable calls in unit tests
  • Cache downloaded climate data in test fixtures
  • Use @pytest.mark.slow for tests >2s
```

#### Regression Report
```
⏱️  Performance Regression Check
=====================================================================

Baseline: .test-baseline.json (2025-10-15)

Regressions (>20% slower):
  ✗ tests/nodb/test_wepp.py::test_run_watershed
    Baseline: 2.1s  Current: 3.8s  (+81% slower, +1.7s)
    
  ✗ tests/routes/test_climate_bp.py::test_build_climate
    Baseline: 1.2s  Current: 1.8s  (+50% slower, +0.6s)

Improvements (>20% faster):
  ✓ tests/wepp/test_topaz.py::test_delineation
    Baseline: 8.3s  Current: 5.1s  (-39% faster, -3.2s)

New tests (no baseline):
  • tests/nodb/test_new_controller.py::test_serialize  (0.8s)

Overall: 2 regressions, 1 improvement
```

#### JSON Output
```json
{
  "timestamp": "2025-10-22T14:45:23Z",
  "total_duration": 311.7,
  "test_count": 259,
  "slowest_tests": [
    {
      "nodeid": "tests/wepp/test_watershed_abstraction.py::test_peridot_run",
      "duration": 12.45,
      "outcome": "passed"
    }
  ],
  "categories": {
    "WEPP Integration": {
      "count": 45,
      "total_duration": 123.4,
      "avg_duration": 2.74
    }
  },
  "regressions": {
    "tests/nodb/test_wepp.py::test_run_watershed": {
      "baseline": 2.1,
      "current": 3.8,
      "change_pct": 80.95,
      "slower_by": 1.7
    }
  }
}
```

### Integration

Add to `wctl/wctl.sh`:

```bash
test-profile)
  shift
  TOP_N="10"
  THRESHOLD=""
  DETAILED=""
  COMPARE=""
  BASELINE=""
  JSON_FLAG=""
  TEST_PATH="tests"
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --top=*) TOP_N="${1#--top=}"; shift ;;
      --threshold=*) THRESHOLD="--threshold=${1#--threshold=}"; shift ;;
      --detailed) DETAILED="--detailed"; shift ;;
      --compare) COMPARE="--compare"; shift ;;
      --baseline) BASELINE="--baseline"; shift ;;
      --json) JSON_FLAG="--json"; shift ;;
      *) TEST_PATH="$1"; shift ;;
    esac
  done
  
  CMD="cd /workdir/wepppy && python tools/profile_tests.py --top=$TOP_N"
  [[ -n "$THRESHOLD" ]] && CMD="$CMD $THRESHOLD"
  [[ -n "$DETAILED" ]] && CMD="$CMD $DETAILED"
  [[ -n "$COMPARE" ]] && CMD="$CMD $COMPARE"
  [[ -n "$BASELINE" ]] && CMD="$CMD $BASELINE"
  [[ -n "$JSON_FLAG" ]] && CMD="$CMD $JSON_FLAG"
  CMD="$CMD $TEST_PATH"
  
  compose_exec_weppcloud "$CMD"
  exit 0
  ;;
```

### Success Criteria
- Identifies top 10 slowest tests in <1 minute
- Baseline tracking detects >20% performance regressions
- Category breakdown helps identify systemic issues
- JSON output integrates with CI performance tracking
- Threshold filtering finds all tests exceeding specified duration

---

## 4. Test Marker Checker (`wctl check-test-markers`)

### Purpose
Enforce test categorization standards using pytest markers. Ensures slow/integration tests are properly marked for selective execution.

### Scope
- Verify all tests have appropriate markers
- Detect unmarked slow tests (duration >2s)
- Validate marker usage (no typos, required markers present)
- Enforce categorization rules (integration tests must mock network, etc.)
- Generate reports of unmarked/miscategorized tests

### Usage

```bash
# Check all tests for missing markers
wctl check-test-markers

# Find unmarked slow tests
wctl check-test-markers --find-slow

# Validate marker consistency
wctl check-test-markers --validate

# Auto-fix simple issues (add missing markers)
wctl check-test-markers --fix

# Check specific directory
wctl check-test-markers tests/nodb/

# Report only (no failures)
wctl check-test-markers --report-only
```

### Required Markers

Based on wepppy's test suite:

```python
# pytest.ini or pyproject.toml
[pytest]
markers =
    slow: Tests taking >2s (run with -m slow)
    integration: Integration tests requiring external services
    unit: Fast unit tests (<0.5s)
    network: Tests requiring network access (skipped in CI)
    requires_wepp: Tests requiring WEPP executables
    requires_data: Tests requiring large data files
    flask: Flask route tests
    nodb: NoDb controller tests
    microservice: Microservice endpoint tests
```

### Implementation Strategy

#### Phase 1: Marker Detection
Scan test files for marker usage:

```python
import ast
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass

@dataclass
class TestInfo:
    """Test function information."""
    file: Path
    name: str
    lineno: int
    markers: Set[str]
    
    @property
    def nodeid(self) -> str:
        return f"{self.file}::{self.name}"

def extract_test_markers(test_file: Path) -> List[TestInfo]:
    """Extract marker information from test file."""
    tests = []
    
    try:
        tree = ast.parse(test_file.read_text())
    except SyntaxError:
        return tests
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("test_"):
                markers = set()
                
                # Check decorators for pytest.mark.*
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        if (isinstance(decorator.value, ast.Attribute) and
                            decorator.value.attr == "mark"):
                            markers.add(decorator.attr)
                    elif isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if (isinstance(decorator.func.value, ast.Attribute) and
                                decorator.func.value.attr == "mark"):
                                markers.add(decorator.func.attr)
                
                tests.append(TestInfo(
                    file=test_file,
                    name=node.name,
                    lineno=node.lineno,
                    markers=markers
                ))
    
    return tests
```

#### Phase 2: Slow Test Detection
Find tests that should be marked slow:

```python
def find_unmarked_slow_tests(
    timings: List[TestTiming],
    test_infos: List[TestInfo],
    threshold: float = 2.0
) -> List[TestInfo]:
    """Find tests >threshold seconds without @pytest.mark.slow."""
    
    # Build lookup dict
    test_map = {ti.nodeid: ti for ti in test_infos}
    
    unmarked_slow = []
    for timing in timings:
        if timing.duration >= threshold:
            test_info = test_map.get(timing.nodeid)
            if test_info and "slow" not in test_info.markers:
                unmarked_slow.append(test_info)
    
    return unmarked_slow
```

#### Phase 3: Marker Validation
Check for typos and required markers:

```python
VALID_MARKERS = {
    "slow", "integration", "unit", "network",
    "requires_wepp", "requires_data", "flask",
    "nodb", "microservice"
}

def validate_markers(test_infos: List[TestInfo]) -> Dict[str, List[TestInfo]]:
    """Validate marker usage."""
    issues = {
        "invalid_markers": [],
        "missing_category": [],
        "conflicts": []
    }
    
    for test_info in test_infos:
        # Check for invalid markers
        invalid = test_info.markers - VALID_MARKERS
        if invalid:
            issues["invalid_markers"].append((test_info, invalid))
        
        # Check for category markers (at least one of unit/integration/slow)
        category_markers = {"unit", "integration", "slow"}
        if not (test_info.markers & category_markers):
            issues["missing_category"].append(test_info)
        
        # Check for conflicting markers
        if "unit" in test_info.markers and "slow" in test_info.markers:
            issues["conflicts"].append((test_info, "unit+slow"))
        
        if "unit" in test_info.markers and "integration" in test_info.markers:
            issues["conflicts"].append((test_info, "unit+integration"))
    
    return issues
```

#### Phase 4: Auto-Fix
Automatically add missing markers:

```python
def auto_fix_markers(test_file: Path, fixes: List[tuple]) -> None:
    """Add missing markers to test file."""
    lines = test_file.read_text().splitlines()
    
    # Sort fixes by line number (reverse to preserve line numbers)
    fixes.sort(key=lambda f: f[0], reverse=True)
    
    for lineno, marker in fixes:
        # Insert marker decorator before test function
        indent = len(lines[lineno - 1]) - len(lines[lineno - 1].lstrip())
        marker_line = " " * indent + f"@pytest.mark.{marker}"
        lines.insert(lineno - 1, marker_line)
    
    # Write back
    test_file.write_text("\n".join(lines) + "\n")
```

### Output Format

#### Validation Report
```
🏷️  Test Marker Validation
=====================================================================

Scanning 259 tests across 47 files...

Invalid Markers (typos?):
  ✗ tests/nodb/test_climate.py::test_build_gridmet (line 123)
    Unknown marker: @pytest.mark.intergration
    Did you mean: @pytest.mark.integration?

Missing Category Markers:
  ⚠️  tests/wepp/test_soil_util.py::test_modify_kslast (line 45)
     No category marker (should have @pytest.mark.unit or similar)
     
  ⚠️  tests/routes/test_wepp_bp.py::test_run_endpoint (line 78)
     No category marker

Unmarked Slow Tests (>2s):
  ⚠️  tests/climates/test_daymet.py::test_fetch_tiles (3.2s)
     Missing @pytest.mark.slow
     
  ⚠️  tests/nodb/test_wepp.py::test_run_watershed (4.8s)
     Missing @pytest.mark.slow

Conflicting Markers:
  ✗ tests/wepp/test_quick.py::test_fast_check (line 67)
    Has both @pytest.mark.unit and @pytest.mark.slow
    Unit tests should be fast; remove one marker

Summary:
  • 1 invalid marker
  • 2 tests missing category markers
  • 2 unmarked slow tests
  • 1 conflicting marker
  
Total issues: 6

Run with --fix to automatically add missing markers.
```

#### Auto-Fix Report
```
🏷️  Auto-Fixing Test Markers
=====================================================================

Adding missing markers...

  ✓ tests/climates/test_daymet.py::test_fetch_tiles
    Added @pytest.mark.slow (line 234)
    
  ✓ tests/nodb/test_wepp.py::test_run_watershed
    Added @pytest.mark.slow (line 567)
    
  ✓ tests/wepp/test_soil_util.py::test_modify_kslast
    Added @pytest.mark.unit (line 45)

Fixed 3 tests.
Remaining issues require manual review:
  • 1 invalid marker (typo)
  • 1 conflicting marker

Please review and commit changes.
```

### Integration

Add to `wctl/wctl.sh`:

```bash
check-test-markers)
  shift
  FIND_SLOW=""
  VALIDATE=""
  FIX=""
  REPORT_ONLY=""
  TEST_PATH="tests"
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --find-slow) FIND_SLOW="--find-slow"; shift ;;
      --validate) VALIDATE="--validate"; shift ;;
      --fix) FIX="--fix"; shift ;;
      --report-only) REPORT_ONLY="--report-only"; shift ;;
      *) TEST_PATH="$1"; shift ;;
    esac
  done
  
  CMD="cd /workdir/wepppy && python tools/check_markers.py"
  [[ -n "$FIND_SLOW" ]] && CMD="$CMD $FIND_SLOW"
  [[ -n "$VALIDATE" ]] && CMD="$CMD $VALIDATE"
  [[ -n "$FIX" ]] && CMD="$CMD $FIX"
  [[ -n "$REPORT_ONLY" ]] && CMD="$CMD $REPORT_ONLY"
  CMD="$CMD $TEST_PATH"
  
  compose_exec_weppcloud "$CMD"
  exit 0
  ;;
```

### Success Criteria
- Detects all unmarked tests taking >2s
- Identifies marker typos with suggestions
- Auto-fix adds correct markers without breaking tests
- Validates against pytest.ini marker definitions
- Zero false positives on properly marked tests
- Runs in <10 seconds for full suite

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. Implement `wctl test-coverage` (simplest, highest value)
2. Set up `.coveragerc` with proper excludes
3. Document coverage workflow in `tests/README.md`

### Phase 2: Performance (Week 2)
4. Implement `wctl test-profile`
5. Establish performance baseline for current suite
6. Identify and document slow tests
7. Add performance tracking to CI

### Phase 3: Quality (Week 3)
8. Implement `wctl check-test-markers`
9. Run validation and fix unmarked tests
10. Add marker validation to pre-commit hooks

### Phase 4: Isolation (Week 4)
11. Implement `wctl check-test-isolation` (most complex)
12. Run against current suite to establish baseline
13. Document isolation patterns in `tests/AGENTS.md`

### CI Integration

Add to `.github/workflows/test.yml`:

```yaml
- name: Check test stubs
  run: wctl check-test-stubs

- name: Check test markers
  run: wctl check-test-markers --validate

- name: Run tests with coverage
  run: wctl test-coverage --check --min=80 --json > coverage.json

- name: Check performance regressions
  run: wctl test-profile --compare --threshold=5

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: coverage.json
```

---

## Success Metrics

### Immediate Impact
- **Test isolation issues**: Detect within 1 week of occurrence
- **Coverage gaps**: Identified per module, enforced at 80%+
- **Performance regressions**: Caught before merge (>20% slower fails CI)
- **Marker compliance**: 100% of tests properly categorized

### Long-term Goals
- **Test suite time**: Reduce from 312s to <240s (25% improvement)
- **Flaky test rate**: Reduce to <1% via isolation checking
- **Coverage trend**: Increase from 93% to 95%+ over 6 months
- **Developer velocity**: Faster feedback via selective test runs

---

## References

- Original issue: `test_disturbed_bp.py` import failure (October 2025)
- Related docs: `tests/AGENTS.md`, `tests/README.md`
- Tools: `wctl check-test-stubs`, pytest-cov, pytest-randomly
- Future work: Consider pytest-xdist for parallel execution
