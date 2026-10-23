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
| Full Python suite | Running; package closure pending |

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
was introduced. Full regression and final review closure are required before
closing the package.
