# Run Page Title Implementation Correctness Review

Date: 2026-08-28
Amendment: PC-13 / WP12D-20260828-7
Ratified checkpoint: `8a15b963c26a4d9201e238610bfdbbf1734c77a6`
Reviewed candidate: uncommitted implementation on `feature/project-owned-config` at HEAD `5f59ce5d01c6302bd184b058fe1197b74c3946cc`
Reviewer: independent implementation correctness review

## Verdict

**READY** — High: 0, Medium: 0, Low: 0.

The bounded implementation conforms to the ratified title-lifetime contract. The
run page title is the exact route-resolved `runid` at initial render and no
project-name or scenario operation mutates it afterwards. No backend, security,
authorization, persistence, or run-data behavior changed.

## Conformance evidence

- `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm` renders the title block
  as `{{ runid }}` without configuration, project-name, scenario, locale,
  nested-run, PUP, or capability metadata.
- The existing `run_0` route context supplies `runid` from the route parameter.
  The implementation does not substitute `current_runid` or another nested/PUP
  identity.
- `wepppy/weppcloud/controllers_js/project.js` removes only the two title-update
  helpers and their successful save-path calls. The existing POST transports,
  input synchronization, `project:name:updated` and
  `project:scenario:updated` events, and success notifications remain intact.
- Source and rebuilt `wepppy/weppcloud/static/js/controllers-gl.js` contain no
  `document.title` assignment or removed title-update helper. The generated
  bundle retains the project-name and scenario event paths.
- `tests/weppcloud/routes/test_pure_controls_render.py` renders the actual title
  block and proves exact route-run identity across missing and populated
  metadata, including a differing nested/PUP current-run identity. A separate
  case proves Jinja autoescape for HTML-significant route identifiers.
- `wepppy/weppcloud/controllers_js/__tests__/project.test.js` proves populated
  and cleared project names plus populated and cleared scenarios leave the base
  title unchanged. Each case also asserts the request payload, field state,
  emitted event payload, and exact success notification.
- `wepppy/weppcloud/controllers_js/README.md` records the same title ownership
  and lifetime rule without broadening controller responsibilities.

## Finding disposition

An initial Medium test-evidence gap was identified during review: the new
clear-name and scenario cases did not directly assert their event payloads and
notifications. The final candidate closes that gap with exact assertions for
the Untitled name notification, both scenario notifications, and the associated
event payloads. The focused Project suite remains green. No unresolved finding
remains.

## Scope review

Against the ratified checkpoint, the implementation files are limited to:

- `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
- `wepppy/weppcloud/controllers_js/project.js`
- `wepppy/weppcloud/controllers_js/__tests__/project.test.js`
- `wepppy/weppcloud/controllers_js/README.md`
- `tests/weppcloud/routes/test_pure_controls_render.py`

The active ExecPlan and tracker are the only additional tracked work-package
files in the scoped diff. The ignored runtime controller bundle was rebuilt and
matches the reviewed source. Prerecorded unrelated dirty paths were excluded
from this review. No backend route logic, NoDb/RQ behavior, authentication,
authorization, schema, or stored data was changed.

## Validation evidence

Independently rerun during this review:

- `wctl run-npm test -- project`: 2 suites, 54 tests passed.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k runs0_title --maxfail=1`:
  3 passed, 155 deselected.
- `wctl run-npm lint`: passed.
- Scoped `git diff --check`: passed.

Package-provided broader evidence:

- Full frontend: 107 suites, 820 tests passed.
- Full Pure controls: 158 tests passed.
- Broader WEPPcloud routes: 1,070 passed with 30 warnings in 74.28 seconds.
- Repository-wide `wctl run-pytest tests --maxfail=1`: 7,272 passed, 63 skipped,
  and 2,740 warnings in 771.24 seconds.

## Residual risk

Residual risk is limited to integration behavior outside the reviewed title and
Project-controller surfaces. The broader WEPPcloud routes and repository-wide
Python gates are green. The active ExecPlan/tracker should record the final gate
and review disposition; this bookkeeping does not require a production-code
change in this amendment.
