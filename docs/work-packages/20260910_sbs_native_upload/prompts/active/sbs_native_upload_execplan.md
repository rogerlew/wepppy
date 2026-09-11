# Native SBS upload ExecPlan

## Purpose

Users must receive the SBS result summary without accidentally entering a slow
Python raster engine. When uploads fail, show formatted gateway errors in Details
and keep hints/Summary in their intended roles. Execute this plan, preserving
all preexisting Builder/M1 changes. No full suite or push.

## Progress

- [x] Profile actual Wallow timeout and identify per-pixel fallback.
- [x] Record owner decisions and prepare canonical contracts.
- [ ] Independent checkpoint reviews and ancestor commit.
- [ ] Native-only SBS helpers and pixel/mask parity tests.
- [ ] SBS Details HTML renderer and controller regression tests.
- [ ] Focused quality checks, actual Wallow upload/summary and hostile HTML test.
- [ ] Independent final reviews, evidence and closeout.

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
Correct union masking reduces Wallow export from 55.55 to 0.35 seconds.

## Decision Log

2026-09-10 UTC: native dependency failures must be explicit. Owner requests HTML
formatting for gateway responses in Details, no error in hint, result-only Summary.

## Outcomes & Retrospective

Pending implementation and end-to-end evidence.
