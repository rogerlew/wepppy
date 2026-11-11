# Focused dependency validation map - M1/M2 preparation

**Reviewer**: independent correctness reviewer  
**Date**: 2026-11-11 UTC  
**Source**: `2041fb8e267de3a1572d9fb4f4a62e725b75cc91`, local worktree  
**Status**: read-only source/test assessment; no tests or dependencies changed,
no validation run, and no advisory disposition made by this review.

Use this map only after direct baseline-image inventory identifies an applicable
finding and the actual proposed version change. Development-image findings do
not establish M1 exposure or authorize a version change. The current requirements
already pin Authlib 1.6.12, cryptography 46.0.7, urllib3 2.7.0, Pillow 12.2.0,
bleach 6.1.0, mistune 3.2.1, nbconvert 7.17.1, GDAL 3.10.2, and Fiona 1.10.1.
Installed versions, transitive consumers and native libraries remain image facts.

## Authentication and cryptography

`wepppy/weppcloud/utils/oauth.py::ensure_oauth_client` constructs the real
Authlib Flask client. `_security/oauth.py` uses its authorization redirect,
token exchange and user-info request, then applies application identity/email
and login rules.

Reuse these focused suites through `wctl run-pytest`:

- `tests/weppcloud/routes/test_security_oauth_routes.py`
- `tests/weppcloud/routes/test_security_oauth_callback.py`
- `tests/weppcloud/test_auth_remember_cookie.py`
- `tests/weppcloud/routes/test_security_auth_forms.py`
- `tests/weppcloud/test_auth_tokens.py`

The OAuth tests cover application success/redirects, session PKCE presence,
disabled providers, provider cancellation, failed token/user-info requests,
malformed responses, missing identity and unverified email. However,
`ensure_oauth_client` is replaced with dummy clients, and successful callbacks
also replace identity linking/login. They do **not** exercise Authlib's actual
state validation, token transport, metadata/JWK parsing or signature checks.
An Authlib upgrade needs a bounded real-client test using a local provider fixture:
normal flow plus state mismatch/replay, PKCE handling, and invalid signed claims
for the provider configuration actually used. Mock unrelated persistence if
necessary, but keep the upgraded Authlib path real.

Remember-cookie tests use real Flask-Login issuance/restoration and cover invalid
cookies, mismatched identity, logout and identity rotation. Form tests cover
rendered escaping and real CSRF-before-CAP rejection. Neither proves a real OAuth
provider exchange or an ordinary password-login round trip by itself.

The service JWT code in `wepppy/weppcloud/utils/auth_tokens.py` uses owned stdlib
HMAC/hashlib, not cryptography. Its real audience/signature/expiry/rotation tests
are useful regression coverage but cannot qualify a cryptography upgrade. No
direct cryptography import was found in the searched application Python sources.
Inventory actual transitive consumers in the candidate, then exercise the
relevant Authlib signing/verification or other confirmed consumer with real
valid/invalid key material. An import-only check is insufficient.

## HTTP transport

urllib3 is reached through Requests across OAuth, SSURGO, climate acquisition,
and WEPPcloudR control-plane clients. Reuse:

- `tests/soils/test_ssurgo_request_errors.py`
- `tests/climates/gridmet/test_download_clients.py`
- `tests/climates/prism/test_bulk_client.py`
- the OAuth suites above for application error translation.

These provide useful timeout/SSL-error translation, redirect rejection,
retry/permanent-status distinctions, bounded bodies, malformed/truncated data,
and atomic artifact publication coverage. SSURGO injects `SSLError`/`Timeout`;
gridMET injects response/transport doubles; PRISM supplies fake sessions or
providers. They do not prove urllib3 certificate verification, redirect handling,
socket timeout, framing, or decoding behavior.

For an applicable urllib3 change, add only the missing transport cases implicated
by the advisory/current call sites using local HTTP/TLS fixtures and real
Requests: trusted certificate succeeds; untrusted or hostname-mismatched
certificate fails; timeout, redirect and malformed-response cases preserve the
application contract. Do not disable TLS verification to make tests pass.
`tests/rq/test_webhook_http.py` has real socket/child checks, but its owned
stdlib transport is not urllib3 coverage.

