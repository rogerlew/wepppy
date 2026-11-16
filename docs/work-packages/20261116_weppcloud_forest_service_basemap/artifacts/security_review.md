# Security Review — Forest Service basemap

## Metadata

Package: 20261116_weppcloud_forest_service_basemap. Reviewer:
`/root/contract_security` (independent security_reviewer). Date: 2026-11-16.
Primary author transcribed the reviewer's read-only source/evidence verdict.
Checkpoints: FSBASE-01 `277d55fba`; FSBASE-02 `abd9f6156`; FSBASE-03 `630e155e1`, all ancestors before
their respective implementation deltas. Related: `correctness_review.md`,
`contract_reviews.md`, `renderer_evaluation.md`, and browser receipts/scripts.

## Security triage and assumptions

High: new browser external-egress surface; dedicated review required. The
service/style may change or be hostile. Application credentials and project URL
details must not reach it. Optional/empty/legacy states and existing raster-only
consumers must remain usable. No backend route, auth boundary, data model,
worker identity, queue, filesystem mutation boundary, or CSP change is introduced.
FSBASE-02 is low-impact same-origin navigation to an existing public guide.

## Findings

| ID | Severity | Description | Evidence/action | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | Medium | Pre-adoption inspection alone did not confine mutable style resources. | Canonical runtime boundary; custom protocol validates approved HTTPS subtree and rejects redirects. Real hostile-resource/redirect tests. | Resolved |
| SEC-02 | Medium | Playwright headers() omits security headers, weakening evidence. | Both scripts now await allHeaders() and capture promises; actual served browser tests rerun. | Resolved |
| SEC-03 | High | Legacy landing fallback uses an old CDN renderer with a reachable remote-attribution HTML sink. | Operator removed fallback under FSBASE-03. Template/CDN path deleted; both Vite themes and logged, path-free 503 responses verified. | Resolved by removal |

## Surface checks

- External fetch/supply chain: MapLibre 5.24.1 is pinned; exported distribution
  bytes match the installed patched renderer. BSD license retained. Overall npm
  audit is not claimed clean; exact advisory discrepancy and unrelated build
  findings are documented in renderer_evaluation.md.
- DOM: source attribution and TileJSON URL are removed; MapLibre attribution
  control stays disabled. Fixed safe text/link credit identifies the service.
  Hostile attribution passes through the actual renderer without HTML execution.
- Network: every style/font/sprite/tile fetch revalidates the service subtree,
  omits credentials/referrers, and rejects redirects. Captured request headers
  are reduced to booleans; no secrets are retained. Foreign glyph URLs and
  redirects cannot contact the forbidden host.
- Noninterference: Terrain remains default; valid selection, overlay picking,
  camera alignment, mobile layout, failures and switching remain usable. The
  shared OSM factory requires no renderer. Asset initialization/CSS failures
  now settle visibly and allow retry.
- Server/persistence/identity: unchanged; upload, filesystem, serialization,
  database locking, JWT/CSRF, worker execution and queue gates are not applicable.
- Observability/recovery: visible loading/unavailable states and alternate
  basemaps remain usable. Rollback rebuilds package-owned frontend artifacts;
  no project records or migrations are created. Artifact evidence is retained
  in this package and `asset_manifest.json` verifies served bytes.

## Validation evidence

`fs-acceptance.json`: 43 official requests; `fs-deep.json`: 48 requests in the
reviewed rerun, including normal rendering and hostile metadata/redirect cases.
Both use awaited allHeaders captures and report no Cookie, Authorization or
Referer. Node regressions cover resource checks, initialization failure/retry,
and the OSM-only factory. The reviewer inspected source and retained evidence;
they did not independently rerun the browser scripts.

## Verdict and sign-off

Gate: **pass**. Unresolved high/medium/low findings: **0/0/0**.
Security reviewer `/root/contract_security`, 2026-11-16, explicitly approved
FSBASE-01/02 after SEC-02 correction and FSBASE-03 after legacy fallback removal. Primary author `/root` recorded closure.
No risk acceptance or deployment authorization is implied. Existing broader
smoke/test limitations remain correctness/validation matters.


## FSBASE-03 final verification

Both independent reviewers passed after checkpoint `630e155e1` and removal.
The actual Flask route receipt covers four valid exports and twelve unavailable
export cases (missing, directory/read failure, invalid UTF-8). Each failure is a
plain, uncached 503 without path disclosure. Both live Vite themes and keyboard
disclosures pass. No legacy template reference remains in application/tests.
SEC-03 is closed by removal; no fallback renderer exception is accepted.
