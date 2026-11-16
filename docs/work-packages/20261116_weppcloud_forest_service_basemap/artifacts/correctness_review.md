# Correctness and User-Experience Review — Forest Service basemap

## Metadata

Independent reviewer: `/root/contract_correctness` (reviewer role), 2026-11-16.
Primary author records read-only review reports. Scope: FSBASE-01/02/03 adapter,
run/dashboard controllers, shared raster API, templates and landing export.
Canonical authority: `docs/ui-docs/contracts/forest-service-basemap-contract.md`.
Checkpoints: `277d55fba`, `abd9f6156`, and `630e155e1`. Related: security_review.md and browser
receipts, screenshots, asset_manifest.json, contract_reviews.md.

## User outcome and failure behavior

Terrain stays default. Users can choose official Forest Service cartography
without changing analysis or view. Fixed credit and limitations identify the
source. Loading/resource/renderer failures stay visible, preserve overlays and
allow choosing another provider. Combined-viewer OSM behavior stays independent.
The user-guide link repairs the legacy header. FSBASE-03 removes the obsolete
landing fallback while preserving both Vite themes.

## Valid runtime states and input cases

| State | Required outcome | Evidence |
| --- | --- | --- |
| Never used / optional state absent | Terrain; no renderer required | Controller regression and served fresh pages |
| Empty map / analysis state | Background independent of datasets | Controller initial empty layers; no model/data changes |
| Populated run | Official symbols and labels below existing overlays | fs-dashboard.png, fs-run.png, fs-deep.json |
| Existing legacy selections | Terrain/Satellite aliases and OSM preserved | Controller/factory regressions; browser switching |
| Failed/delayed resources | Visible status; last selection wins; other choices usable | fs-acceptance.json and asset-failure regression |
| Hostile metadata | Explicit unavailable state without provider substitution | fs-deep.json |
| Archived/restored project | Existing behavior, no added persistence requirement | No project writer/schema/persistence changes |

Selection inputs are separately specified in canonical FSBASE-01: missing/empty,
known explicit keys, run aliases, unknown/inherited keys and rapid sequences.
Own-property regression covers constructor/toString/__proto__; browser initial
state receipts cover absent/empty and explicit choices. No exhaustive claim for
all browsers or archived project formats is made.

## Failure-class assessment

FSBASE-02 fixes a confirmed deleted-route assumption in exactly two consumers:
landing.htm and header/_global_header_fixed.htm. FSBASE-03 subsequently removes
landing.htm at operator request; the header targets the existing user guide.
Real Flask URL building/rendering passes; mocked URL generation hid the defect.

## Findings

| ID | Severity | Description | Disposition |
| --- | --- | --- | --- |
| COR-01 | Medium | Contract combined inputs and runtime states. | Split matrices and failure classification; checkpoint review passed. |
| COR-02 | Medium | Asset onload initialization could throw and leave loading pending. | Validate renderer API, reject/reset assets; CSS failure and retry regression passes. |
| COR-03 | Medium | Inherited object keys incorrectly counted as providers. | Own-property checks in all changed resolution paths; regression passes. |

## Artifact and review evidence

Source reviews close COR-02/COR-03 with no unresolved medium/high source defects.
Frontend tests pass 126 suites / 1,083 Jest tests plus 9 Node tests. Actual served
artifacts render official cartography, preserve layer identities and view, and
support Deck picking, pan/resize synchronization and mobile credit. SHA-256
readback establishes the rebuilt bytes consumed by the browser.

Performance receipts initially measured idle requestAnimationFrame intervals,
not a pan stress benchmark. Original zoom checks established alignment; loaded
zoom-edge validation and authenticated pointer-selection evidence are recorded
separately. Production deployment and cross-browser validation are not claimed.
No new project artifacts require archive/restore membership changes; generated
frontend artifacts and failure states are the applicable observability boundary.

## Verdict

Gate: **pass** for reviewed source and browser scope. Unresolved findings:
**0 high, 0 medium, 0 low**. Independent reviewer `/root/contract_correctness`
confirmed final evidence on 2026-11-16: pointer selection/click editing, loaded
zoom edges, hydration, all landing disclosures and real Flask navigation pass.
The operator subsequently selected scoped tests: 327 Python, 43 controller,
6 adapter tests pass; broad execution was stopped without failures. Production
deployment is excluded.


FSBASE-03 final review passed on 2026-11-16 after ancestor `630e155e1`:
all four routes, real missing/unreadable/invalid-UTF-8 exports, unchanged state
injection, both live themes/disclosures, and 327 scoped tests. No unresolved
findings; the obsolete template and application/test references are removed.
