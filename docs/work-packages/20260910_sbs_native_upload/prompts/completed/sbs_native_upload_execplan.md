# Native SBS upload ExecPlan

## Purpose

Users must receive the SBS result summary without accidentally entering a slow
Python raster engine. When uploads fail, show formatted gateway errors in Details
and keep hints/Summary in their intended roles. Execute this plan, preserving
all preexisting Builder/M1 changes. No full suite or push.

## Progress

- [x] Profile actual Wallow timeout and identify per-pixel fallback.
- [x] Record owner decisions and prepare canonical contracts.
- [x] Independent checkpoint reviews and ancestor commit `328db92dd`.
- [x] Native-only SBS helpers and pixel/mask parity tests.
- [x] SBS Details HTML renderer and controller regression tests.
- [x] Focused quality checks, actual Wallow upload/summary and hostile HTML test.
- [x] Independent final reviews, evidence and closeout.

## Context and sequence

Read sbs_map.py under nodb/mods/baer: five native wrapper helpers currently
catch failures and fall back. Remove those fallback paths and duplicate raster
implementations. Retain scalar summaries/custom color-map interpretation and
GDAL display reprojection. Preserve NoData union in four-class export and native
array orientation. Test actual native binaries against saved old Wallow output
and analytical expected arrays; fail visibly on missing/broken native APIs.

Read Disturbed uploadSbs and Baer loadModifyClass controllers. Shared
pushResponseStacktrace escapes error text and copies errors to Summary, so add
a bounded SBS error path that keeps Summary result-only. Render gateway HTML
in Details through off-document parse and allowlisted attribute-free elements;
discard active/resource nodes. Reuse existing status/details adapters and
revealing conventions. Test hostile HTML before browser installation. Build
controllers bundle with the canonical builder and reload development service
only after targeted checks. Do not touch fair-division map inputs merely to test;
use the disposable self-imposed-nave Builder run with the same Wallow fixture.

## Validation

Focused tests/nodb/mods/baer and tests/sbs_map, native failure/parity tests;
SBS/controller Jest tests, npm lint, relevant transport tests. Actual upload
through public development proxy must return success and render filename, table
and map. Exercise HTML 504 and then recovery in browser, confirm Details markup,
no hint/Summary error copies and no script/network execution.

## Surprises & Discoveries

Source NoData gated native export even though the native API accepts NoData.
The installed native binary predated the source NoData correction. Rebuilt the
owned Rust module; also excluded nonfinite/fractional metadata from integer masks.
Final export matches saved Python pixels/geometry/NoData at 0.57 seconds versus
54.09 seconds. Source/configured masks must remain separate from display NoData.

Review found concurrent map/summary errors could overwrite Summary or hide
Details; source-specific error retention now prevents that. Legacy HTTP200 JSON
errors are also rejected as summaries. First-upload filename had no DOM target
until reload; the template now always provides the current-map display.

The Builder synthetic generated-input fixture triggered migration checks after
soil validation. The proxy gate uses a separate fresh Builder run, lawless-challah.

## Decision Log

2026-09-10 UTC: native dependency failures must be explicit. Owner requests HTML
formatting for gateway responses in Details, no error in hint, result-only Summary.

## Outcomes & Retrospective

Completed. Native processing is required; corrected companion binary matches
the prior Wallow output. Gateway HTML renders safely in Details, accepted
Summary and filename remain coherent, and concurrent failures survive sibling
success. HTTP admission now rejects stale cross-request lease inheritance.

Validation: 78 SBS Python tests, 10 admission tests, 4 Rust tests, 852 JavaScript
tests and 2 template tests; native/submission stubtests, test-stub completeness,
ESLint, broad-exception checks, docs lint and bundle generation passed. Real
proxy upload/failure/retry/reload plus three consecutive additional uploads pass.
Independent correctness and security reviews pass, including real Redis/flock
admission checks and hostile-HTML browser containment. No full Python suite.

Development native artifact and services were refreshed; no fleet deployment or
push. Runtime changes remain uncommitted in WEPPpy and wepppyo3.


## Admission diagnostic extension

Repeated proxy smoke exposed intermittent HTTP409 `Submission lock expired`
before raster validation. Read-only Redis checks show no eviction. Add boundary
stack logging (no authorization/header/body data) to identify the failing lease
checkpoint. Compatibility: no response, schema, authorization or lock policy
change; retain rejection on lost ownership. Validate with actual upload and
existing admission tests if a confirmed logic repair follows.


The captured stack identifies `parent_lease.checkpoint()` at entry to a new
HTTP request, with Redis `Cannot extend an unlocked lock`. Repair request
isolation explicitly: top-level HTTP admission does not inherit lifecycle
context; nested operations retain their existing inheritance and lost-owner
checks. Add copied-context regression and current-owner conflict checks; retain
response/permission/queue contracts and validate repeated real proxy uploads.
