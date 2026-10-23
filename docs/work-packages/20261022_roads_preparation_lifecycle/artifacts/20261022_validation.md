# Roads lifecycle validation

Contract checkpoint: `1270c209f`. Local forest Compose environment; model and HTTP
probes ran as uid 1000/gid 993 against isolated validation projects. Production and
original `/wc1/runs/cl/clogging-starch` were not modified.

## Automated gates

| Gate | Result |
| --- | --- |
| Roads controller | 47 passed |
| Reports, routes and archive focused suites | 248 passed |
| Lifecycle, D-Tale and module focused suites | 80 passed |
| Browse files API | 95 passed |
| Final lifecycle regressions | 17 passed |
| Final query server/MCP regressions | 75 passed |
| Final D-Tale regressions | 20 passed |
| Frontend lint | Passed |
| Full frontend tests | 119 suites, 990 tests passed |
| Test stub completeness | Passed |
| Changed broad-exception enforcement against checkpoint | Passed, net delta zero |
| Documentation lint and git whitespace checks | Passed |
| Broad Python coverage | 11,115 unique passes, 126 unique skips across retained runs; see limits below |

Canonical commands: `wctl run-pytest <suite>`, `wctl run-npm lint`,
`wctl run-npm test`, `wctl check-test-stubs`, `wctl doc-lint --path <document>`.
The full suite uses `wctl exec weppcloud env` with `PYTHONPATH=/workdir/wepppy`
and `PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers`,
then `/opt/venv/bin/pytest tests --maxfail=1`. Final query/preview additions are
also covered by the focused suites above because collection preceded those edits.
The generated controller bundle was rebuilt with the canonical build script.

## Generated artifacts and live consumers

- [Real model receipt](20261022_real_run_validation.json): two full Roads runs
  separated by preparation; 34 profile rows; 911 baseline files and 46 original
  project Parquets unchanged. Independent numeric readback is in the correctness review.
- [Canonical archive receipt](20261022_archive_validation.json): real filesystem
  archive/restore, with isolated RQ/status/cache callbacks; complete restored
  resources and history, lock excluded from ZIP and inode preserved on restore.
- [Seven-reader HTTP receipt](20261022_http_validation.json): download, CSV,
  schema, metadata, browse, GL Dashboard and query return 200/current,
  409/writer-busy, 409/reprepared and 200/fresh full run. CSV/query each return
  34 rows. Explicit historical download and actual Chromium browse succeed.
- [Live preview receipt](20261022_dtale_http_validation.json): actual browse to
  separate D-Tale service launch and existing grid reads reject busy/reprepared
  state and recover after a full fresh Roads run.
- [Discovery/report receipt](20261022_discovery_validation.json): live catalog,
  query console and run info use no-store; busy discovery omits current Roads.
  Actual authenticated loss summary renders through forest HTTPS ingress and
  rejects a writer conflict. Login uses the existing dev-agent account and normal
  CAP flow; credentials, tokens and session cookies are not retained.

Executable validation scripts are adjacent to these receipts. Synthetic fixture
receipts serve consumer unit tests only; they are not the model execution evidence.
Independent security probes cover restrictive retention, stale controllers,
aliases, derived previews, response lifetime and failed readonly restore.

## Completion limits

This evidence supports local environment validation. It does not claim deployment,
repair of original UM1, or implementation of the future GL detachment choropleth.
No new runtime service, dependency, durable identity or compatibility migration
was introduced. The final regression tail passed. Independent correctness and security reviews
accept the bounded restarts with the limits below.

## Maintainability observation

Post-commit observability against `1270c209f` analyzed 42 changed source/test files.
The new lifecycle helper remains within green size/function bands (378 source
lines, longest function 57 lines). Existing large producer/consumer modules grow
slightly to call admission/retention and translate explicit errors; Roads grows
32 source lines and the longest existing producer grows seven lines. This is
intentional integration into existing boundaries, avoiding an unrelated rewrite.
JavaScript complexity is unchanged in the Roads controller. Python cyclomatic
complexity was unavailable because radon is not installed in the host tooling;
this observe-only result is not a correctness gate. Report outputs stayed in
`/tmp/roads-lifecycle-quality.{json,md}`, leaving unrelated tracked reports intact.

## Broad-run interruption and continuation

The initial invocation stopped at `test_create_mcp_app` after 6,029 passed and 56
skipped (2350.77 seconds). During that long run, final discovery-header integration
added `discovery_headers`; the process had already imported the previous
`feature_access` module. A test then reloaded the newer router and raised ImportError
for that new symbol. This is a mixed-revision process, not a passing full-suite run.

Runtime is now frozen at `e4d28c9ad`. The retained `roads_resume.py` selector
re-collects all tests and selects the failed node inclusively plus every later node.
Continuation collected 11,240 items: 6,086 deselected, one collection skip, 5,154
selected. Use the same wctl environment with `PYTHONPATH=/tmp:/workdir/wepppy`, copy
the retained selector to `/tmp/roads_resume.py` inside the container, and append
`-p roads_resume` to pytest. No test result is fabricated or marked passed by this
selector. The final query 75 and D-Tale 20 focused passes cover edits made after
initial collection, including the two added pre-boundary preview alias cases.

This is segmented regression evidence. It does not establish a single clean
invocation on the final revision or cross-boundary test-order isolation. Both
independent reviewers accepted this bounded adaptation.

The first continuation passed 4,774 tests and skipped 70 runtime cases before an
unrelated OpenET admission test reached a real Redis client captured at import
before the autouse stub. Its isolated 52-case file passed. The test now explicitly
binds the existing Redis factory and a temporary lifecycle-lock directory; real
JWT and SQL membership checks are unchanged. Both reviewers approved this test-only
isolation fix. Production code remained frozen.

The final continuation set `ROADS_RESUME_NODE` to
`tests/weppcloud/test_feature_access.py::test_openet_signed_token_live_membership_admission`.
It collected 11,240, deselected 10,930 and selected 310; all 310 passed in 68.86
seconds. Counts reconcile without gaps: 6,029 + 4,774 + 310 + two added pre-boundary
D-Tale cases = **11,115 unique passing tests**. Runtime skips 55 + 70 plus one
collection skip = **126 unique skips**, counted once across runs. The
[regression receipt](20261022_regression_validation.json) retains exact summaries
and log hashes. There is no remaining failing node; the single-process/cross-boundary
coverage limitations above remain explicit.
