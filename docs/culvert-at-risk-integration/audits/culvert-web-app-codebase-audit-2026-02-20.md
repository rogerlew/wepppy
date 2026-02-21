# Culvert_web_app Codebase Audit (Dev Clone)

Date: 2026-02-20  
Repository reviewed: `https://github.com/SouravDSGit/Culvert_web_app/`  
Author: Roger Lew, GPT-5.3-codex, Claude Opus 4.6  
Audit target: barriers/challenges to scaling and incorporating new models. 

## Executive conclusion

Codebase maturity is the dominant current and future scaling constraint.

The critical blockers are not only infrastructure capacity, but code-level structure: a very large monolithic Flask app, weak trust boundaries in file handling/auth, high cyclomatic complexity in core geospatial routines, low test coverage depth, and heavy path-based data coupling. Adding a new model currently requires touching backend route code, long task modules, form parsing logic, and large frontend scripts, with limited automated safety nets.

## Why Codebase Dominates Over Infrastructure

Important strengths in the current baseline:

- Strong domain functionality: end-to-end watershed, hydrologic, and hydro-geomorphic workflows are already implemented.
- Background execution exists (`RQ` + Redis), so long-running jobs are offloaded from request handlers.
- Real-time progress/cancel UX is implemented and user-facing flow completeness is comparatively good.
- A containerized deployment baseline exists (`Dockerfile`, `docker-compose`, `Caddy`), which is materially better than ad-hoc host setup.
- Production ready code with tests has been provided by Roger for incorporation with 20x performance gain for watershed delineation and 10x to raster zonal statistics calculations.

Infrastructure constraints exist, but they are secondary in this repo because the highest-impact risks are application-design and code-quality risks:

- Core security exposures are in code paths, not hosting capacity (for example `eval`, ZIP extraction/path handling, CSRF gaps, Socket.IO origin policy, and unsafe shared file operations).
- Increasing infrastructure parallelism does not fix those defects and can worsen behavior where no locking exists (`20` RQ workers with shared-file and shared-dict mutation patterns).
- Performance ceilings are primarily algorithmic and implementation-level (for example O(n^2) hierarchy processing and unbounded external-service retry loops), so additional CPU/RAM does not remove the bottleneck class.
- New-model integration cost is dominated by cross-layer code coupling (template/JS -> Flask route parsing -> task orchestration -> utility calls), naming drift, and wide parameter plumbing.
- Regression risk during change is driven by low typing coverage and limited tests/CI gating, which are codebase maturity concerns rather than infrastructure provisioning concerns.

Bottom line: infrastructure tuning can improve throughput at the margin, but codebase hardening/modularization is the first-order prerequisite for reliable scaling.

## Scope and method

This was a static/dev-box audit (not a production runtime assessment). Review used:

- `radon` for complexity/maintainability/raw metrics
- `pytest` collection and run for test health
- `vulture` for dead-code indicators
- `rg`, `wc`, `git log`/`numstat` for churn/debt and architecture signals
- Manual source inspection for security and integration coupling
- Cross-check against migration guide: `/workdir/wepppy/docs/culvert-at-risk-integration/dev-package/weppcloud-wbt-unnest-basins-migration-guide.md`

## Quick risk profile

| Domain | Risk |
| --- | --- |
| Security | Critical |
| Code quality and maintainability | High |
| Technical debt | High |
| Flexibility/adaptability for new models | High |
| Testing and error handling | High |
| Performance and scalability | High |
| DevOps/deployment process | Medium-High |
| Data architecture | High |
| Frontend/visualization architecture | Medium-High |
| Documentation accuracy and operational guidance | Medium-High |

## Metric interpretation for non-developers

### What LOC means

- `LOC` = lines of code (including blanks/comments depending on metric).
- `SLOC` = source lines of code (blank/comment lines removed).
- Why it matters: larger files are harder to review, test, and safely change.

### What cyclomatic complexity means

- Cyclomatic complexity (`CC`) is the number of independent decision paths through a function.
- Roughly: each `if`/`elif`/loop/branch adds paths you must reason about and test.
- Why it matters: higher CC correlates with defect risk and regression risk when changing logic.

### What maintainability index (radon) means

- Maintainability Index (`MI`) is a single score that combines code size, complexity, and documentation/comment signal.
- Higher is better: higher MI generally means code is easier/safer to change.
- MI is usually reported on a `0-100` scale (radon floors extreme values at `0`), so very low scores are a strong warning sign.
- Radon also gives a coarse letter rank (`A/B/C`), but this audit uses raw MI numbers because they are more informative than a coarse letter.
- Why it matters: low MI hotspots usually require more engineering time per change, higher test burden, and have higher regression risk.

### “Reasonable” limits used in WEPPpy (documented standard)

WEPPpy’s documented observe-only code-quality bands are:

- `docs/dev-notes/code-quality-observability.md` (severity bands)
- `AGENTS.md` (treat LOC/complexity bands as triage telemetry, not hard merge blockers)

| Metric | Yellow | Red |
| --- | ---: | ---: |
| Python file SLOC | 650 | 1200 |
| Python function length (lines) | 80 | 150 |
| Python cyclomatic complexity (max per file) | 15 | 30 |
| JS file SLOC | 1500 | 2500 |
| JS cyclomatic complexity (max per file) | 15 | 30 |

Applied to Culvert_web_app Python (non-junk files):

- File SLOC bands: `33 green`, `7 yellow`, `8 red`
- Function-length bands: `18 green`, `6 yellow`, `24 red`
- CC bands: `18 green`, `11 yellow`, `15 red`
- `culvert_app/app.py` SLOC is `4017` (well above the red `1200` band)
- Peak CC is `151` (`5x` the red CC band of `30`)

## 1. Security

### 1.1 Known GitHub issues status (validated in current code)

All five are still exploitable from code review.

As of 2026-02-20, GitHub issue `#103` remains open and the traversal condition is still reachable in current code paths.

| Vulnerability | Submitted (issue opened) | Status | Evidence Ref |
| --- | --- | --- | --- |
| RCE via `eval()` (`#177`) | `2026-02-06` | Still present | `E1` |
| Zip-Slip path traversal (`#178`, `#182`) | `2026-02-06` (`#178`), `2026-02-18` (`#182`) | Still present | `E2` |
| Zip bomb/no size limits (`#182`) | `2026-02-18` | Still present | `E3` |
| Missing `MAX_CONTENT_LENGTH` (`#182`) | `2026-02-18` | Still present | `E4` |
| Download path traversal (`#103`) | `2025-09-22` | Still present (bypassable) | `E5` |

Evidence reference key:

- `E1`: `culvert_app/tasks/hydro_vuln_analysis_task.py:576`
- `E2`: `culvert_app/utils/subroutine_zipshapefile_with_GDAL.py:16-18` uses `extract` with archive names; no canonical path enforcement.
- `E3`: Upload endpoints save ZIPs directly and process them; no archive size/member count thresholds.
- `E4`: No `MAX_CONTENT_LENGTH` config found in `culvert_app`.
- `E5`: User-controlled file list enters via `request.json` (`culvert_app/app.py:5199`), then worker checks `os.path.join(base, filename).startswith(base)` (`culvert_app/tasks/download_output_files_task.py:97`, `culvert_app/tasks/download_output_files_task.py:104`) without canonical normalization (`realpath`/`commonpath`).

`#103` exploitability note:

- The check at `culvert_app/tasks/download_output_files_task.py:104` is string-prefix based, so traversal payloads with `../` segments can pass prefix validation before path resolution.
- Download preparation route accepts file names from client JSON (`culvert_app/app.py:5199`) and forwards them to background task packaging.
- This means an authenticated attacker can attempt to request files outside project output directories if the resolved target exists/readable.

### 1.2 Additional security concerns found

- Potential authorization bypass pattern in streamflow/precip routes: URL `user_id` is overwritten from form data and reused for filesystem paths:
  - `culvert_app/app.py:4372`, `culvert_app/app.py:4421`, `culvert_app/app.py:4452`, `culvert_app/app.py:4486`, `culvert_app/app.py:4531`, `culvert_app/app.py:4562`
- File-explorer rendering path is vulnerable to DOM-injection/XSS if file or directory names contain HTML/script payloads:
  - backend returns raw names from filesystem enumeration: `culvert_app/app.py:5341`, `culvert_app/app.py:5351`
  - frontend injects names into `innerHTML` template strings without escaping: `culvert_app/static/js/explore_download_files.js:527`, `culvert_app/static/js/explore_download_files.js:536`, `culvert_app/static/js/explore_download_files.js:556`
- Sensitive form-response content is printed to logs in debug flows:
  - `culvert_app/app.py:2097`
  - `culvert_app/app.py:2266`
