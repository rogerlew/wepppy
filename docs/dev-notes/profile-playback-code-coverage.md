# Profile Playback Code Coverage Mapping

> **Goal:** Map Python files, classes, methods, and functions executed during each profile playback run to understand test coverage and identify which profiles exercise which backend components.

## Overview

**Problem:** The 19 profile playback tests exercise different backend workflows, but there's no visibility into which Python modules, classes, or functions each profile actually uses.

**Solution:** Flask middleware-based coverage tracing activated via HTTP headers during playback, producing per-profile `coverage.py` data that we can post-process into a symbol-by-symbol map.

**Key Mechanism:**
1. Playback client adds `X-Profile-Trace: {profile_slug}` header to every HTTP request
2. Flask middleware intercepts this header and starts `coverage.py` tracing (line-level only; no per-call accounting needed)
3. All backend Python code executed during that request is traced (Fortran/Rust binaries remain out-of-scope)
4. Coverage data accumulates across the entire playback session into a `.coverage` file
5. Post-playback: convert the `.coverage` binary to JSON/HTML reports and merge with a static symbol inventory

**No Re-recording Required:** Existing profile captures work as-is; only the playback mechanism changes.

## Current State

### Profile Structure
Profiles are recorded user interactions that capture:
- HTTP requests (GET/POST with payloads)
- Run directory snapshots
- Configuration artifacts
- File uploads

Playback replays these interactions against WEPPcloud to verify modeling workflows.

### Playback Profiles (`.github/forest_workflows/playback-profiles.yml`)
19+ profiles exercising different scenarios:
- **Delineation:** TOPAZ, WBT, Peridot
- **Climate:** CLIGEN, Daymet, PRISM, GridMET, E-OBS, NEXRAD
- **Soils:** SSURGO, ISRIC, disturbed conditions
- **Land use:** NLCD, RAP, custom uploads
- **Models:** WEPP, RHEM, WATAR (ash transport), revegetation, debris flow
- **Regions:** US, Canada, Europe, Australia

### Current Gap
**No mapping exists between profiles and the code they exercise.** We can't answer:
- Which profiles test `wepppy.nodb.core.Climate.build()`?
- Does any profile exercise `wepppy.climates.prism` monthly interpolation?
- What's the unique code path tested only by `rattlesnake-topaz-vanilla-wepp-watar`?
- Which NoDb controllers never get touched by profile tests?

## Architecture Clarification

**Critical insight:** Profile playback is a **client-server interaction**:
- **Playback client** (`PlaybackSession`) replays HTTP requests
- **WEPPcloud server** (Flask routes) processes those requests and executes backend code

**Therefore:** Code tracing must happen **server-side** in the Flask app, not in the playback client.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ GitHub Actions / Local Development                              │
│                                                                 │
│  ┌──────────────────────────────────────────────┐               │
│  │ Playback Client (PlaybackSession)            │               │
│  │                                              │               │
│  │ 1. Read profile events from disk             │               │
│  │ 2. Add X-Profile-Trace: {profile_slug} header│───────┐       │
│  │ 3. Send HTTP requests to WEPPcloud           │       │       │
│  └──────────────────────────────────────────────┘       │       │
│                                                         │       │
└─────────────────────────────────────────────────────────┼───────┘
                                                          │
                                      HTTP Request        │
                                      X-Profile-Trace: us-small-wbt...
                                                          │
                                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ WEPPcloud Flask Server                                          │
│                                                                 │
│  ┌──────────────────────────────────────────────┐               │
│  │ CoverageMiddleware                           │               │
│  │                                              │               │
│  │ @before_request:                             │               │
│  │   - Check for X-Profile-Trace header         │               │
│  │   - Start coverage.Coverage() tracing        │               │
│  │                                              │               │
│  │ Request Processing:                          │               │
│  │   Flask Routes → NoDb Controllers →          │               │
│  │   Climate/Soils/Wepp modules                 │               │
│  │   [All code execution is traced]             │               │
│  │                                              │               │
│  │ @after_request:                              │               │
│  │   - Stop coverage tracing                    │               │
│  │   - Save to .coverage file                   │               │
│  └──────────────────────────────────────────────┘               │
│                                                                 │
│  Coverage Data: /workdir/wepppy-test-engine-data/coverage/      │
│                 {profile_slug}.coverage                         │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ After playback completes
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Report Generation                                               │
│                                                                 │
│  tools/generate_coverage_reports.py                             │
│  - Load .coverage files                                         │
│  - Generate JSON reports (programmatic analysis)                │
│  - Generate HTML reports (human review)                         │
│  - Extract summaries (%, modules, functions)                    │
│                                                                 │
│  Output: coverage-reports/{profile_slug}-coverage.json          │
│          coverage-reports/{profile_slug}/html/index.html        │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Analysis & Aggregation                                          │
│                                                                 │
│  tools/analyze_profile_coverage.py                              │
│  - Load all JSON reports                                        │
│  - Generate coverage matrix (module × profile)                  │
│  - Identify unique coverage per profile                         │
│  - Find gaps (uncovered modules)                                │
│                                                                 │
│  Output: coverage-matrix.json                                   │
│          coverage-summary.md                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Points

