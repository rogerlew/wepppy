# Builder run-page timeout: repeated capability config reads

Resolved on the development stack, 2026-09-10. User reported a 504 after creating
`fair-division` and when opening `/weppcloud/runs/fair-division/config/`.
The builder API logged successful 201 creation and the project's config/manifest
and NoDb files existed. The failure was downstream page rendering.

## Evidence and fix

A direct invocation of `_build_runs0_context` took 30.65 seconds. Timed stack
traces repeatedly found `config_get_list` → `_configparser` →
`load_project_config` inside capability graph traversal. Every axis/relation
field reparsed and revalidated the entire flattened project configuration.
The new postfire visibility check added another full traversal to this existing
read amplification.

`project_config_capabilities.py` now observes the NoDb owner's validated parser
once per `capability_authority`/`resolve_run_capability_authority` call. The same
observation provides parser options, list/scalar values and project-config status.
There is no persistent or cross-request cache. Custom NoDb getters and other protocol implementations
retain their existing getters. No authority validation, manifest checks, amendment
recovery, locale interpretation or user selections were removed or changed.
This restores usable rendering under the existing project-owned config and run
UI contracts; it does not introduce a new authority or fallback policy.

After the fix, context construction took 3.15 seconds and template rendering
1.21 seconds in a fresh process. After reloading development web workers,
an authenticated Chromium request to the exact external URL returned HTTP 200
and page title `fair-division` in 2.70 seconds. The project was not recreated.
No config, manifest or NoDb schema mutation was needed. The same fix was then
loaded into development rq-engine; model workers were not restarted.

## Regression evidence

`wctl run-pytest tests/nodb/test_project_config_capabilities.py
tests/nodb/test_locale_capability_authority.py
tests/nodb/test_project_config_reader_foundation.py
tests/nodb/test_landuse_build_event_contracts.py
tests/weppcloud/routes/test_run_0_builder_maturity.py --maxfail=1`:
**169 passed**. New tests use actual NoDb/config loading, compare the entire
resolved authority to the existing parser implementation, assert one reader call,
and verify that a malformed replacement config is detected by the next call.

The capability module stub check, test-stub completeness, broad-exception gate
and documentation lint passed. The operator stopped full-suite testing. The second sweep had already ended
with 5,056 passed, 60 skipped and a fork callback failure
(`test_invalid_or_legacy_callback_cannot_publish[missing_lineage]`); that failure
has not been attributed or investigated as part of this repair. No JavaScript, queue wiring,
scientific parameters, permissions, proxy timeouts or authentication were changed.
A browser automation issue initially clicked Login before CAPTCHA completion;
those verification-screen responses were not counted as project-page evidence.

The first full sweep caught a controller test using custom config getters. The
optimization now applies only to the standard NoDb getter implementations; an
explicit regression test preserves custom getter authority without requiring a
disk parser. The affected landuse build tests pass in the focused run.