- Weak secret fallback in app config:
  - `culvert_app/app.py:224` falls back to static dev secret string
- Testing endpoint exposed in application:
  - `culvert_app/app.py:341` (`/test-smtp`)
- Email behavior forced on with testing bypass:
  - `culvert_app/app.py:323`

### 1.3 Shapefile ZIP dependency is a primary security amplifier

- Core uploads are explicitly ZIP/shapefile based in both UI and backend paths:
  - `culvert_app/templates/ws_deln.html:361`, `culvert_app/templates/ws_deln.html:542`, `culvert_app/templates/ws_deln.html:602`
  - `culvert_app/app.py:2742`, `culvert_app/app.py:3268`, `culvert_app/app.py:3571`
- ZIP extraction in shapefile processing currently trusts archive member names:
  - `culvert_app/utils/subroutine_zipshapefile_with_GDAL.py:16-18`
- ZIP-backed geopandas reads are widespread (`zip://...`) across route, task, and utility code:
  - `culvert_app/app.py:2752`, `culvert_app/app.py:3278`, `culvert_app/app.py:3581`
  - `culvert_app/utils/subroutine_nested_watershed_delineation.py:2039`, `culvert_app/utils/subroutine_nested_watershed_delineation.py:2040`

Why this matters:

- Shapefile is a multi-file format, so the app repeatedly accepts and unpacks user-controlled ZIP archives as a normal workflow.
- That dependency directly increases exposure to Zip-Slip and Zip Bomb classes, compared with single-container alternatives (GeoPackage) or single-object alternatives (GeoParquet/GeoJSON).

### 1.4 CSRF and cross-origin control gaps

- Flask-WTF `FlaskForm` classes are present, but no CSRF middleware integration (`CSRFProtect`) is configured in the reviewed app code:
  - `culvert_app/app.py:31`, `culvert_app/app.py:330`, `culvert_app/app.py:496`, `culvert_app/app.py:507`
- Static JS contains `44` `fetch(...)` calls and no CSRF-token header usage (`X-CSRFToken` or equivalent).
- Examples of state-changing POSTs without CSRF token headers:
  - `culvert_app/static/js/ws_delin.js:1825`
  - `culvert_app/static/js/hydrovuln.js:425`
  - `culvert_app/static/js/hydrovuln.js:1119`
  - `culvert_app/static/js/explore_download_files.js:186`
  - `culvert_app/static/js/explore_download_files.js:286`
- Socket.IO accepts all origins in both primary and fallback modes:
  - `culvert_app/app.py:194`
  - `culvert_app/app.py:213`

### 1.5 Session, request-abuse, and browser-header hardening gaps

