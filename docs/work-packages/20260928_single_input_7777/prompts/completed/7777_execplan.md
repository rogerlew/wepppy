# Add 7777 single-file soils

Maintain this plan under docs/prompt_templates/codex_exec_plans.md.

## Purpose and context

Allow opted-in users to upload one 7777 soil and apply it to every hillslope and
OFE. wepppy/wepp/single_input.py validates input; the preserving writer in
wepppy/wepp/soils/utils/wepp_soil_util.py writes native fields. NoDb preparation
already opts uploaded soils into this writer and owned synthesis repeats profiles.

## Progress

- [x] Traced native and owned parser layouts.
- [x] Independently reviewed canonical contract committed as e3a12ba42.
- [x] Implemented validator/writer/help and regression coverage.
- [x] Focused 205 and regression 305 tests passed; native 1/2/12/32 OFE passed.
- [x] Exact supplied-file authenticated upload/build/download and archive/restore passed.
- [x] Full suite: 9892 passed, 99 skipped, 12 subtests passed; independent reviews approved.
- [x] Closed package with retained source/native/live/archive evidence.

## Surprises & Discoveries

7777 has ten layer fields and profile anisotropy; numeric comparisons against
7778 currently incorrectly group it with the six-field 2006 layout.

## Decision Log

2026-09-28: preserve 7777 without migration because supplied hydraulics are user
inputs. Reuse existing admission, source publication, synthesis and worker paths.

## Plan of Work

First commit contract and independent reviews. Then explicitly distinguish 7777
in validator and preserving serializer, extend existing soil-format and native
artifact test matrices with a sentinel fixture, and update UI/user/developer
guidance. Finally run focused tests and broad regression, inspect actual prepared
files and native outputs, and obtain independent correctness/security reviews.

## Concrete Steps and Acceptance

From repository root use wctl run-pytest tests/wepp/test_single_input_soil_formats.py
tests/nodb/test_single_input_sources.py tests/nodb/test_single_input_artifacts.py.
Extend native test matrix to 7777 at 1/2/12/32 OFEs and modifiers at 1/3 OFEs. Inspect
all ten layer values and profile anisotropy, source immutability and nonempty native
loss outputs. Run wctl run-pytest tests --maxfail=1; doc-lint changed docs.

## Compatibility and Recovery

Add accepted version without changing schemas or default serializer. Tests use
temporary paths; source archives remain opaque. Revert code only with uploaded
7777 projects preserved and compatible processing restored. No deployment here.

## Outcomes & Retrospective

7777 is implemented and wired through existing upload/preparation paths. Focused
artifact/native tests and live disposable-run acceptance pass. Full regression
and final independent reviews passed. No deployment performed.

Final revision note (2026-09-28): all milestones complete. Retained the supplied
243-byte CRLF source; clarified that native depth limits do not authorize
WEPPcloud to rewrite authored input. Existing shared workers need restart upon
deployment; fresh-process local acceptance does not imply rollout.