1. **Request-scoped tracing:** Coverage starts/stops for each HTTP request
2. **Cumulative data:** `coverage.py` accumulates data across multiple requests to the same `.coverage` file
3. **Profile isolation:** Each profile gets its own `.coverage` file
4. **No re-recording needed:** Uses existing profile captures; only adds tracing header

## Implementation Concept

### Middleware Architecture

Flask middleware intercepts every HTTP request and:
1. **Detects the trace header** (`X-Profile-Trace`)
2. **Initializes coverage tracing** using Python's `coverage.py` library
3. **Starts tracing** before the request is processed
4. **Stops tracing** after the response is generated
5. **Saves coverage data** to a profile-specific `.coverage` file

#### Request Lifecycle

```
HTTP Request arrives
  ↓
Middleware checks for X-Profile-Trace header
  ↓
If present: Start coverage.Coverage() with profile-specific data file
  ↓
Process Flask route → Controller → Backend modules
  [All Python code execution is traced]
  ↓
Generate response
  ↓
Middleware stops coverage tracing
  ↓
Save accumulated data to {profile_slug}.coverage file
  ↓
Return HTTP response
```

#### Key Characteristics

- **Request-scoped:** Each HTTP request gets traced independently
- **Cumulative:** Multiple requests append to the same `.coverage` file for a profile run. The `.coverage` file provides a comprehensive record of backend model code execised by the profile
- **Non-intrusive:** Routes/controllers don't need modification
- **Opt-in:** Only activated when header is present
- **Profile-isolated:** Each profile slug gets its own coverage file
### Requirements

**Environment Setup:**
- `ENABLE_PROFILE_COVERAGE=1` environment variable activates middleware
- `PROFILE_COVERAGE_DIR` specifies where `.coverage` files are saved (default: `/workdir/wepppy-test-engine-data/coverage`)

**Flask Integration:**
- Middleware registers hooks: `@before_request`, `@after_request`, `@teardown_request`
- Initialized in `create_app()` factory function

**Playback Client Changes:**
- Add `--trace-code` CLI flag to wctl
- When enabled, add `X-Profile-Trace: {profile_slug}` header to all HTTP requests

**Dependencies:**
- Python `coverage.py` library (already part of dev dependencies)

### HTTP Header Protocol

**Header Name:** `X-Profile-Trace`  
**Header Value:** `{profile_slug}` (e.g., `us-small-wbt-daymet-rap-wepp`)

The playback client includes this header in every HTTP request during a profile run. The middleware uses the slug to:
- Identify which profile is running
- Name the `.coverage` output file
- Group all requests from one playback session

### Coverage Data Files

**Location:** `/workdir/wepppy-test-engine-data/coverage/{profile_slug}.coverage`