- Session backend is configured, but cookie hardening flags are missing from config:
  - current config keys only at `culvert_app/app.py:227`, `culvert_app/app.py:228`, `culvert_app/app.py:229`, `culvert_app/app.py:230`, `culvert_app/app.py:231`
  - no `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, or `SESSION_COOKIE_SAMESITE` setting found in the reviewed tree
- No rate-limiting integration (`Flask-Limiter` or equivalent) was found in the reviewed Python code.
- No explicit CSP/X-Frame/HSTS policy was found in app/proxy config:
  - app sets cache headers only in reviewed response blocks (`culvert_app/app.py:1079`, `culvert_app/app.py:1080`, `culvert_app/app.py:1081`)
  - Caddy reverse proxy site block has no explicit security-header directives (`Caddyfile:11`, `Caddyfile:27`)

### 1.6 Concurrency safety gaps in shared state and shared filesystems

- Runtime topology uses `20` RQ worker processes:
  - `docker-compose.yml:53`
- Locking primitives were not found in reviewed Python code (`flock`, `filelock`, `threading.Lock`, `multiprocessing.Lock` all absent).
- Shared-file race exposure examples:
  - overwrite form response file with no lock: `culvert_app/app.py:3944`
  - append writes with no lock: `culvert_app/app.py:4228`, `culvert_app/app.py:4235`
  - hydro-vuln response write with no lock: `culvert_app/app.py:4622`
  - temp dir delete/recreate pattern in task path: `culvert_app/tasks/hydrogeo_vuln_analysis_task.py:293`, `culvert_app/tasks/hydrogeo_vuln_analysis_task.py:294`
  - download directory mutation in worker vs cleanup route:
    - `culvert_app/tasks/download_output_files_task.py:76`, `culvert_app/tasks/download_output_files_task.py:79`
    - `culvert_app/app.py:5403`, `culvert_app/app.py:5411`
- In-memory task state uses a global mutable dict with no synchronization:
  - declaration: `culvert_app/app.py:96`
  - updates: `culvert_app/app.py:904`, `culvert_app/app.py:910`, `culvert_app/app.py:923`, `culvert_app/app.py:970`, `culvert_app/app.py:976`, `culvert_app/app.py:985`
  - delete iteration on logout: `culvert_app/app.py:5746`, `culvert_app/app.py:5749`

Developer barrier: security debt is load-bearing. A developer adding any new upload, download, or file-processing feature inherits all of the above vulnerabilities. Fixing them retroactively is harder than building on a secure foundation, but building new features on top of known-broken foundations means every new endpoint expands the attack surface. The absence of CSRF middleware means every new `fetch()` call must be manually hardened — and there is no existing pattern in the JS to copy. The absence of locking means every new task that writes shared files is a new race condition, and the developer has no way to know they introduced one without concurrent load testing (which also does not exist).

## 2. Code quality

### 2.1 Size and concentration

- Total Python raw LOC: `58,369` (`37,140` SLOC)
- Python LOC excluding `utils/junk`: `42,030` (`27,974` SLOC)
- Top-heavy modules:
  - `culvert_app/app.py`: `5,786` lines
  - `culvert_app/static/js/hydrovuln.js`: `4,240` lines
  - `culvert_app/utils/subroutine_nested_watershed_delineation.py`: `4,056` lines
  - `culvert_app/utils/subroutine_rusle_analysis.py`: `3,370` lines
  - `culvert_app/static/js/hydrogeovuln.js`: `3,358` lines

Developer barrier: a developer opening `app.py` to add a route must navigate `70` existing routes and `89` functions to find the right insertion point. Merge conflicts are frequent because most changes touch the same file. Code review is slow because reviewers must mentally load thousands of lines of surrounding context to evaluate a small change.

### 2.2 Cyclomatic complexity (radon)

- Blocks analyzed: `522`
- Rank distribution: `A=280`, `B=108`, `C=73`, `D=18`, `E=12`, `F=31`
- Excluding `/junk`: still `F=20`
- Highest-risk blocks:
  - `add_appendices` CC `151` (`culvert_app/utils/subroutine_generate_CULVERT_Report.py:853`)
  - `run_wdfm_model` CC `143` (`culvert_app/utils/subroutine_wdfm_analysis.py:1099`)
  - `generate_hydrologic_vulnerability_map` CC `116` (`culvert_app/static/visualization/subroutine_plot_generator_for_report.py:1265`)
  - `add_layers_to_basemaps` CC `105` (`culvert_app/static/visualization/subroutine_add_layers_to_base_map.py:184`)
  - `run_hydro_vuln_analysis_task` CC `94` (`culvert_app/tasks/hydro_vuln_analysis_task.py:414`)

Interpretation against WEPPpy’s documented CC bands:

- Yellow risk begins at `15`; red at `30`.
- Culvert has multiple files with max CC in the `40-151` range.
- This is not “a little high”; these are deep-branching hotspots where every change needs wide test coverage to be safe.

Developer barrier: a function with CC `151` has `151` independent execution paths. A developer modifying that function cannot reason about whether their change is safe without testing a significant fraction of those paths — but only `8` tests exist in the entire repo. In practice, developers resort to manual testing of “the path I care about” and hope nothing else breaks.

### 2.3 Maintainability index (radon)

- MI files analyzed: `58`
- Mean MI: `48.6`, median `51.41`, min `0.0`
- MI `0.0` appears in critical files including (strong warning signal):
  - `culvert_app/app.py`
  - `culvert_app/utils/subroutine_nested_watershed_delineation.py`
  - `culvert_app/utils/subroutine_rusle_analysis.py`
  - `culvert_app/utils/subroutine_wdfm_analysis.py`
  - `culvert_app/utils/subroutine_generate_CULVERT_Report.py`

Developer barrier: MI `0.0` means the files that change most often are the most expensive to change safely. These are the exact files a developer must touch to add a model or fix a bug — the highest-traffic files have the worst maintainability scores.

### 2.4 Naming standardization and traceability

AST scan across 59 Python files:

- Functions: `599` total, `27` non-snake
- Arguments: `2,550` total, `261` non-snake
- Local vars: `9,471` total, `301` non-standard casing
- Examples:
  - `dataType`, `pourDataAvailibility`, `My_crs` in `culvert_app/app.py`
  - Mixed uppercase/snake forms across task and geospatial utility modules

No repository-level naming convention document was found in Culvert docs/READMEs for cross-layer field names (JS form keys, Flask route vars, task vars, payload vars).

Concrete same-concept name drift:

| Concept | Frontend/template name | Flask route/task name | downstream/util/payload name |
| --- | --- | --- | --- |
| Pour point selection | `pourPointDataSelect` (`culvert_app/templates/ws_deln.html:584`) | `pour_point_selection` (`culvert_app/app.py:3955`), `point_data_select` (`culvert_app/tasks/watershed_delineation_task.py:303`) | `pourDataAvailibility` typo variant (`culvert_app/app.py:4284`, `culvert_app/app.py:4297`, `culvert_app/app.py:4351`) |
| Hydro enforcement mode | `hydroEnforcementSelect` (`culvert_app/templates/ws_deln.html:652`) | `hydro_enforcement_selection` (`culvert_app/app.py:3925`, `culvert_app/app.py:3956`, `culvert_app/app.py:3968`) | `hydro_enforcement_select` (`culvert_app/tasks/watershed_delineation_task.py:304`, `culvert_app/utils/subroutine_nested_watershed_delineation.py:2013`, `culvert_app/tasks/build_payload.py:745`) |
| Flow accumulation threshold | `flowAccumThreshold` / `flowAccumThreshold_nohydro` (`culvert_app/templates/ws_deln.html:723`, `culvert_app/templates/ws_deln.html:770`) | `hydro_params['flow_accumulation_threshold']` (`culvert_app/app.py:3973`, `culvert_app/app.py:3987`) | `flow_accum_threshold` (`culvert_app/utils/subroutine_nested_watershed_delineation.py:2019`, `culvert_app/tasks/build_payload.py:760`) |
| Stream/precip data type | `streamflow_data_type` / `precip_data_type` (`culvert_app/static/js/hydrovuln.js:1115`, `culvert_app/static/js/hydrovuln.js:1344`) | `dataType` (`culvert_app/app.py:4373`, `culvert_app/app.py:4487`) | reused as filename prefix in persisted CSV path (`culvert_app/app.py:4384`, `culvert_app/app.py:4496`) |

Developer barrier: a developer searching for "how does pour point selection work" gets different results depending on which layer they search — `pourPointDataSelect`, `pour_point_selection`, `point_data_select`, `pourDataAvailibility` (sic). Grep misses related code paths unless you already know all aliases. Renaming or refactoring a concept requires coordinated changes across JS, HTML, Python routes, task files, and utility code with no tooling or contract enforcing consistency.

### 2.5 Excessive parameter plumbing in watershed flow

The watershed delineation task uses a “manual data bus” pattern: dozens of path/option values are threaded explicitly through branch-specific mega-calls.

Evidence:

- Branch call sites:
  - `watershed_delineation_point_both(...)` call with `51` keyword args (`culvert_app/tasks/watershed_delineation_task.py:330`)
  - `watershed_delineation_point_NA(...)` call with `44` keyword args (`culvert_app/tasks/watershed_delineation_task.py:385`)
  - `watershed_delineation_point_only_gauging_st(...)` call with `49` keyword args (`culvert_app/tasks/watershed_delineation_task.py:434`)
- Overlap between these call argument sets is very high (Jaccard `0.86-0.96`), indicating copy-variant plumbing rather than composable interfaces.
- Downstream function signatures mirror the same breadth:
  - `watershed_delineation_point_both` has `51` params (`culvert_app/utils/subroutine_nested_watershed_delineation.py:1980`)
  - `watershed_delineation_point_NA` has `44` params (`culvert_app/utils/subroutine_nested_watershed_delineation.py:2711`)
  - `watershed_delineation_point_only_gauging_st` has `47` params (`culvert_app/utils/subroutine_nested_watershed_delineation.py:3409`)
- Roughly `77-80%` of these params are path/file/location plumbing fields.

Developer barrier: adding one new model option (for example a new runoff method) means adding a form field in HTML, a JS handler, a route parser key in `app.py`, a task-call kwarg in 2-3 branch call sites, and a function parameter in 2-3 downstream signatures. Missing any one of these silently uses a stale default. There is no typed request object, schema validation, or compile-time check to catch the omission — the developer discovers it at runtime, if at all.

### 2.6 Type-hint and docstring coverage (Python)

Method:

- AST scan over Python files in `/workdir/Culvert_web_app`.
- Two views were measured:
  - full tree
  - active code (`utils/junk` and tests excluded)
- One file failed AST parsing due to syntax error:
  - `culvert_app/utils/junk/regional_frequency_analysis_colab_v.py:107`

Coverage summary:

| Metric | Full tree (60 parseable files) | Active code (48 files) |
| --- | ---: | ---: |
| Module docstring coverage | `16.67%` | `16.67%` |
| Class docstring coverage | `37.50%` | `33.33%` |
| Function docstring coverage | `73.73%` | `69.49%` |
| Functions with any type hints | `14.78%` | `15.16%` |
| Fully hinted functions (all params + return) | `11.33%` | `12.99%` |
| Parameter annotation coverage | `12.15%` | `13.39%` |

Additional signal:

- Variable annotations are nearly absent (`1` annotated variable over `8,402` assignment nodes in full-tree scan).

Subsystem distribution (active code):

| Subsystem | Function docstrings | Any type hints | Fully hinted |
| --- | ---: | ---: | ---: |
| `culvert_app/app.py` | `40.0%` | `0.0%` | `0.0%` |
| `culvert_app/tasks/*` | `93.65%` | `46.03%` | `46.03%` |
| `culvert_app/utils/*` (non-junk) | `71.89%` | `17.27%` | `14.86%` |
| `culvert_app/static/visualization/*.py` | `71.23%` | `6.85%` | `0.0%` |

Interpretation:

- Docstrings exist for many functions, but they are unevenly distributed, with large orchestration files (`app.py`) under-documented.
- Type hints are sparse across the codebase and close to absent in high-churn hotspots (`app.py`, major visualization/util modules), which weakens static analysis, refactor safety, and interface clarity.
- Tasks are the only area with moderate hint adoption; this pattern is not consistently applied elsewhere.

Developer barrier: without type hints, a developer's IDE cannot autocomplete parameters, catch type mismatches, or support safe renames. Refactoring a 51-parameter function signature is manual text surgery with no tooling safety net. `mypy` or `pyright` cannot be usefully run because annotation coverage is too low to produce actionable results.

### 2.7 Orthodoxy of data architecture (quality signal)

Data flow is largely path-and-file orchestration rather than domain model orchestration:

- `gpd.read_file` occurrences (non-junk Python): `208`
- `.to_file` occurrences (non-junk Python): `77`
- `os.path.join(DATA_FOLDER, ...)` occurrences: `138`
- Only one SQLAlchemy domain model (`User`): `culvert_app/models/user.py:6`

Developer barrier: a developer cannot inspect project state from a REPL, database query, or API call. Understanding what a project run produced requires navigating nested filesystem directories. There is no manifest or metadata index — if a file is missing or corrupted, the developer must trace the code path that was supposed to create it.

## 3. Maintainability

- `culvert_app/app.py` contains `70` routes and `89` function definitions.
- Route, background task, and model orchestration logic are tightly mixed.
  - Concrete example (watershed delineation):
    - The route `ws_deln_results` handles auth/session checks, filesystem cleanup/rebuild, form normalization/persistence, and task wiring in one place (`culvert_app/app.py:3833`, `culvert_app/app.py:3851`, `culvert_app/app.py:3876`, `culvert_app/app.py:3901`, `culvert_app/app.py:4051`).
    - The task `run_watershed_delineation_task` reparses those inputs and performs branch-heavy orchestration (`culvert_app/tasks/watershed_delineation_task.py:233`, `culvert_app/tasks/watershed_delineation_task.py:330`, `culvert_app/tasks/watershed_delineation_task.py:385`, `culvert_app/tasks/watershed_delineation_task.py:434`).
    - The downstream model utility consumes a very large path-parameter surface (`culvert_app/utils/subroutine_nested_watershed_delineation.py:1980`).
  - Why this impedes maintainability:
    - Adding or renaming one input requires synchronized changes across route parsing, task payload/call-site wiring, and model signatures; any miss becomes a runtime failure.
    - Unit testing is expensive because HTTP concerns, queue concerns, and model orchestration are not isolated behind clean interfaces.
    - Ownership boundaries are unclear, so refactors have large blast radius and regressions are harder to localize.
- Debug/control-path noise is high in production code:
  - `print(...)` in `app.py`: `307`
  - `except Exception as e` in `app.py`: `119`
  - bare `except:` in `app.py`: `9`
- Code reuse patterns are inconsistent: high duplication in progress/state helpers across task modules, but no shared hardened utility layer for common security-sensitive file operations.

Developer barrier: a developer can fix a local bug in minutes, but any change that crosses route/task/utility boundaries is high-risk. `307` print statements in `app.py` mean production logs are noisy — filtering signal from noise during debugging requires reading through output that mixes debug chatter with actual errors. `119` broad `except Exception` blocks mean errors are caught and logged but not typed or propagated, so failures present as silent wrong behavior rather than clear stack traces.

### 3.1 Route architecture audit

Full route inventory: `70` HTTP routes and `3` Socket.IO event handlers in `culvert_app/app.py`. No Flask Blueprints; all routes defined directly on the app instance. Cross-referenced against all frontend call sites (`fetch()`, `XMLHttpRequest`, `window.location.href`, `url_for()`, form `action=` attributes) across `12` JavaScript files and `8` HTML templates.

#### 3.1.1 HTTP method semantic violations

Critical:

| Route | Line | Issue |
| --- | ---: | --- |
| `GET /logout` | `5735` | Logout via GET is a security anti-pattern. Any page or email can embed `<img src="/logout">` or a cross-origin link to force-log a user out. Should be `POST` only. |
| `GET /report_generate/<user_id>/<project_name>` | `5662` | Triggers a background RQ job (side effect) via GET. GET must be safe and idempotent per HTTP spec. This enqueues work, mutates Redis state, and emits socket events. Should be `POST`. |
| `GET /test-smtp` | `341` | Exposes SMTP credential status and attempts live Zoho authentication on a GET with no `@login_required`. Should be removed in production or at minimum `POST` + admin-only gated. |

Moderate:

| Route | Line | Issue |
| --- | ---: | --- |
| `GET,POST /ws_deln/<int:user_id>/<project_name>` | `1887` | Accepts POST but the handler only uses GET logic (page rendering). The POST path is never hit by any frontend call site. Dead method declaration. |
| `GET,POST /hydrologic_vuln/<int:user_id>/<project_name>` | `2034` | Same: both methods do identical page-load logic. POST serves no purpose. |
| `GET,POST /hydrogeo_vuln/<int:user_id>/<project_name>` | `2204` | Same: both methods do identical page-load logic. POST serves no purpose. |
| `GET,POST /reset_hydro_vuln/<int:user_id>/<project_name>` | `4641` | **Bug:** only the `POST` branch has a return statement. A `GET` request falls through the `if request.method == 'POST'` block and the function returns `None`, which Flask converts to a `500 Internal Server Error`. |
| `POST,GET /hydro_vul_analysis/<int:user_id>/<project_name>` | `4184` | GET and POST do completely different things (GET renders analysis page with gauging station lookup; POST saves flagged-watershed decision and renders a template). These are two distinct operations sharing one route and should be split. |

Inconsistent URL naming convention (hyphens vs underscores vs nesting):

- Hyphens: `/cancel-bound`, `/reset-boundary`, `/cancel-dem`, `/check-file-existence`
- Underscores: `/upload_streamflow`, `/reset_precip`, `/delete_road_path`, `/check_streams_exist`
- Nested path: `/upload/boundary`, `/upload/dem`, `/upload/roaddata`, `/upload/pourpoint`
- Flat path: `/upload_streamflow`, `/upload_precip`

No consistent convention is documented or enforced. A developer choosing a URL for a new route has no pattern to follow and will add to the drift.

#### 3.1.2 Dead and suspect routes

| Route | Line | Evidence | Recommendation |
| --- | ---: | --- | --- |
| `GET /async` | `115` | Zero frontend references. Test harness for RQ queue (`q.enqueue(handle_request_sync, ...)`). | Remove. |
| `GET /test-smtp` | `341` | Zero frontend references. Debug-only. Leaks credential status without auth check. | Remove from production. |
| `GET /get_usa_bounds` | `2662` | Zero frontend references. Source comment says "Optional." Returns a hardcoded bounding box. | Remove or wire up. |

Infrastructure routes (not dead, but not user-facing):

| Route | Line | Notes |
| --- | ---: | --- |
| `GET /health` | `1192` | Used by proxy/infra only. Keep, but document as internal. |
| `GET /static-dashboard` | `1200` | Redirect glue for Caddy-served path. Keep. |

#### 3.1.3 Routes that should be consolidated or split

**A. Three near-identical project-delete routes**

```
POST /dashboard_delete_project     (line 1670)
POST /delete_project               (line 1736)
POST /delete_active_project        (line 1796)
```

All three perform the same operation: read `project_name` from JSON body, delete `{user_id}_{inputs,outputs,logs,temp}/{project_name}` directories, clear session. The only differences:

- `/delete_project` has `@log_route` decorator.
- `/delete_active_project` returns a `redirect_url` field in the JSON response.
- `/delete_active_project` is missing `@login_required` (`culvert_app/app.py:1796`), which is an authorization gap.

These should be consolidated into one `POST /delete_project` with an optional `redirect` flag in the request body.

**B. Cancel / Reset / Delete triplication per data type**

Each data type (boundary, DEM, road, pour point, streamflow, precipitation) has 2-3 near-identical route handlers:

| Data type | `cancel-*` | `reset-*` | `delete-*` |
| --- | --- | --- | --- |
| Boundary | `/cancel-bound` (`2806`) | `/reset-boundary` (`2852`) | — |
| DEM | `/cancel-dem` (`3107`) | `/reset-dem` (`3154`) | — |
| Road data | `/cancel-roaddata` (`3364`) | `/reset-roaddata` (`3408`) | `/delete_road_path` (`3470`) |
| Pour point | `/cancel-pour` (`3628`) | `/reset-pour` (`3673`) | — |
| Streamflow | — | `/reset_streamflow` (`4414`) | `/delete_streamflow_file` (`4445`) |
| Precipitation | — | `/reset_precip` (`4524`) | `/delete_precip_file` (`4555`) |

Total: `14` routes. The "cancel" handlers delete a single file. The "reset" handlers delete a file and optionally regenerate a map. The "delete" handlers delete a file. Structural overlap is very high.

These `14` routes could be reduced to `~3` parameterized routes (e.g. `POST /data/<data_type>/cancel`, `POST /data/<data_type>/reset`, `POST /data/<data_type>/delete`) with shared auth/session/logging boilerplate and a data-type dispatch table.

**C. `hydrologic_vuln` and `hydrogeo_vuln` are 95% duplicated**

`hydrologic_vuln` (`culvert_app/app.py:2034-2199`, `~167` lines) and `hydrogeo_vuln` (`culvert_app/app.py:2204-2369`, `~167` lines) are near-copy-paste of each other. Both:

1. Validate session user ID.
2. Construct directory paths.
3. Read `user_ws_deln_responses.txt` and check for `FlagKeepOptionSelect`.
4. Read gauging station names from shapefile.
5. Check WS delineation map existence.
6. Load map HTML (vulnerability map with WS delineation fallback).
7. Render a template.

The only differences are the template name (`hydro_vuln_analysis.html` vs `hydrogeo_vuln.html`) and some variable naming. A shared `_load_vulnerability_page(user_id, project_name, template_name, logger)` helper would eliminate `~160` lines of duplication.

Similarly, the gauging station name loading logic (read shapefile, filter by `Flag_Gst==1`, regex-sort by `GWS_ID`) is duplicated in `4` route handlers:

- `ws_deln` (`culvert_app/app.py:1956-1966`)
- `hydrologic_vuln` (`culvert_app/app.py:2077-2083`)
- `hydrogeo_vuln` (`culvert_app/app.py:2246-2252`)
- `hydro_vul_analysis` GET branch (`culvert_app/app.py:4312-4331`)

This should be a single helper function.

**D. `hydro_vul_analysis` GET vs POST should be separate routes**

The `POST` branch (`culvert_app/app.py:4209-4279`) saves a flagged-watershed decision to a text file and renders a template. The `GET` branch (`culvert_app/app.py:4281-4351`) reads a response file, conditionally loads gauging station names based on flag/pour-point state, selects a map, and renders the same template with different data. These are two distinct operations with no shared logic beyond auth checking.

Split into:

- `GET /hydro_vul_analysis/<int:user_id>/<project_name>` — load the analysis page.
- `POST /hydro_vul_analysis/<int:user_id>/<project_name>/accept_decision` — save the flagged-watershed decision.

**E. `hydrogeo_vuln_input_form` and `hydro_vul_analysis` share the same map/gauging-station loading pattern**

`hydrogeo_vuln_input_form` (`culvert_app/app.py:4802-4890`) duplicates the response-file parsing + flag-decision branching + gauging-station loading + map selection logic from `hydro_vul_analysis` GET. This pattern appears in at least `3` route handlers and should be extracted.

Interpretation:

- Route consolidation opportunities fall into three categories: identical logic behind different URLs (project delete: `3` routes → `1`), structurally identical CRUD operations per data type (cancel/reset/delete: `14` routes → `~3`), and copy-pasted page-load orchestration (vulnerability pages: `~330` duplicated lines across `2` routes, gauging-station loading duplicated across `4` routes).
- Combined, these `5` consolidation targets account for `~21` of the `70` routes (`30%`) and an estimated `~900` lines of duplicated or near-duplicated handler code.
- The duplication is not just a size concern — it is a correctness multiplier. A bug fix or behavior change in any shared pattern (session validation, map loading, file deletion, gauging-station sorting) must be applied to every copy independently, with no compile-time or test-time check that all copies were updated.
- The missing `@login_required` on `/delete_active_project` (`culvert_app/app.py:1796`) is a concrete example of duplication-induced defect: two of the three delete routes have the decorator, one does not, and nothing enforces consistency.

### 3.2 Route complexity assessment

Estimated cyclomatic complexity and line counts for the highest-complexity route handlers in `culvert_app/app.py`:

| Route handler | Lines | Est. CC | Primary pain points |
| --- | ---: | ---: | --- |
| `ws_deln_results` (`3830-4083`) | `253` | `~18` | 4-level nested conditionals for hydro/non-hydro parameter extraction; multiple form data parsing strategies (JSON embedded in FormData, raw JSON, plain FormData); directory cleanup; RQ enqueue. Should be split into form parsing, validation, and job dispatch. |
| `draw_boundary` (`2404-2627`) | `223` | `~15` | Entire geospatial pipeline in one handler: JSON validation, polygon construction, dual USA bounds checking (shapefile with coordinate fallback), UTM zone selection, area calculation, shapefile creation, zip packaging, map generation. Should be extracted to a service layer. |
| `send_support_email` (`614-837`) | `223` | `~12` | `30+` `print("DEBUG: ...")` statements. Inline HTML email template (`~40` lines). Two separate SMTP sends (support team + user confirmation). Debug logging accounts for roughly half the line count. |
| `hydro_vul_analysis` (`4184-4355`) | `171` | `~14` | Mixed GET/POST with completely different logic. GET path has nested conditionals for `flag_ws_decision` x `pourDataAvailibility` (`4` branches). Response file parsing done independently per method. |
| `upload_roaddata` (`3202-3359`) | `157` | `~11` | Boundary validation, shapefile read, geometry type filtering, UTM projection, 2500m buffering, clip, map generation — all inline. Geospatial processing should be a utility function. |
| `hydrologic_vuln` + `hydrogeo_vuln` (`2034-2369`) | `167` each | `~10` each | Nearly identical. Combined `~330` lines of duplicated code. `50+` debug print statements with emoji prefixes. |
| `generate_dashboard_content` (`5509-5655`) | `146` | `~8` | `12` file path constructions, conditional file selection, external function delegation. Moderate complexity; would benefit from a file-path config object. |

## 4. Best practices and modernity

Positive:

- Uses Flask 3.x, SQLAlchemy 2.x, RQ, Redis, SocketIO, GeoPandas stack.

### 4.1 Architectural pattern maturity (fair characterization)

Limited adoption of modern typed/modular architecture patterns, with over-reliance on synchronous procedural orchestration.

Evidence:

- Typed-structure patterns are largely absent in reviewed Python (`culvert_app`):
  - no `@dataclass`, `TypedDict`, `Protocol`, or Pydantic model usage found.
- Concurrency exists operationally (RQ workers), but active culvert workflows execute synchronously inside each job:
  - queue/background runtime is present (`culvert_app/app.py:221`, `culvert_app/app.py:946`)
  - core task entrypoints are synchronous procedural functions (`culvert_app/tasks/watershed_delineation_task.py:233`, `culvert_app/tasks/hydro_vuln_analysis_task.py:414`, `culvert_app/tasks/hydrogeo_vuln_analysis_task.py:251`)
  - only `4` async functions out of `599` total functions in `culvert_app`; 3 are in the abandoned WEPP utility module and 1 is a lightweight helper in `app.py` (AST/grep scan used in this audit)
- Core model workflows remain branch-heavy, manually wired, and path-parameter driven:
  - watershed branch-call pattern (`culvert_app/tasks/watershed_delineation_task.py:330`, `culvert_app/tasks/watershed_delineation_task.py:385`, `culvert_app/tasks/watershed_delineation_task.py:434`)
  - hardcoded method-control flow in hydrologic vulnerability task (`culvert_app/tasks/hydro_vuln_analysis_task.py:571`)
  - heavy file/path orchestration in route layer (`culvert_app/app.py`)

Interpretation:

- The system is not “without concurrency,” but concurrency is mostly infrastructure/runtime plumbing.
- Domain-level composition remains primarily synchronous/procedural, which increases integration cost and regression risk when adding or changing models.

Developer barrier: without `@dataclass`, `TypedDict`, or Pydantic models, a developer adding a new analysis method has no contract to implement against. They must read existing task code, infer the expected inputs/outputs from file paths and variable names, and manually wire everything. There is no interface to satisfy, no schema to validate against, and no type checker to confirm correctness.

Gaps versus modern production norms:

- Monolithic application entrypoint instead of bounded services/modules.
- No migration framework in repo; `db.create_all()` at startup (`culvert_app/app.py:284`, `culvert_app/app.py:5771`).
- Dependency hygiene issues in `culvert_app/requirements.txt`:
  - duplicate/conflicting constraints (`Flask==3.1.0` and `Flask>=2.0`, `gunicorn==23.0.0` and `gunicorn>=20.0`, duplicate `contextily`, both `dotenv` and `python-dotenv`).
- Security hardening missing in several upload/download patterns.

## 5. Technical debt (specific and quantified)

### 5.1 Git history: refactor cadence vs patch cadence (12 months to 2026-02-20)

- Total commits: `578`
- Non-merge commits: `395`
- Merge commits: `183`
- Active commit days: `141`
- Days containing patch/fix keywords (`fix`, `bug`, `error`, `revert`, `patch`, `testing`, etc.): `36` (`25.5%` of active days)
- Non-merge commits with patch/fix keywords: `91-93` (depending on keyword set; about `23%`)
- Repeated message patterns:
  - `fixed accept ws deln error` appears `9` times
  - `testing ws deln with map result loading` appears `11` times
  - indicates iterative rework loops in hotspot flows

Hotspot concentration (source files, 12 months):

- Total source touches: `705`
- Top 10 files account for `268` touches (`38.0%`)
- `culvert_app/app.py` alone touched `84` times

Refactor-frequency assessment:

- Strict refactor-like commit subjects (`refactor`, `restructure`, `rewrite`, `simplify`, `dedupe`, `extract`): `11/395` (`2.8%`)
- Patch/fix-like commit subjects (`fix`, `bug`, `error`, `patch`, `testing`, `test`): `91/395` (`23.0%`)
- Source touches in those commits:
  - strict-refactor touches: `23`
  - patch/fix touches: `134`
  - patch/fix to refactor touch ratio: `5.8x`

Core-hotspot refactor signal is near-zero:

- `culvert_app/app.py`: strict-refactor churn share `0.1%`
- `culvert_app/tasks/watershed_delineation_task.py`: `0.0%`
- `culvert_app/tasks/hydro_vuln_analysis_task.py`: `0.0%`
- `culvert_app/tasks/hydrogeo_vuln_analysis_task.py`: `0.2%`
- `culvert_app/utils/subroutine_nested_watershed_delineation.py`: `0.0%`

Additional copy/paste pattern evidence (current tree):

- Identical helper functions replicated across 5-6 task files:
  - `safe_emit_progress` in 5 files
  - `safe_update_task_state` in 5 files
  - `emit_and_update` in 6 files
- Cross-file repeated task blocks:
  - `60` repeated 8-line blocks appearing in at least 3 task files

Interpretation:

- The codebase shows mostly patch-in-place and duplication growth, not frequent consolidation/refactor of core patterns.
- Suggests “find something that works and copy/paste repeatedly” assessment is strongly supported by both git history signals and static duplication evidence.

Note:

- Commit-message keyword methods are an imperfect proxy, but the conclusion is corroborated by concrete duplicated function bodies and hotspot-file churn composition.

Developer barrier: `safe_emit_progress` duplicated in 5 files means a developer fixing a bug in progress reporting must find and patch all 5 copies — and nothing tells them where the copies are. The `5.8x` patch-to-refactor ratio means the codebase accumulates workarounds faster than it consolidates them, so each new developer inherits more variants to navigate. The `11` repeated `testing ws deln with map result loading` commits indicate a developer spending multiple sessions trying to get one flow to work, with no automated feedback loop to shorten the cycle.

### 5.2 Duplication metrics

Approximate cross-file clone scan (normalized 6-line shingles):

- Python duplication estimate: `3,162` duplicated normalized lines out of `29,956` (`10.56%`)
- JS duplication estimate: `2,707` duplicated normalized lines out of `13,027` (`20.78%`)

Near-duplicate signal in watershed logic:

- `subroutine_nested_watershed_delineation.py` vs `utils/junk/subroutine_watershed_delineation.py` similarity `0.748`

### 5.3 Dead code metrics

- `vulture` findings (`--min-confidence 70`): `77`
- Includes:
  - multiple unused imports in core files (`culvert_app/app.py`, visualization/util modules)
  - unreachable code (`culvert_app/static/visualization/subroutine_plot_generator_for_report.py:585`)
- Structural debt:
  - `culvert_app/utils/junk`: `22` files, `32,298` lines
  - `culvert_app/utils/notebooks`: `32` files, `98,989` lines
- Import-graph low-integration modules (in-degree 0) include production-named utilities such as:
  - `utils/subroutine_GSSURGO_data_preprocessing.py`
  - `utils/subroutine_USGS_Regression_Peak_flow_Stats.py`
  - `utils/subroutine_back_calculating_runoff.py`
  - `utils/subroutine_check_cancellation.py`
  - `utils/subroutine_run_WEPP_model.py`
  - `utils/subroutine_single_site_freq_analysis.py`

Developer barrier: a developer encountering `subroutine_run_WEPP_model.py` or `subroutine_GSSURGO_data_preprocessing.py` cannot tell from file naming or location whether the code is live, experimental, or abandoned. `131,287` lines of junk/notebook code sit alongside production code in the same directory tree, so search results are polluted with dead code. A developer investigating a bug may follow a code path into a file that is not actually imported or executed.

## 6. Flexibility and adaptability (new model integration readiness)

Current architecture makes new model integration expensive because control/data logic is spread across:

- request parsing in routes (`culvert_app/app.py`)
- task worker implementation (`culvert_app/tasks/*.py`)
- utility routines with direct file IO/geospatial operations (`culvert_app/utils/*.py`)
- large frontend scripts with form and map assumptions (`culvert_app/static/js/*.js`)

Concrete coupling example:

- Method selection and parsing are embedded inside long task flow (`culvert_app/tasks/hydro_vuln_analysis_task.py:571-590`), not a pluggable strategy registry.

Developer barrier: adding a new model requires coordinated changes in at minimum 4 layers (HTML template, JS form handler, Flask route parser, task worker, utility module). There is no pluggable model registry, strategy pattern, or configuration-driven dispatch. A developer cannot write and test a new model module in isolation — it must be wired into the full app to produce any output. Estimated minimum touch count for a new model: `6-10` files across `3-4` directories.

## 7. Testing and error handling

### 7.1 Test coverage footprint

- `pytest --collect-only`: `8` tests total
- `pytest`: `7 passed`, `1 error`
- failing test shape/fixture issue:
  - `culvert_app/test_concurrency_job.py::test_concurrent_job`
- warning signal:
  - multiple tests return bool instead of assertions in `test_dash_startup.py`
- collected suite scope is infrastructure/devops focused:
  - `test_dash_startup.py` validates dependency imports, file presence, port/process startup, and Dash HTTP reachability.
  - `culvert_app/test_concurrency_job.py` validates RQ concurrency timing/Redis write behavior.
- no collected tests exercise core domain/data-processing flows:
  - no pytest coverage found for watershed/hydro/hydrogeo analysis paths in `culvert_app/tasks/*.py`.
  - no pytest coverage found for core geospatial/model utilities in `culvert_app/utils/subroutine_*.py`.
  - practical effect: domain logic change risk is largely unmanaged by automated tests.

### 7.2 Error-handling style metrics (non-junk Python)

- bare `except:`: `25`
- `except Exception as ...`: `532`
- `print(...)`: `2,219`
- structured logger calls: `422`

Developer barrier: `8` tests for `~28,000` SLOC means a developer has no safety net for refactoring, and those tests are mostly infrastructure checks rather than model/data correctness checks. Any change beyond a trivial fix requires manual end-to-end testing through the browser UI. `25` bare `except:` blocks (which also catch `KeyboardInterrupt` and `SystemExit`) mask the real cause of failures — a developer debugging a production issue sees "Error" in logs but not what error or where. `2,219` print statements versus `422` structured logger calls mean log output cannot be filtered, searched, or alerted on by severity level. No CI gate means a developer can push broken code directly to production without any automated check.

### 7.3 CI gating

- Deployment workflow (`.github/workflows/deploy.yml`) runs direct deploy steps only.
- No test/lint/security gate in that workflow before deployment actions.

### 7.4 Download error-path semantics are flattened

- `get_download` raises specific HTTP errors (`403/404/500`) inside a broad `try` block:
  - `culvert_app/app.py:5250`
  - `culvert_app/app.py:5259`
  - `culvert_app/app.py:5284`
- A catch-all `except Exception` at the end re-raises generic `500`:
  - `culvert_app/app.py:5308-5310`

Operational effect:

- Distinct failure modes (for example "not found/expired" vs internal errors) are flattened into generic server errors, degrading client behavior, SRE triage, and alert quality.
- Download key cleanup occurs before `send_file` completion:
  - `culvert_app/app.py:5294-5297`
  - if file transfer fails after key deletion, user retry path is degraded.

## 8. Performance and scalability

### 8.1 Current nested delineation path is algorithmically expensive

In `culvert_app/utils/subroutine_nested_watershed_delineation.py`:

- per-point delineation loop in `nested_basin_delineation(...)` (`:811` onward)
- pairwise containment/overlap in `establish_nesting_hierarchy(...)` (`:967`, nested loop starts `:978`)
- this is effectively O(n^2) geometry interaction for hierarchy determination

### 8.2 Migration guide not yet integrated

Migration guide expects replacing Python hierarchy logic with Rust `UnnestBasins` sidecar workflow:

- guide: `/workdir/wepppy/docs/culvert-at-risk-integration/dev-package/weppcloud-wbt-unnest-basins-migration-guide.md`
- no `UnnestBasins`/`unnest_basins` invocation found in current code

The guide documents component speed improvements roughly in the `~20x` range for nested delineation/hierarchy segments; current codebase leaves that gain unrealized.

Developer barrier: the O(n^2) hierarchy path means iteration cycles are slow. A developer testing a change to delineation logic must wait for the full computation to complete — there is no fast-path or mock that bypasses the expensive geometry operations.

### 8.3 Runtime and serving topology constraints

- Gunicorn configured with single web worker:
  - `docker-compose.yml:41-43` sets `-w 1`
- RQ worker pool configured to `20` workers:
  - `docker-compose.yml:53`

This can create imbalance where HTTP serving bottlenecks independently from background throughput.

Additional scaling barrier in current real-time stack:

- App uses gevent WebSocket worker plus Flask-SocketIO message queue:
  - `docker-compose.yml:40`
  - `culvert_app/app.py:192-197`
- Sessions are Redis-backed (`Flask-Session`), which helps cross-worker auth/session continuity:
  - `culvert_app/app.py:227-231`
- But task-progress state is also kept in process-local memory (`active_tasks`), not shared store:
  - `culvert_app/app.py:96`
  - `culvert_app/app.py:905-923`
  - `culvert_app/app.py:5746-5749`

Operational consequence:

- Scaling web workers/replicas for Socket.IO typically requires sticky load-balancer affinity (or equivalent transport/session affinity) to keep polling/upgrade traffic coherent.
- Without strict state externalization, worker-local task state and sticky routing interact in non-obvious ways, increasing defect and outage risk during scale-out.

### 8.4 External call resilience and retry-control gaps

- Inventory of `requests.get/post` calls in reviewed Python: `14` total, `10` without explicit timeout.
- Timeout-missing examples:
  - `culvert_app/utils/subroutine_graphical_peak_discharge_Est.py:315`
  - `culvert_app/utils/subroutine_rational_method.py:87`
  - `culvert_app/utils/subroutine_determine_WS_characteristics.py:55`
  - `culvert_app/utils/subroutine_wetland_data_download_and_preprcoessing.py:46`
  - `culvert_app/utils/subroutine_USGS_Regression_Peak_flow_Stats.py:86`, `culvert_app/utils/subroutine_USGS_Regression_Peak_flow_Stats.py:103`, `culvert_app/utils/subroutine_USGS_Regression_Peak_flow_Stats.py:121`, `culvert_app/utils/subroutine_USGS_Regression_Peak_flow_Stats.py:139`, `culvert_app/utils/subroutine_USGS_Regression_Peak_flow_Stats.py:159`
  - `culvert_app/utils/subroutine_run_WEPP_model.py:1133`
- USGS regression flow includes `5` unbounded retry loops with no max-attempt ceiling:
  - `culvert_app/utils/subroutine_USGS_Regression_Peak_flow_Stats.py:84`
  - `culvert_app/utils/subroutine_USGS_Regression_Peak_flow_Stats.py:102`
  - `culvert_app/utils/subroutine_USGS_Regression_Peak_flow_Stats.py:120`
  - `culvert_app/utils/subroutine_USGS_Regression_Peak_flow_Stats.py:138`
  - `culvert_app/utils/subroutine_USGS_Regression_Peak_flow_Stats.py:158`
- Inconsistent download-memory behavior:
  - full-buffer writes via `response.content`:
    - `culvert_app/utils/subroutine_graphical_peak_discharge_Est.py:322`
    - `culvert_app/utils/subroutine_rational_method.py:93`
    - `culvert_app/utils/subroutine_determine_WS_characteristics.py:59`
    - `culvert_app/utils/subroutine_wetland_data_download_and_preprcoessing.py:50`
  - better streamed pattern exists but is not consistent:
    - `culvert_app/utils/subroutine_run_WEPP_model.py:1133`, `culvert_app/utils/subroutine_run_WEPP_model.py:1138`
  - timeout-aware pattern also exists in newer task code:
    - `culvert_app/tasks/submit_payload.py:202`
    - `culvert_app/tasks/wepp_cloud_integration_task.py:147`

### 8.5 Disk-capacity and back-pressure controls

- No disk preflight checks (`shutil.disk_usage`/equivalent) were found in reviewed app/task code.
- Large extraction/download/write flows proceed without explicit free-space guardrails.

### 8.6 Download archive path has artificial delay and poor large-directory scaling

The download packaging task includes explicit sleeps that are not practical at scale:

- `time.sleep(1)` for single-file copy flow:
  - `culvert_app/tasks/download_output_files_task.py:136`
- `time.sleep(0.2)` per file when more than 5 files are selected:
  - `culvert_app/tasks/download_output_files_task.py:162-163`
- `time.sleep(0.5)` at finalize:
  - `culvert_app/tasks/download_output_files_task.py:171`

For `N > 5` files, minimum artificial delay alone is approximately:

- `0.2 * N + 0.5` seconds (not including actual zip I/O and emit overhead)

Examples:

- `1,000` files: `~200.5s` artificial delay (~`3.3 min`)
- `5,000` files: `~1000.5s` artificial delay (~`16.7 min`)
- `9,000` files: `~1800.5s` artificial delay (~`30 min`) before real work/overhead

This collides with current background job timeout:

- download task enqueue timeout is `30m`:
  - `culvert_app/app.py:5218`

Additional scaling friction in the same path:

- Progress/state updates are emitted per file during zip assembly:
  - `culvert_app/tasks/download_output_files_task.py:152-156`
- No cap on selected file count in request payload:
  - `culvert_app/app.py:5199`
- Download state key is deterministic and overwritten per user/project/task:
  - `culvert_app/tasks/download_output_files_task.py:184`
- Download metadata is serialized with ad-hoc `str(...)` + `ast.literal_eval(...)` instead of stable JSON schema:
  - write: `culvert_app/tasks/download_output_files_task.py:185`
  - read/parse: `culvert_app/app.py:5266-5268`

Operational effect:

- Large directory/download selections can timeout or become non-responsive primarily due to synthetic delay and high progress-event churn, not just archive I/O cost.

Developer barrier: a developer investigating "why does download hang?" will spend time profiling I/O and network before discovering the root cause is `time.sleep(0.2)` called in a loop. The `ast.literal_eval` serialization pattern for download metadata is fragile — a developer changing the download info structure must ensure `str()` and `ast.literal_eval()` round-trip correctly, with no schema or test to validate it.

## 9. DevOps and deployment

- Deploy workflow is simple and direct (`git pull` + `docker compose down && up -d --build`).
- No explicit rollback/health-gate step in workflow.
- No test/security scan stage in shown deployment pipeline.
- Compose uses mounted source directories in runtime containers (good for dev velocity, but raises drift/immutability concerns in stricter production patterns).

Developer barrier: no rollback step means a developer's broken deploy requires manual SSH intervention to recover (`git revert` + rebuild). No health gate means the deploy succeeds even if the app fails to start. A developer cannot confidently deploy a change without watching logs manually to confirm it came up correctly.

### 9.1 Container least-privilege and resource-limits gaps

- Dockerfile has no `USER` directive in reviewed build stage:
  - `Dockerfile:1`, `Dockerfile:88`
- App and worker services run without explicit non-root user override:
  - `docker-compose.yml:2`, `docker-compose.yml:49`
- Only Caddy is explicitly non-root:
  - `docker-compose.yml:83`
- CPU/memory limits are not declared for app/worker services (`deploy.resources`, `mem_limit`, `cpus` absent in reviewed compose file).

### 9.2 Socket.IO scale-out and sticky-balancer complexity

This architecture is currently optimized for single-web-worker simplicity; scaling it horizontally introduces non-trivial operational and debugging complexity.

- Current stack is gevent + Flask-SocketIO + Redis message queue + Redis Flask-Session:
  - `docker-compose.yml:40-43`
  - `culvert_app/app.py:192-197`
  - `culvert_app/app.py:227-231`
- This setup can broadcast across workers, but real-time connection handling still requires careful load-balancer behavior for sticky affinity and upgrade continuity.
- The app also keeps task progress in worker-local Python memory (`active_tasks`), so behavior diverges by worker if requests are not routed consistently.

Developer/debugging impact:

- Reproducing bugs becomes non-deterministic because symptoms depend on which worker handled HTTP route calls vs Socket.IO events.
- Troubleshooting requires cross-layer correlation (request ID + worker/container ID + Socket.IO SID + RQ job ID), which is not fully standardized in current logs.
- Rolling deploys and reconnect storms are harder to reason about when stickiness and worker-local state are both in play.

### 9.3 Issue `#98`: app-coupled workers and monkey-patch risk

GitHub issue `#98` ("Use socketio.RedisManager instead of app_context") was opened on `2025-09-21` and is still open (as of this audit date).

Current coupling pattern in code:

- Task workers import runtime objects directly from `app`:
  - `culvert_app/tasks/hydro_vuln_analysis_task.py:14`
  - `culvert_app/tasks/watershed_delineation_task.py:11`
  - `culvert_app/tasks/download_output_files_task.py:10`
- `app.py` conditionally applies global gevent monkey patching at import time:
  - `culvert_app/app.py:9-13`
- Web container explicitly sets gevent mode:
  - `docker-compose.yml:17`

Why monkey patching RQ workers is bad practice:

- Global side effects: `monkey.patch_all()` mutates standard-library behavior process-wide, so worker semantics change in non-local ways.
- Hidden coupling: worker behavior becomes dependent on web runtime env vars and import order instead of explicit worker bootstrap.
- Debugging complexity: the same task can behave differently in patched vs non-patched workers, making failures hard to reproduce.
- Library compatibility risk: many geospatial/native pipelines are blocking and not designed for cooperative monkey-patched I/O models.
- Operational fragility: scaling, rollback, and incident response are harder when worker runtime behavior can change via configuration drift.

Implementation gotcha captured in `#98` discussion:

- If moving worker emits to `socketio.RedisManager`/message-queue-only publishing, the channel/topic naming must be explicitly aligned with the Flask-SocketIO server configuration, otherwise worker emits appear to "succeed" but clients receive nothing.

Note: current compose does not set `SOCKETIO_ASYNC_MODE=gevent` on the `rq-worker` service, which reduces immediate exposure. However, the app-coupled import design keeps this as a high-risk footgun for future config changes.

## 10. Data architecture

- DB usage is minimal and identity-centric (single `User` model).
- Project/user operational state is file-system centric under `instance/user_data`.
- Registration/activation flow also writes PII to CSV:
  - `culvert_app/app.py:1214`, `culvert_app/app.py:1247`

Implications:

Developer barrier: a developer cannot answer "what projects exist, what state are they in, and what outputs did they produce" without walking the filesystem. There is no queryable run-state table, no output manifest, and no lineage record. Debugging a failed user run means SSH-ing to the server, navigating `instance/user_data/{user_id}_outputs/{project}/`, and manually inspecting which files exist. PII written to CSV alongside project data means a developer must also be careful not to accidentally expose user records during debugging.

### 10.1 Shapefile-centric contracts create schema and integration drag

- Watershed and WEPP integration tasks emit and consume many `.shp` artifacts as internal pipeline contracts:
  - `culvert_app/tasks/watershed_delineation_task.py:270`, `culvert_app/tasks/watershed_delineation_task.py:287`, `culvert_app/tasks/watershed_delineation_task.py:292`
  - `culvert_app/tasks/wepp_cloud_integration_task.py:377`, `culvert_app/tasks/wepp_cloud_integration_task.py:378`
- Frontend guidance and upload handling are hard-wired to shapefile component packaging:
  - `culvert_app/static/js/ws_delin.js:3048`, `culvert_app/static/js/ws_delin.js:3195`, `culvert_app/static/js/ws_delin.js:3257`
- Migration guidance already documents shapefile-field truncation compatibility aliases due to dBase 10-character limits:
  - `/workdir/wepppy/docs/culvert-at-risk-integration/dev-package/weppcloud-wbt-unnest-basins-migration-guide.md:56`
  - `/workdir/wepppy/docs/culvert-at-risk-integration/dev-package/weppcloud-wbt-unnest-basins-migration-guide.md:57`
  - `/workdir/wepppy/docs/culvert-at-risk-integration/dev-package/weppcloud-wbt-unnest-basins-migration-guide.md:59`
  - `/workdir/wepppy/docs/culvert-at-risk-integration/dev-package/weppcloud-wbt-unnest-basins-migration-guide.md:157`

Operational effect on the WEPP `.parquet -> shapefile -> Folium` path:

- schema names are shortened/aliased (for example `parent_wat`, `child_coun`, `hierarchy_`), then remapped later
- field-level traceability drops across boundaries, increasing debugging and search cost
- conversion overhead grows and schema fidelity is reduced versus a canonical GeoParquet/GeoPackage contract

Developer barrier: the dBase 10-character column name limit means a developer adding a new field to the WEPP pipeline must invent a truncated alias, document it somewhere, and ensure all downstream consumers use the alias consistently. A developer debugging a field mismatch must mentally map between full names and their truncated forms across file boundaries.

## 11. Frontend and visualization

- Frontend logic is concentrated in very large JS modules (`hydrovuln.js`, `hydrogeovuln.js`, `ws_delin.js`).
- Folium map HTML is injected with `|safe` in templates:
  - `culvert_app/templates/ws_deln.html:849`
  - `culvert_app/templates/hydro_vuln_analysis.html:1562`
  - `culvert_app/templates/hydrogeo_vuln.html:1697`
- Additional iframe-based embedding and Blob HTML map loading in dashboard:
  - `culvert_app/static/js/analysis_dashboard.js:592-613`

Developer barrier: Folium generates self-contained HTML blobs server-side and injects them via `|safe` into Jinja templates. A developer cannot add a map interaction (click handler, dynamic layer toggle, linked chart) without modifying the Python Folium generation code, the Jinja template, and the JS that loads the blob. Map rendering cannot be tested independently from the backend — it requires a running Flask app and a browser. The `4,240`-line `hydrovuln.js` file means any frontend change risks regressions in unrelated form/map behavior with no test coverage to catch it.

## 12. Documentation

- Repo has baseline docs (`README.md`, data formatting guidelines, manual docs), but technical-operational documentation appears thin for:
  - architecture boundaries
  - model plugin contract/interface
  - security hardening standards
  - runbook for incident/rollback
- Root README is high-level and does not document internal architecture, lifecycle, or contribution/testing workflow in depth.

### 12.1 Accuracy check: README and WEPP-related docs

Material documentation drift. 

- `README.md` has a broken image reference:
  - `README.md:7` references `static/images/Pasted image.png`, but that asset is not present under `static/images` or `culvert_app/static/images`.
- `Docker_integration.md` is substantially stale relative to current code/deployment:
  - claims WEPP is run via Wine (`Docker_integration.md:10`, `Docker_integration.md:154`, `Docker_integration.md:202`) but current WEPP local execution is direct subprocess of `wepp_path` (`culvert_app/utils/subroutine_run_WEPP_model.py:1503-1505`) and `Dockerfile` has no Wine install (`Dockerfile:11-39`).
  - shows outdated repo structure rooted at `/SouravDSGit/Culvert-web-app_main/` with top-level `app.py/models/utils` (`Docker_integration.md:18-32`), while active app code is under `culvert_app/`.
  - states app on `localhost:5000` (`Docker_integration.md:88`), but active compose uses Caddy on `80/443` (`docker-compose.yml:87-89`) and nocaddy maps host `8732 -> 5000` (`docker-compose.nocaddy.yml:8`).
  - documents fixed memory/CPU allocations (`Docker_integration.md:39-40`, `Docker_integration.md:179-182`, `Docker_integration.md:201`), but current compose does not set container memory/CPU limits.
- `WEPP_steps.md` is also stale/inaccurate in key implementation details:
  - repeatedly states WEPP runs through Wine (`WEPP_steps.md:3`, `WEPP_steps.md:11`, `WEPP_steps.md:98-101`, `WEPP_steps.md:181`) and relies on `WEPP_PATH`/`WINE_PATH` env vars (`WEPP_steps.md:32-33`), which does not match current implementation.
  - shows fixed `ThreadPoolExecutor(max_workers=4)` pattern (`WEPP_steps.md:60`) while current code computes worker count dynamically (`culvert_app/utils/subroutine_run_WEPP_model.py:1896-1900`).
  - implies a direct `process_watershed_for_wepp` integration path (`Docker_integration.md:112`), but the active hydro-geo flow calls WEPP Cloud integration (`culvert_app/tasks/hydrogeo_vuln_analysis_task.py:499-512`, `culvert_app/tasks/wepp_cloud_integration_task.py:90-99`).
- `Guidelines_for_input_data_formatting.md` is mixed (partly accurate, partly overstated):
  - accurate constraints: boundary area limit `120000` ha and pour-point limit `300` are enforced server-side (`culvert_app/app.py:2548`, `culvert_app/app.py:2781`, `culvert_app/app.py:3595`).
  - stated boundary ZIP size cap (`25 MB`) is enforced client-side in JS (`culvert_app/static/js/ws_delin.js:1687-1689`) but no backend `MAX_CONTENT_LENGTH` enforcement is configured.
  - several sample links are placeholders (`Guidelines_for_input_data_formatting.md:23`, `Guidelines_for_input_data_formatting.md:136`, `Guidelines_for_input_data_formatting.md:155`, `Guidelines_for_input_data_formatting.md:182`, `Guidelines_for_input_data_formatting.md:202`).
- Manual docs are uneven for operations/engineering use:
  - `Manual/rational_method.md:1-14` is a small Mermaid snippet, not a full operator/developer manual.
  - `Manual/Phase2/lit_review.md` duplicates major section blocks (`Manual/Phase2/lit_review.md:1`, `Manual/Phase2/lit_review.md:35`) and does not serve as implementation/runbook documentation.

Operational effect:

- New engineer/devops onboarding is slowed by contradictory WEPP runtime guidance.
- Troubleshooting steps can send responders to wrong paths/ports/runtime assumptions.
- Documentation cannot be trusted as a source of operational truth without code verification.

Developer barrier: a new developer's first hours are spent discovering the docs are wrong. `Docker_integration.md` says WEPP uses Wine — it doesn't. `WEPP_steps.md` says `ThreadPoolExecutor(max_workers=4)` — the code computes it dynamically. The README shows a broken image. A developer following the setup guide will hit incorrect ports, wrong paths, and missing dependencies. Every doc must be verified against code before acting on it, which defeats the purpose of having docs.

## Barriers to scaling and adding models (ranked)

1. Known unpatched critical/high security vulnerabilities in file and input handling.
2. Concurrency/race-condition exposure in shared files and global task state under `20` workers.
3. CSRF/cross-origin control gaps (`fetch` POSTs without CSRF tokens + Socket.IO `cors_allowed_origins="*"`).
4. Session/cookie hardening, rate-limiting, and browser security-header gaps.
5. Monolithic route/controller design (`app.py`) with high change concentration.
6. High-complexity geospatial/model routines with low maintainability index.
7. Shapefile/ZIP-centric and file-path-centric contracts with limited typed schemas.
8. External-call resilience gaps (timeouts, unbounded retries, in-memory download writes).
9. Real-time serving architecture is hard to scale safely (`gevent` + Socket.IO + worker-local task state), requiring sticky balancing and stronger observability discipline.
10. Container least-privilege/resource-limit gaps in deployment baseline.
11. Limited/fragile test suite and weak CI gating.
12. High duplication and retained legacy/junk logic increasing change risk.
13. Performance ceiling from current Python nested hierarchy path versus available Rust-sidecar migration.
14. Frontend map embedding architecture that is hard to compose with new model-specific interactions.

## Final assessment for sponsor conversation

Codebase maturity currently dominates both operational risk and model scaling risk. Infrastructure tuning can help throughput, but without targeted codebase hardening/modularization, each new model integration will remain high-cost and high-regression-risk.