## Pillow and parser/report packages

The direct Pillow import found is the static icon developer script
`wepppy/weppcloud/static/open-iconic/png/recolor.py`. This does not establish
runtime nonreachability: matplotlib and other installed consumers may use Pillow.
PATH-CE imports matplotlib and emits figures through Quarto/Jupyter.

`tests/nodb/mods/path_ce/test_report_render_integration.py::test_real_render_end_to_end`
executes the actual Quarto render against committed representative inputs. It
reads generated HTML, local assets and exported CSV values, comparing the report
calculation with the job result. Run it in the candidate with Quarto available;
its module-level skip otherwise leaves this boundary unverified. The companion
`test_sweep_columns_parse_per_browser_contract` mocks the renderer and does not
replace the real test.

No direct application imports of bleach, mistune or nbconvert were found in the
searched Python sources, and no package-specific hostile-input suite was found.
Usersum Markdown rendering uses `cmarkgfm`, so Usersum route tests are not evidence
for those three libraries. The real PATH render is a normal-output compatibility
check, not proof that all three libraries are invoked or that hostile Markdown,
HTML, notebook output or images are safely handled.

Before changing these packages, map the installed Jupyter/Quarto/notebook
dependency graph and the exact advisory operation. If reachable, exercise the
actual converter/sanitizer with a normal control and the relevant retained
hostile-input corpus; parse resulting output under the current application
contract. Do not assume Markdown conversion sanitizes HTML or invent a new
sanitization policy to satisfy a library change. For a Pillow decoder finding,
first establish accepted image sources/formats, then use representative valid
and malformed images at that consumer rather than an unrelated import test.

## GDAL/Fiona/native boundary

The common Dockerfile installs system GDAL, pins Python GDAL, and explicitly
rebuilds Fiona 1.10.1 from source with `/usr/bin/gdal-config`. Preserve that
pairing unless a separately reviewed native migration is needed. The shape
converter's worker opens shapefiles through real Fiona/GDAL with a driver
allowlist; many raster/export consumers import `osgeo` directly.

Reuse these direct artifact suites through `wctl run-pytest`:

- `tests/shape_converter/unit/test_convert_endpoint.py`
- `tests/shape_converter/integration/test_convert_api.py`
- `tests/all_your_base/geo/test_vrt.py`
- `tests/all_your_base/geo/test_raster_stacker.py`
- `tests/nodb/mods/test_features_export_openfilegdb.py`

The shape tests construct real shapefile bytes and exercise conversion through
the parser worker: point/line/polygon success, GeoJSON/GeoParquet outputs, missing
or invalid CRS, corrupt geometry, traversal and metadata-entity inputs. Some
error/resource tests substitute subprocesses or converters, and the test of
Fiona egress-option forwarding mocks `fiona.Env/open`; those checks alone do not
prove native network containment.

VRT tests create/open real GDAL rasters and assert windows, dimensions and
geotransforms. Raster-stacker crosses Rasterio/GDAL and reads back GeoTIFF values.
`test_real_openfilegdb_conversion_preserves_representative_values` invokes the
real exporter and reopens both directory and ZIP outputs, checking geometry,
large numeric values, empty layers and null attributes. Its capability-based
skip must be counted as an acceptance gap if that export is supported by the
candidate. Its neighboring failure tests mock the conversion subprocess.

After a native change, additionally retain candidate readback of `gdal-config
--version`, `gdal.VersionInfo()`, Fiona's linked GDAL version, Rasterio's linked
GDAL version and relevant shared-library paths. Successful imports alone cannot
prove ABI parity or stable coordinates/nodata/schema. Select one existing
representative run/export workflow under production-equivalent UID/GID/mounts
when affected; preserve output semantics and owned native components.

## Acceptance limits

The suggested focused suites are a starting set, not a substitute for the exact
full pytest/npm gates or an exhaustive reachability assessment. Record actual
test IDs/counts/skips, candidate image ID and installed versions per batch. Add
tests only for confirmed upgraded boundaries or uncovered acceptance conditions;
do not create speculative suites for libraries unchanged by the candidate.