**Format:** Binary SQLite database (`.coverage` is Python `coverage.py`'s native format)

**Contents:** The `.coverage` file stores:
- **Line-level execution data:** Which lines of which files were executed
- **Branch coverage:** Which code branches were taken
- **Execution context:** Metadata about when/how code was traced (we will use dynamic contexts to encode `{profile_slug}:{request_id}`)
- **Cumulative data:** All requests from a playback session accumulate into one file

**Why SQLite:** `coverage.py` uses SQLite for efficient incremental updates across a profile run with multiple HTTP requests.

**File lifecycle:**
1. **First request:** Middleware creates `.coverage` file
2. **Subsequent requests:** Middleware appends to existing file
3. **Playback completes:** File contains coverage from entire profile run
4. **Post-processing:** Convert to JSON/HTML using `coverage.py` report generators

### Multi-Process + Worker Handling

`coverage.py` only writes to a single SQLite file per process. WEPPcloud uses multiple Flask workers, celery-style RQ workers, and subprocess-heavy tasks, so we need a deterministic way to merge per-process data without duplicating code changes everywhere.

**Strategy:**

1. **Parallel coverage mode:** Initialize coverage with `data_file=/.../{slug}.coverage`, `data_suffix=True`, `parallel=True`, and `context=f"profile:{slug}:{request_id}"`. The suffix prevents concurrent writers from trampling each other; `coverage combine` later merges them into the canonical `{slug}.coverage`.
2. **Slug propagation:** The middleware stores the slug in `g.profile_trace_slug`. When a traced request enqueues an RQ job (or launches a subprocess that runs Python), a helper attaches the slug to job metadata/environment (for example `job.meta["profile_trace_slug"] = g.profile_trace_slug`). Centralized enqueue utilities (e.g., `wepppy.rq.project_rq.enqueue_wepp_job`) are the only code that needs to know about this; we do **not** have to touch every endpoint individually.
3. **Worker bootstrap:** RQ workers call a shared initializer that checks for `PROFILE_TRACE_SLUG` (set from job meta before the task runs). If present, workers start coverage with the same `{slug}` data file + suffix, run the task, stop coverage, and flush data. This captures all downstream Python execution kicked off by the profile, even if it finishes after the HTTP response returns.
4. **Combine step:** After the profile playback finishes, run `coverage combine /workdir/wepppy-test-engine-data/coverage/{slug}` to merge shards. The nightly pipeline can then emit JSON/HTML reports directly from the merged file.

This keeps the instrumentation surface limited to: (a) the middleware, (b) the enqueue helpers that already wrap job dispatch, and (c) the RQ worker entry point. Regular Flask routes/controllers remain untouched.

### Symbol Inventory + Line Hits

The profile artifact needs to list every class/function even when no profile touches it. Coverage data alone cannot describe “everything defined” — it only records executed line numbers. We therefore need a lightweight static scan step:

1. Walk the whitelisted directories (`wepppy/nodb`, `wepppy/wepp`, etc.) with `ast` to capture every class, method, and function definition plus start/end lines.
2. Serialize that inventory to `coverage-symbols.json` (or a SQLite table) so nightly jobs can reuse it without re-parsing the tree.
3. During report generation, intersect each symbol’s line span with the `executed_lines` pulled from the combined coverage JSON. If any line within the span appears in coverage output, mark the symbol as “covered_by = [slug]`.
4. Produce matrices like `symbol -> [slug...]`, `slug -> [symbols...]`, and tree views showing uncovered regions.

Because we only care about Python backend coverage, non-Python executables (Fortran, Rust, Whitebox) stay outside this inventory and we skip trying to trace them.

### Coverage Config

Create a dedicated `coverage.profile-playback.ini` alongside the Flask app:

```ini
[run]
source = wepppy
parallel = True
dynamic_context = test_function
omit =
    wepppy/tests/*
    wepppy/tools/*
    wepppy/scripts/*
    wepppy/wepp/migrations/*

[report]
exclude_lines =
    pragma: no cover
    if TYPE_CHECKING:
```

The middleware loads this config when `ENABLE_PROFILE_COVERAGE=1`, ensuring that nightly artifacts always ignore tests, CLI helpers, and migrations without depending on developer-specific `~/.coveragerc` files.

## Output Formats

### Profile Coverage Report (`{profile_slug}-coverage.json`)

example output (line hits only; no per-call accounting):

```json
{
  "profile": "us-small-wbt-daymet-rap-wepp",
  "timestamp": "2025-11-09T12:34:56Z",
  "summary": {
    "file_count": 87,
    "module_count": 42,
    "class_count": 156,
    "function_count": 1243,
    "lines_covered": 4521,
    "lines_total": 8903,
    "coverage_percent": 50.8
  },
  "modules": [
    "wepppy.nodb.core.climate",
    "wepppy.nodb.core.wepp",
    "wepppy.climates.daymet",
    "wepppy.topo.wbt"
  ],
  "classes": [
    "wepppy.nodb.core.climate.Climate",
    "wepppy.nodb.core.wepp.Wepp",
    "wepppy.climates.daymet.DaymetClient"
  ],
  "symbols": [
    {
      "name": "wepppy.nodb.core.climate.Climate.build",
      "file": "/workdir/wepppy/wepppy/nodb/core/climate.py",
      "line_span": [430, 520],
      "executed_lines": [487, 488],
      "covered": true
    },
    {
      "name": "wepppy.climates.daymet.DaymetClient.get_monthly_data",
      "file": "/workdir/wepppy/wepppy/climates/daymet/client.py",
      "line_span": [180, 240],
      "executed_lines": [],
      "covered": false
    }
  ]
}
```


## References

- Python `coverage.py` docs: https://coverage.readthedocs.io/
- `sys.settrace()` reference: https://docs.python.org/3/library/sys.html#sys.settrace
- `cProfile` guide: https://docs.python.org/3/library/profile.html
- GitHub Actions artifact uploads: https://github.com/actions/upload-artifact
