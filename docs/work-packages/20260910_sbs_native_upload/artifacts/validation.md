# Validation

Contract checkpoint `328db92dd` precedes native-only/UI implementation. The
operator excluded the full Python suite.

- `python_tests.log`: 78 passed, including missing/failing native APIs, failed
  cache entries, NoData/palette/orientation, metadata truncation and batch failure.
- `rust_tests.log`: 4 passed. Companion native source filters noninteger/nonfinite
  NoData metadata instead of masking valid integer classes by truncation.
- `native_parity.log`: final Wallow output equals the frozen prior Python output
  pixel-for-pixel, with identical projection, geometry and NoData. Export takes
  0.57 s versus 54.09 s. The old installed native artifact failed mask parity;
  it was replaced only after rebuilding and verifying the corrected candidate.
- Final JavaScript suite: 110 suites / 852 tests passed, including request-order
  races, HTTP200 JSON errors, filename text safety and hostile gateway HTML.
- `security_browser_probe.log`: real Chromium, no active nodes, scripts,
  custom-element execution, outbound requests or navigation from gateway HTML;
  safe retained-error rendering and retry recovery.
- Native stubtest, test-stub completeness, ESLint and broad-exception gate pass.
  Bundle rebuilt with the canonical builder. The builder's `[[` interpolation
  syntax required spaces between the nested JavaScript array brackets.
- Native install provenance: `native_refresh.json`; rq-engine restart after final
  atomic binary replacement in `development_reload.log`. Web workers also reloaded.

## Runtime acceptance

`proxy_browser.log` passes on API-created Builder project lawless-challah:
Wallow upload HTTP200 in 5.597 s; accepted filename, rendered classification
table, map image URL, injected HTML504 in Details, preserved Summary, blank
hint, successful retry and persisted filename/table after reload. See
`gateway_details.png`, `upload_success.png` and the reproducible browser script.
The final run also passed three additional consecutive real uploads after recovery.
The fair-division input map was not overwritten for testing.

## Operator compatibility

Deploy WEPPpy together with the corrected `wepppyo3.sbs_map` artifact. A stale
extension may import yet classify masks incorrectly; import-only checks are
insufficient. Repeat real mask parity and an authenticated upload under the
serving identity/mounts before rollout. This package refreshed only the shared
development release artifact, not another host or the production fleet.

The Python raster fallback and duplicate raster loops are gone. Explicit custom
palette and scalar class-label helpers remain. Failed native operations return
errors through the existing upload boundary. No proxy timeout was increased.

## HTTP admission correction

Repeated smoke attempts exposed HTTP409 `Submission lock expired` before raster
validation. `admission_failure_stack.log` identifies a copied previous-request
context at `parent_lease.checkpoint()`, referring to an already-released Redis
lock. Each HTTP request now explicitly acquires fresh lifecycle ownership;
nested operations still inherit the current lease and fail closed on lost ownership.
No timeout, authorization or queue policy changed. Boundary diagnostics record
run ID and stack without request headers/body or tokens.

`admission_tests.log`: 10 passed, including copied-context reuse through the
actual middleware, competing owner rejection and nested lost-parent rejection.
The final repeated proxy gate and `admission_stubtest.log` pass after the correction. The companion stub
check also exposed a missing `on_job_id` annotation from the earlier M1 runtime
change; the stub now matches that existing API.
